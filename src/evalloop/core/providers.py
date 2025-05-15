from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

# Assuming schemas.py contains EvalLoopConfig and ModelConfig
from .schemas import EvalLoopConfig, ModelConfig, ModelConfigParameters

import time
import openai # Added import
from openai import OpenAIError # For specific error handling
import groq # Added import
from groq import GroqError # For specific error handling
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os # Ensure os is imported for getenv

# Default timeout for LLM API calls in seconds
DEFAULT_TIMEOUT_SECONDS = 30.0
# Default retry attempts
DEFAULT_RETRY_ATTEMPTS = 3

class LLMResponse(BaseModel):
    text_output: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None # Estimated cost for this specific call
    latency_ms: Optional[float] = None # Latency for this specific call
    model_name_used: Optional[str] = None # Actual model name used by the provider
    raw_response: Optional[Any] = None # To store the original provider response for debugging/auditing
    error: Optional[str] = None # If any error occurred during the call
    attempts_made: Optional[int] = 1 # Number of attempts made for the call
    # We can add other fields like finish_reason, etc. if needed later

class LLMProvider(ABC):
    """Abstract Base Class for all LLM providers."""

    provider_name: str # Must be defined by subclasses, e.g., "openai", "groq"

    def __init__(self, global_config: EvalLoopConfig):
        """
        Initializes the provider with the global EvalLoop configuration.
        Specific API keys should be retrieved from global_config.api_keys within this constructor.
        """
        self.global_config = global_config
        self.api_key: Optional[str] = self._get_api_key(global_config)

    @abstractmethod
    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        """Helper method for subclasses to extract their specific API key from config."""
        pass

    @abstractmethod
    def _execute_llm_call_attempt(
        self,
        client: Any, # Provider-specific client
        prompt_messages: List[Dict[str,str]], # e.g., [{"role": "user", "content": prompt}]
        model_to_call: str,
        effective_params: Dict[str, Any],
        timeout: float
    ) -> LLMResponse:
        """
        Executes a single attempt of the LLM call. Subclasses implement this.
        This method is what tenacity will retry.
        """
        pass

    def make_llm_call(
        self,
        test_case_name: str, 
        prompt: str,
        resolved_model_config: ModelConfig, 
    ) -> LLMResponse:
        """
        Makes a call to the LLM provider, handling retries and timeouts.

        Retries are performed using an exponential backoff strategy. The number of
        attempts and the timeout for each attempt can be configured:
        1. Via `parameters.retry_attempts` and `parameters.timeout_s` in the `resolved_model_config` for the test case.
        2. Via `default_model.parameters.retry_attempts` and `default_model.parameters.timeout_s` in `evalloop.config.yaml`.
        3. Defaults to `DEFAULT_RETRY_ATTEMPTS` (currently 3) and `DEFAULT_TIMEOUT_SECONDS` (currently 30.0s) if not specified.

        Args:
            test_case_name: The name of the test case for logging/context.
            prompt: The prompt to send to the LLM.
            resolved_model_config: The fully resolved model configuration (provider, model_name, parameters)
                                   to use for this call.
        
        Returns:
            An LLMResponse object containing the LLM's output and metadata.
        """
        if not self.api_key and not self.provider_name == "mock": # Mock provider might not need API key
            return LLMResponse(
                error=f"{self.provider_name} API key not found in configuration for test: {test_case_name}", 
                model_name_used=resolved_model_config.model_name,
                attempts_made=1
            )

        effective_params = self.get_effective_model_parameters(resolved_model_config)
        model_to_call = resolved_model_config.model_name
        if model_to_call == "default" and self.global_config.default_model:
            if self.global_config.default_model.provider == self.provider_name or self.global_config.default_model.provider == "default":
                 model_to_call = self.global_config.default_model.model_name
        
        if not model_to_call or model_to_call == "default":
             return LLMResponse(error=f"No valid {self.provider_name} model name specified for test: {test_case_name}", attempts_made=1)

        # Determine timeout: test_case -> global_default -> DEFAULT_TIMEOUT_SECONDS
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        if resolved_model_config.parameters and resolved_model_config.parameters.timeout_s is not None:
            timeout_seconds = resolved_model_config.parameters.timeout_s
        elif self.global_config.default_model and self.global_config.default_model.parameters and self.global_config.default_model.parameters.timeout_s is not None:
            timeout_seconds = self.global_config.default_model.parameters.timeout_s
        
        # Determine retries: test_case -> global_default -> DEFAULT_RETRY_ATTEMPTS
        retry_attempts = DEFAULT_RETRY_ATTEMPTS
        if resolved_model_config.parameters and resolved_model_config.parameters.retry_attempts is not None:
            retry_attempts = resolved_model_config.parameters.retry_attempts
        elif self.global_config.default_model and self.global_config.default_model.parameters and self.global_config.default_model.parameters.retry_attempts is not None:
            retry_attempts = self.global_config.default_model.parameters.retry_attempts
        
        # Prepare messages list (common for OpenAI-compatible APIs)
        prompt_messages = [{"role": "user", "content": prompt}]

        # Instantiate the tenacity retry decorator dynamically based on provider specifics if needed
        # For now, a generic retry for common transient errors (OpenAIError, GroqError)
        # Subclasses can override `_get_retry_decorator` if they have more specific error types
        
        @self._get_retry_decorator(max_attempts=retry_attempts)
        def DYNAMIC_WRAPPED_CALL_WITH_RETRY():
            # Client instantiation might be specific to provider, so done within _execute_llm_call_attempt or just before
            # For now, assume client is created in _execute_llm_call_attempt or its an instance var
            return self._execute_llm_call_attempt(
                client=self._get_client(), # Subclasses will need to implement _get_client()
                prompt_messages=prompt_messages,
                model_to_call=model_to_call,
                effective_params=effective_params,
                timeout=timeout_seconds
            )
        
        try:
            final_response = DYNAMIC_WRAPPED_CALL_WITH_RETRY()
            return final_response
        except Exception as e: # Catch errors from tenacity itself or if retry fails ultimately
            return LLMResponse(
                error=f"LLM call ultimately failed after {retry_attempts} attempts for test '{test_case_name}': {type(e).__name__} - {str(e)[:200]}", 
                model_name_used=model_to_call,
                attempts_made=retry_attempts # or use tenacity's attempt_number if accessible
            )

    @abstractmethod
    def _get_client(self) -> Any:
        """Subclasses must implement this to return their specific API client."""
        pass

    def _get_retry_decorator(self, max_attempts: int):
        """ Returns a tenacity retry decorator. Subclasses can override for specific error types."""
        transient_errors = (OpenAIError, GroqError, openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError)
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10), # Changed min to 1 for 1s minimum backoff
            retry=retry_if_exception_type(transient_errors),
        )

    def get_effective_model_parameters(self, test_model_config: ModelConfig) -> Dict[str, Any]:
        """
        Resolves the effective model parameters by merging global defaults with test-specific overrides.
        This is a utility that concrete providers might use.
        Assumes test_model_config.parameters already contains overrides.
        """
        # Start with global default parameters if they exist
        effective_params = {}
        if self.global_config.default_model and self.global_config.default_model.parameters:
            effective_params = self.global_config.default_model.parameters.model_dump(exclude_none=True)
        
        # Override with test-specific parameters
        if test_model_config.parameters:
            test_specific_params = test_model_config.parameters.model_dump(exclude_none=True)
            effective_params.update(test_specific_params)
            
        return effective_params

# Example of how a concrete provider might look (very basic sketch):
class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    _client: Optional[openai.OpenAI] = None

    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        key = os.getenv("OPENAI_API_KEY")
        if key: return key
        return config.api_keys.openai if config.api_keys else None

    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            if not self.api_key: # Should have been caught by make_llm_call guard
                raise ValueError("OpenAI API key not available for client instantiation")
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def _execute_llm_call_attempt(
        self, client: openai.OpenAI, prompt_messages: List[Dict[str,str]], 
        model_to_call: str, effective_params: Dict[str, Any], timeout: float
    ) -> LLMResponse:
        """
        Executes a single attempt of an OpenAI ChatCompletion call.
        This method is intended to be wrapped by the retry logic in the base LLMProvider.
        """
        start_time = time.time()
        params_for_call = effective_params.copy()
        params_for_call.pop('timeout_s', None) # Remove timeout_s if it exists
        params_for_call.pop('retry_attempts', None) # Remove retry_attempts if it exists
        try:
            completion = client.chat.completions.create(
                model=model_to_call,
                messages=prompt_messages,
                timeout=timeout, 
                **params_for_call # Use the modified params
            )
            latency_ms = (time.time() - start_time) * 1000
            text_output = completion.choices[0].message.content if completion.choices else None
            return LLMResponse(
                text_output=text_output,
                prompt_tokens=completion.usage.prompt_tokens if completion.usage else None,
                completion_tokens=completion.usage.completion_tokens if completion.usage else None,
                total_tokens=completion.usage.total_tokens if completion.usage else None,
                latency_ms=latency_ms,
                model_name_used=model_to_call,
                raw_response=completion.model_dump(exclude_none=True),
                attempts_made=1 # This will be updated by tenacity if retried
            )
        except OpenAIError as e:
            raise e 
        except Exception as e:
            return LLMResponse(error=f"Unexpected error in OpenAI call: {type(e).__name__} - {e}", model_name_used=model_to_call, attempts_made=1)

class GroqProvider(LLMProvider):
    provider_name = "groq"
    _client: Optional[groq.Groq] = None

    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        key = os.getenv("GROQ_API_KEY")
        if key: return key
        return config.api_keys.groq if config.api_keys else None

    def _get_client(self) -> groq.Groq:
        if self._client is None:
            if not self.api_key:
                raise ValueError("Groq API key not available for client instantiation")
            self._client = groq.Groq(api_key=self.api_key)
        return self._client

    def _execute_llm_call_attempt(
        self, client: groq.Groq, prompt_messages: List[Dict[str,str]], 
        model_to_call: str, effective_params: Dict[str, Any], timeout: float
    ) -> LLMResponse:
        """
        Executes a single attempt of a Groq ChatCompletion call.
        This method is intended to be wrapped by the retry logic in the base LLMProvider.
        """
        start_time = time.time()
        params_for_call = effective_params.copy()
        params_for_call.pop('timeout_s', None) # Remove timeout_s if it exists
        params_for_call.pop('retry_attempts', None) # Remove retry_attempts if it exists
        try:
            completion = client.chat.completions.create(
                model=model_to_call,
                messages=prompt_messages,
                timeout=timeout,
                **params_for_call # Use the modified params
            )
            latency_ms = (time.time() - start_time) * 1000
            text_output = completion.choices[0].message.content if completion.choices else None
            return LLMResponse(
                text_output=text_output,
                prompt_tokens=completion.usage.prompt_tokens if completion.usage else None,
                completion_tokens=completion.usage.completion_tokens if completion.usage else None,
                total_tokens=completion.usage.total_tokens if completion.usage else None,
                latency_ms=latency_ms,
                model_name_used=model_to_call,
                raw_response=completion.model_dump(exclude_none=True),
                attempts_made=1
            )
        except GroqError as e:
            raise e
        except Exception as e:
            return LLMResponse(error=f"Unexpected error in Groq call: {type(e).__name__} - {e}", model_name_used=model_to_call, attempts_made=1)

# Note: OpenRouter uses an OpenAI-compatible API. We use the openai library.
# No separate library install is typically needed if `openai` is already a dependency.

class OpenRouterProvider(LLMProvider):
    provider_name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1" # Default OpenRouter API base URL
    _client: Optional[openai.OpenAI] = None # Uses OpenAI client

    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        key = os.getenv("OPENROUTER_API_KEY")
        if key: return key
        return config.api_keys.openrouter if config.api_keys else None

    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenRouter API key not available for client instantiation")
            self._client = openai.OpenAI(api_key=self.api_key, base_url=self.BASE_URL)
        return self._client

    def _execute_llm_call_attempt(
        self, client: openai.OpenAI, prompt_messages: List[Dict[str,str]], 
        model_to_call: str, effective_params: Dict[str, Any], timeout: float
    ) -> LLMResponse:
        """
        Executes a single attempt of an OpenRouter ChatCompletion call using the OpenAI client.
        This method is intended to be wrapped by the retry logic in the base LLMProvider.
        """
        start_time = time.time()
        params_for_call = effective_params.copy()
        params_for_call.pop('timeout_s', None) # Remove timeout_s if it exists
        params_for_call.pop('retry_attempts', None) # Remove retry_attempts if it exists
        try:
            completion_obj = client.chat.completions.with_raw_response.create(
                model=model_to_call, 
                messages=prompt_messages,
                timeout=timeout,
                **params_for_call # Use the modified params
            )
            completion = completion_obj.parse() # Get the Pydantic model
            latency_ms = (time.time() - start_time) * 1000
            text_output = completion.choices[0].message.content if completion.choices else None
            
            cost = None
            if completion_obj.headers and completion_obj.headers.get("x-openrouter-cost"):
                try: cost = float(completion_obj.headers.get("x-openrouter-cost"))
                except ValueError: pass

            return LLMResponse(
                text_output=text_output,
                prompt_tokens=completion.usage.prompt_tokens if completion.usage else None,
                completion_tokens=completion.usage.completion_tokens if completion.usage else None,
                total_tokens=completion.usage.total_tokens if completion.usage else None,
                cost=cost,
                latency_ms=latency_ms,
                model_name_used=model_to_call,
                raw_response=completion.model_dump(exclude_none=True),
                attempts_made=1
            )
        except OpenAIError as e:
            raise e
        except Exception as e:
            return LLMResponse(error=f"Unexpected error in OpenRouter call: {type(e).__name__} - {e}", model_name_used=model_to_call, attempts_made=1)

# Provider Factory
_provider_classes = {
    OpenAIProvider.provider_name: OpenAIProvider,
    GroqProvider.provider_name: GroqProvider,
    OpenRouterProvider.provider_name: OpenRouterProvider,
    # Add other providers here as they are implemented
}

def get_llm_provider(provider_name: str, global_config: EvalLoopConfig) -> Optional[LLMProvider]:
    """
    Factory function to get an instance of an LLM provider.

    Args:
        provider_name: The name of the provider (e.g., "openai", "groq").
        global_config: The global EvalLoopConfig object.

    Returns:
        An instance of the requested LLMProvider, or None if not found.
    """
    provider_class = _provider_classes.get(provider_name.lower())
    if provider_class:
        return provider_class(global_config)
    return None



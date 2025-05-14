from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

# Assuming schemas.py contains EvalLoopConfig and ModelConfig
from .schemas import EvalLoopConfig, ModelConfig, ModelConfigParameters

import time
import openai # Added import
from openai import OpenAIError # For specific error handling
import groq # Added import
from groq import GroqError # For specific error handling

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
    def make_llm_call(
        self,
        test_case_name: str, # For logging/context
        prompt: str,
        resolved_model_config: ModelConfig, # Already resolved from global and test-specific configs
        # We pass the full ModelConfig in case provider needs more than just parameters
    ) -> LLMResponse:
        """
        Makes a call to the LLM provider.

        Args:
            test_case_name: The name of the test case for logging/context.
            prompt: The prompt to send to the LLM.
            resolved_model_config: The fully resolved model configuration (provider, model_name, parameters)
                                   to use for this call.
        
        Returns:
            An LLMResponse object containing the LLM's output and metadata.
        """
        pass

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

    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        if config.api_keys:
            return config.api_keys.openai
        return None

    def make_llm_call(
        self,
        test_case_name: str, # For logging/context
        prompt: str,
        resolved_model_config: ModelConfig,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(error=f"OpenAI API key not found in configuration for test: {test_case_name}", model_name_used=resolved_model_config.model_name)

        client = openai.OpenAI(api_key=self.api_key)
        start_time = time.time()
        
        effective_params = self.get_effective_model_parameters(resolved_model_config)
        model_to_call = resolved_model_config.model_name
        if model_to_call == "default" and self.global_config.default_model:
            model_to_call = self.global_config.default_model.model_name
        
        if not model_to_call or model_to_call == "default": # Still default after trying global
             return LLMResponse(error=f"No valid OpenAI model name specified for test: {test_case_name}")

        try:
            # Ensure messages format is correct
            messages = [{"role": "user", "content": prompt}]
            
            completion = client.chat.completions.create(
                model=model_to_call,
                messages=messages,
                **effective_params
            )
            latency_ms = (time.time() - start_time) * 1000
            
            text_output = None
            if completion.choices and len(completion.choices) > 0:
                text_output = completion.choices[0].message.content

            prompt_tokens = completion.usage.prompt_tokens if completion.usage else None
            completion_tokens = completion.usage.completion_tokens if completion.usage else None
            total_tokens = completion.usage.total_tokens if completion.usage else None

            # Placeholder for cost calculation - requires model-specific pricing
            cost = None 

            return LLMResponse(
                text_output=text_output,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                model_name_used=model_to_call,
                raw_response=completion.model_dump(exclude_none=True)
            )
        except OpenAIError as e: # Catch specific OpenAI errors
            return LLMResponse(error=f"OpenAI API Error for test '{test_case_name}': {type(e).__name__} - {e}", model_name_used=model_to_call)
        except Exception as e:
            # Catch any other unexpected errors during the API call
            return LLMResponse(error=f"Unexpected error during OpenAI call for test '{test_case_name}': {type(e).__name__} - {e}", model_name_used=model_to_call)

class GroqProvider(LLMProvider):
    provider_name = "groq"

    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        if config.api_keys:
            return config.api_keys.groq
        return None

    def make_llm_call(
        self,
        test_case_name: str, # For logging/context
        prompt: str,
        resolved_model_config: ModelConfig,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(error=f"Groq API key not found in configuration for test: {test_case_name}", model_name_used=resolved_model_config.model_name)

        client = groq.Groq(api_key=self.api_key)
        start_time = time.time()
        
        effective_params = self.get_effective_model_parameters(resolved_model_config)
        model_to_call = resolved_model_config.model_name
        if model_to_call == "default" and self.global_config.default_model:
            # Check if the global default provider is also groq, or if it's a generic default
            if self.global_config.default_model.provider == self.provider_name or self.global_config.default_model.provider == "default":
                 model_to_call = self.global_config.default_model.model_name
        
        if not model_to_call or model_to_call == "default": # Still default after trying global
             return LLMResponse(error=f"No valid Groq model name specified for test: {test_case_name}")

        try:
            messages = [{"role": "user", "content": prompt}]
            
            completion = client.chat.completions.create(
                model=model_to_call,
                messages=messages,
                **effective_params
            )
            latency_ms = (time.time() - start_time) * 1000
            
            text_output = None
            if completion.choices and len(completion.choices) > 0:
                text_output = completion.choices[0].message.content

            prompt_tokens = completion.usage.prompt_tokens if completion.usage else None
            completion_tokens = completion.usage.completion_tokens if completion.usage else None
            total_tokens = completion.usage.total_tokens if completion.usage else None

            # Placeholder for cost calculation - requires model-specific pricing for Groq
            cost = None 

            return LLMResponse(
                text_output=text_output,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                model_name_used=model_to_call,
                raw_response=completion.model_dump(exclude_none=True) # Groq API is OpenAI compatible
            )
        except GroqError as e: # Catch specific Groq errors
            return LLMResponse(error=f"Groq API Error for test '{test_case_name}': {type(e).__name__} - {e}", model_name_used=model_to_call)
        except Exception as e:
            return LLMResponse(error=f"Unexpected error during Groq call for test '{test_case_name}': {type(e).__name__} - {e}", model_name_used=model_to_call)

# Note: OpenRouter uses an OpenAI-compatible API. We use the openai library.
# No separate library install is typically needed if `openai` is already a dependency.

class OpenRouterProvider(LLMProvider):
    provider_name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1" # Default OpenRouter API base URL

    def _get_api_key(self, config: EvalLoopConfig) -> Optional[str]:
        if config.api_keys:
            return config.api_keys.openrouter
        return None

    def make_llm_call(
        self,
        test_case_name: str, # For logging/context
        prompt: str,
        resolved_model_config: ModelConfig,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(error=f"OpenRouter API key not found in configuration for test: {test_case_name}", model_name_used=resolved_model_config.model_name)

        # For OpenRouter, the model name in the config often includes the provider, e.g., "openai/gpt-3.5-turbo"
        # The `openai` library expects just the model part for its `model` parameter when a base_url is set.
        # However, OpenRouter documentation specifies using the full path as the model string.
        model_to_call = resolved_model_config.model_name
        if model_to_call == "default" and self.global_config.default_model:
            if self.global_config.default_model.provider == self.provider_name or self.global_config.default_model.provider == "default":
                 model_to_call = self.global_config.default_model.model_name
        
        if not model_to_call or model_to_call == "default":
             return LLMResponse(error=f"No valid OpenRouter model name specified for test: {test_case_name} (e.g., 'openai/gpt-3.5-turbo')")

        client = openai.OpenAI(
            base_url=self.BASE_URL,
            api_key=self.api_key,
        )
        start_time = time.time()
        
        effective_params = self.get_effective_model_parameters(resolved_model_config)
        
        # Remove 'provider' from effective_params if it exists, as it's not an OpenAI API param
        effective_params.pop('provider', None)

        try:
            messages = [{"role": "user", "content": prompt}]
            
            completion = client.chat.completions.create(
                model=model_to_call, # For OpenRouter, this is usually the full model string like "google/gemini-flash-1.5"
                messages=messages,
                **effective_params
            )
            latency_ms = (time.time() - start_time) * 1000
            
            text_output = None
            if completion.choices and len(completion.choices) > 0:
                text_output = completion.choices[0].message.content

            prompt_tokens = completion.usage.prompt_tokens if completion.usage else None
            completion_tokens = completion.usage.completion_tokens if completion.usage else None
            total_tokens = completion.usage.total_tokens if completion.usage else None

            # Cost calculation for OpenRouter is complex as it depends on the specific model routed to.
            # This might require parsing the `X-OpenRouter-Cost` header from the raw response if available,
            # or using their pricing API/documentation. For now, placeholder.
            cost = None 
            if completion.headers and completion.headers.get("x-openrouter-cost"):
                try:
                    cost = float(completion.headers.get("x-openrouter-cost"))
                except ValueError:
                    pass # Could log a warning here

            return LLMResponse(
                text_output=text_output,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                model_name_used=model_to_call, # This is the OpenRouter model string
                raw_response=completion.model_dump(exclude_none=True)
            )
        except OpenAIError as e: # OpenRouter uses OpenAI-compatible error structures
            return LLMResponse(error=f"OpenRouter API Error for test '{test_case_name}' (model: {model_to_call}): {type(e).__name__} - {e}", model_name_used=model_to_call)
        except Exception as e:
            return LLMResponse(error=f"Unexpected error during OpenRouter call for test '{test_case_name}' (model: {model_to_call}): {type(e).__name__} - {e}", model_name_used=model_to_call)

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



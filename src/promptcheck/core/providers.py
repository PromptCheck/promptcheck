from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

from promptcheck.core.schemas import PromptCheckConfig, ModelConfig, ModelConfigParameters

import time
import openai
from openai import OpenAIError
import groq
from groq import GroqError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRY_ATTEMPTS = 3

class LLMResponse(BaseModel):
    text_output: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None
    latency_ms: Optional[float] = None
    model_name_used: Optional[str] = None
    raw_response: Optional[Any] = None
    error: Optional[str] = None
    attempts_made: Optional[int] = 1

class LLMProvider(ABC):
    provider_name: str

    def __init__(self, global_config: PromptCheckConfig):
        self.global_config = global_config
        self.api_key: Optional[str] = self._get_api_key(global_config)

    @abstractmethod
    def _get_api_key(self, config: PromptCheckConfig) -> Optional[str]:
        pass

    @abstractmethod
    def _execute_llm_call_attempt(self, client: Any, prompt_messages: List[Dict[str,str]], model_to_call: str, effective_params: Dict[str, Any], timeout: float) -> LLMResponse:
        pass

    def make_llm_call(self, test_case_name: str, prompt: str, resolved_model_config: ModelConfig) -> LLMResponse:
        """
        Makes a call to the LLM provider, handling retries and timeouts.
        Retries are performed using an exponential backoff strategy. The number of
        attempts and the timeout for each attempt can be configured:
        1. Via `parameters.retry_attempts` and `parameters.timeout_s` in the `resolved_model_config` for the test case.
        2. Via `default_model.parameters.retry_attempts` and `default_model.parameters.timeout_s` in `promptcheck.config.yaml`.
        3. Defaults to `DEFAULT_RETRY_ATTEMPTS` (currently 3) and `DEFAULT_TIMEOUT_SECONDS` (currently 30.0s) if not specified.
        Args:
            test_case_name: The name of the test case for logging/context.
            prompt: The prompt to send to the LLM.
            resolved_model_config: The fully resolved model configuration.
        Returns:
            An LLMResponse object.
        """
        if not self.api_key and not self.provider_name == "mock":
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
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        if resolved_model_config.parameters and resolved_model_config.parameters.timeout_s is not None:
            timeout_seconds = resolved_model_config.parameters.timeout_s
        elif self.global_config.default_model and self.global_config.default_model.parameters and self.global_config.default_model.parameters.timeout_s is not None:
            timeout_seconds = self.global_config.default_model.parameters.timeout_s
        retry_attempts = DEFAULT_RETRY_ATTEMPTS
        if resolved_model_config.parameters and resolved_model_config.parameters.retry_attempts is not None:
            retry_attempts = resolved_model_config.parameters.retry_attempts
        elif self.global_config.default_model and self.global_config.default_model.parameters and self.global_config.default_model.parameters.retry_attempts is not None:
            retry_attempts = self.global_config.default_model.parameters.retry_attempts
        prompt_messages = [{"role": "user", "content": prompt}]
        @self._get_retry_decorator(max_attempts=retry_attempts)
        def DYNAMIC_WRAPPED_CALL_WITH_RETRY():
            return self._execute_llm_call_attempt(
                client=self._get_client(),
                prompt_messages=prompt_messages,
                model_to_call=model_to_call,
                effective_params=effective_params,
                timeout=timeout_seconds
            )
        try:
            final_response = DYNAMIC_WRAPPED_CALL_WITH_RETRY()
            return final_response
        except Exception as e:
            return LLMResponse(
                error=f"LLM call ultimately failed after {retry_attempts} attempts for test '{test_case_name}': {type(e).__name__} - {str(e)[:200]}", 
                model_name_used=model_to_call,
                attempts_made=retry_attempts
            )

    @abstractmethod
    def _get_client(self) -> Any:
        pass

    def _get_retry_decorator(self, max_attempts: int):
        transient_errors = (OpenAIError, GroqError, openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError)
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(transient_errors),
        )

    def get_effective_model_parameters(self, test_model_config: ModelConfig) -> Dict[str, Any]:
        effective_params = {}
        if self.global_config.default_model and self.global_config.default_model.parameters:
            effective_params = self.global_config.default_model.parameters.model_dump(exclude_none=True)
        if test_model_config.parameters:
            test_specific_params = test_model_config.parameters.model_dump(exclude_none=True)
            effective_params.update(test_specific_params)
        return effective_params

class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    _client: Optional[openai.OpenAI] = None
    def _get_api_key(self, config: PromptCheckConfig) -> Optional[str]:
        key = os.getenv("OPENAI_API_KEY")
        if key: return key
        return config.api_keys.openai if config.api_keys else None
    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            if not self.api_key: 
                raise ValueError("OpenAI API key not available for client instantiation")
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def _execute_llm_call_attempt(self, client: openai.OpenAI, prompt_messages: List[Dict[str,str]], model_to_call: str, effective_params: Dict[str, Any], timeout: float) -> LLMResponse:
        start_time = time.time()
        params_for_call = effective_params.copy()
        params_for_call.pop('timeout_s', None) 
        params_for_call.pop('retry_attempts', None) 
        try:
            completion = client.chat.completions.create(model=model_to_call, messages=prompt_messages, timeout=timeout, **params_for_call)
            latency_ms = (time.time() - start_time) * 1000
            text_output = completion.choices[0].message.content if completion.choices else None
            return LLMResponse(text_output=text_output, prompt_tokens=completion.usage.prompt_tokens if completion.usage else None, completion_tokens=completion.usage.completion_tokens if completion.usage else None, total_tokens=completion.usage.total_tokens if completion.usage else None, latency_ms=latency_ms, model_name_used=model_to_call, raw_response=completion.model_dump(exclude_none=True), attempts_made=1)
        except OpenAIError as e:
            raise e 
        except Exception as e:
            return LLMResponse(error=f"Unexpected error in OpenAI call: {type(e).__name__} - {e}", model_name_used=model_to_call, attempts_made=1)

class GroqProvider(LLMProvider):
    provider_name = "groq"
    _client: Optional[groq.Groq] = None
    def _get_api_key(self, config: PromptCheckConfig) -> Optional[str]:
        key = os.getenv("GROQ_API_KEY")
        if key: return key
        return config.api_keys.groq if config.api_keys else None
    def _get_client(self) -> groq.Groq:
        if self._client is None:
            if not self.api_key:
                raise ValueError("Groq API key not available for client instantiation")
            self._client = groq.Groq(api_key=self.api_key)
        return self._client
    def _execute_llm_call_attempt(self, client: groq.Groq, prompt_messages: List[Dict[str,str]], model_to_call: str, effective_params: Dict[str, Any], timeout: float) -> LLMResponse:
        start_time = time.time()
        params_for_call = effective_params.copy()
        params_for_call.pop('timeout_s', None) 
        params_for_call.pop('retry_attempts', None) 
        try:
            completion = client.chat.completions.create(model=model_to_call, messages=prompt_messages, timeout=timeout, **params_for_call)
            latency_ms = (time.time() - start_time) * 1000
            text_output = completion.choices[0].message.content if completion.choices else None
            return LLMResponse(text_output=text_output, prompt_tokens=completion.usage.prompt_tokens if completion.usage else None, completion_tokens=completion.usage.completion_tokens if completion.usage else None, total_tokens=completion.usage.total_tokens if completion.usage else None, latency_ms=latency_ms, model_name_used=model_to_call, raw_response=completion.model_dump(exclude_none=True), attempts_made=1)
        except GroqError as e:
            raise e
        except Exception as e:
            return LLMResponse(error=f"Unexpected error in Groq call: {type(e).__name__} - {e}", model_name_used=model_to_call, attempts_made=1)

class OpenRouterProvider(LLMProvider):
    provider_name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    _client: Optional[openai.OpenAI] = None
    def _get_api_key(self, config: PromptCheckConfig) -> Optional[str]:
        key = os.getenv("OPENROUTER_API_KEY")
        if key: return key
        return config.api_keys.openrouter if config.api_keys else None
    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenRouter API key not available for client instantiation")
            self._client = openai.OpenAI(api_key=self.api_key, base_url=self.BASE_URL)
        return self._client
    def _execute_llm_call_attempt(self, client: openai.OpenAI, prompt_messages: List[Dict[str,str]], model_to_call: str, effective_params: Dict[str, Any], timeout: float) -> LLMResponse:
        start_time = time.time()
        params_for_call = effective_params.copy()
        params_for_call.pop('timeout_s', None) 
        params_for_call.pop('retry_attempts', None) 
        try:
            completion_obj = client.chat.completions.with_raw_response.create(model=model_to_call, messages=prompt_messages, timeout=timeout, **params_for_call)
            completion = completion_obj.parse()
            latency_ms = (time.time() - start_time) * 1000
            text_output = completion.choices[0].message.content if completion.choices else None
            cost = None
            if completion_obj.headers and completion_obj.headers.get("x-openrouter-cost"):
                try: cost = float(completion_obj.headers.get("x-openrouter-cost"))
                except ValueError: pass
            return LLMResponse(text_output=text_output, prompt_tokens=completion.usage.prompt_tokens if completion.usage else None, completion_tokens=completion.usage.completion_tokens if completion.usage else None, total_tokens=completion.usage.total_tokens if completion.usage else None, cost=cost, latency_ms=latency_ms, model_name_used=model_to_call, raw_response=completion.model_dump(exclude_none=True), attempts_made=1)
        except OpenAIError as e:
            raise e
        except Exception as e:
            return LLMResponse(error=f"Unexpected error in OpenRouter call: {type(e).__name__} - {e}", model_name_used=model_to_call, attempts_made=1)

class DummyProvider(LLMProvider):
    provider_name = "dummy"
    def _get_api_key(self, config: PromptCheckConfig) -> Optional[str]:
        return "local"
    def _get_client(self) -> Any:
        return None
    def _execute_llm_call_attempt(self, client: Any, prompt_messages: List[Dict[str,str]], model_to_call: str, effective_params: Dict[str, Any], timeout: float) -> LLMResponse:
        return LLMResponse(text_output="Hello world", prompt_tokens=1, completion_tokens=2, total_tokens=3, latency_ms=42.0, model_name_used="dummy/dummy-model-v1", attempts_made=1)

_provider_classes = {
    OpenAIProvider.provider_name: OpenAIProvider,
    GroqProvider.provider_name: GroqProvider,
    OpenRouterProvider.provider_name: OpenRouterProvider,
    DummyProvider.provider_name: DummyProvider,
}

def get_llm_provider(provider_name: str, global_config: PromptCheckConfig) -> Optional[LLMProvider]:
    provider_class = _provider_classes.get(provider_name.lower())
    if provider_class:
        return provider_class(global_config)
    return None 
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator

class MetricThreshold(BaseModel):
    # Flexible to allow different kinds of thresholds, e.g., f_score for rouge, value for latency
    f_score: Optional[float] = None
    value: Optional[Union[int, float]] = None
    completion_max: Optional[int] = None
    # Add other specific threshold types as needed

class MetricConfig(BaseModel):
    metric: str
    parameters: Optional[Dict[str, Any]] = None
    threshold: Optional[MetricThreshold] = None # For single value thresholds like latency
    thresholds: Optional[MetricThreshold] = None # Alias for threshold, or for multi-value like token_count

    @validator('thresholds', pre=True, always=True)
    def _check_thresholds(cls, v, values):
        if v is None and values.get('threshold') is not None:
            return values.get('threshold')
        return v

class ModelConfigParameters(BaseModel):
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    # Add other common model parameters here or allow arbitrary through extra
    # For now, let's allow any other parameters
    class Config:
        extra = "allow"

class ModelConfig(BaseModel):
    provider: str = "default"
    model_name: str = "default"
    parameters: Optional[ModelConfigParameters] = Field(default_factory=ModelConfigParameters)

class InputData(BaseModel):
    prompt: str
    variables: Optional[Dict[str, Any]] = None

class ExpectedOutput(BaseModel):
    exact_match_string: Optional[str] = None
    regex_pattern: Optional[str] = None
    reference_texts: Optional[List[str]] = None
    # Allow for custom data structures for other metric types if needed in the future
    class Config:
        extra = "allow"

class TestCase(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    type: str = "llm_generation"
    input_data: InputData = Field(..., alias="input") # Allow 'input' as an alias for input_data
    expected_output: ExpectedOutput = Field(..., alias="expected") # Allow 'expected' as an alias
    metric_configs: List[MetricConfig] = Field(..., alias="metrics") # Allow 'metrics' as an alias
    model_config: ModelConfig = Field(default_factory=ModelConfig, alias="model") # Allow 'model' as an alias
    tags: Optional[List[str]] = None

    @validator('input_data', pre=True, always=True)
    def _check_input_alias(cls, v, values):
        if isinstance(v, dict) and 'input' in v and 'input_data' not in v: # Handle if alias is used
             return v['input']
        if 'input' in values and 'input_data' not in values : # top level alias check
            return values['input']
        return v
    
    @validator('expected_output', pre=True, always=True)
    def _check_expected_alias(cls, v, values):
        if isinstance(v, dict) and 'expected' in v and 'expected_output' not in v:
            return v['expected']
        if 'expected' in values and 'expected_output' not in values:
             return values['expected']
        return v

    @validator('metric_configs', pre=True, always=True)
    def _check_metrics_alias(cls, v, values):
        if isinstance(v, dict) and 'metrics' in v and 'metric_configs' not in v:
            return v['metrics']
        if 'metrics' in values and 'metric_configs' not in values:
            return values['metrics']
        return v
    
    @validator('model_config', pre=True, always=True)
    def _check_model_alias(cls, v, values):
        if isinstance(v, dict) and 'model' in v and 'model_config' not in v:
            return v['model']
        if 'model' in values and 'model_config' not in values :
            return values['model']
        # If v is None (i.e., model_config is not provided at all), it will be handled by default_factory
        return v if v is not None else {}


class TestFile(BaseModel):
    __root__: List[TestCase]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]

    def __len__(self):
        return len(self.__root__)

# Example Usage (for testing this file directly):
if __name__ == '__main__':
    sample_yaml_data_list = [
        {
            "id": "french_capital_exact_match_001",
            "name": "Check Capital of France (Exact Match)",
            "description": "Tests if the LLM correctly identifies Paris as the capital of France with an exact match.",
            "type": "llm_generation",
            "input_data": { # or "input"
                "prompt": "What is the capital of France?"
            },
            "expected_output": { # or "expected"
                "exact_match_string": "Paris",
                "reference_texts": [
                    "Paris",
                    "The capital of France is Paris."
                ]
            },
            "metric_configs": [ # or "metrics"
                {"metric": "exact_match"},
                {
                    "metric": "token_count",
                    "parameters": {"count_types": ["completion", "total"]},
                    "thresholds": {"completion_max": 10}
                },
                {"metric": "latency", "threshold": {"value": 1500}}
            ],
            "model_config": { # or "model"
                "provider": "default",
                "model_name": "default",
                "parameters": {"temperature": 0.1}
            },
            "tags": ["geography", "exact_match", "core_knowledge"]
        }
    ]
    
    # Test with alias for input_data
    sample_yaml_data_list_alias = [
        {
            "id": "french_capital_exact_match_002",
            "name": "Check Capital of France (Exact Match) - Alias Test",
            "input": { # Using alias
                "prompt": "What is the capital of France?"
            },
            "expected": { # Using alias
                "exact_match_string": "Paris"
            },
            "metrics": [{"metric": "exact_match"}], # Using alias
            "model": { # Using alias
                "parameters": {"max_tokens": 5}
            }
        }
    ]

    try:
        test_file_obj = TestFile(__root__=sample_yaml_data_list)
        print("Successfully parsed sample_yaml_data_list:")
        for test_case in test_file_obj:
            print(test_case.json(indent=2))

        test_file_obj_alias = TestFile(__root__=sample_yaml_data_list_alias)
        print("\nSuccessfully parsed sample_yaml_data_list_alias:")
        for test_case in test_file_obj_alias:
            print(test_case.json(indent=2))
            
        # Test case where model_config is not provided at all
        sample_no_model_config = [
            {
                "id": "test_no_model_config",
                "name": "Test without model config",
                "input": {"prompt": "Hello"},
                "expected": {"exact_match_string": "Hi"},
                "metrics": [{"metric": "exact_match"}]
            }
        ]
        test_file_no_model_obj = TestFile(__root__=sample_no_model_config)
        print("\nSuccessfully parsed sample_no_model_config:")
        for test_case in test_file_no_model_obj:
            print(test_case.json(indent=2))
            assert test_case.model_config.provider == "default" # Check default factory worked


    except Exception as e:
        print(f"Error parsing: {e}")

# Schemas for evalloop.config.yaml

class ApiKeys(BaseModel):
    openai: Optional[str] = None
    groq: Optional[str] = None
    openrouter: Optional[str] = None
    # Add other provider API keys as needed
    class Config:
        extra = "allow" # Allow other keys for future providers

class DefaultThresholds(BaseModel):
    latency_p95_ms: Optional[int] = None
    cost_per_run_usd: Optional[float] = None
    # Add other default thresholds as needed

class DefaultModelConfig(BaseModel):
    provider: Optional[str] = "openai" # Default provider if not specified elsewhere
    model_name: Optional[str] = "gpt-3.5-turbo" # Default model if not specified elsewhere
    parameters: Optional[ModelConfigParameters] = Field(default_factory=ModelConfigParameters)

class EvalLoopConfig(BaseModel):
    api_keys: Optional[ApiKeys] = Field(default_factory=ApiKeys)
    default_model: Optional[DefaultModelConfig] = Field(default_factory=DefaultModelConfig)
    default_thresholds: Optional[DefaultThresholds] = Field(default_factory=DefaultThresholds)
    # Add other global configurations as needed in the future

    # Placeholder for a method to resolve effective model config later if needed
    # def get_effective_model_config(self, test_case_model_config: Optional[ModelConfig]) -> ModelConfig:
    #     pass 

# Schemas for run.json output

class MetricOutput(BaseModel): # Renaming from MetricResult to avoid confusion in this context, this is for JSON output
    metric_name: str
    score: Union[float, bool, str, Dict[str, Any]]
    passed: Optional[bool] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TestCaseOutput(BaseModel):
    test_case_id: Optional[str] = None # From TestCase.id
    test_case_name: str # From TestCase.name
    test_case_description: Optional[str] = None # From TestCase.description
    
    # Input details (optional, could be configured to be excluded for brevity)
    prompt_sent: Optional[str] = None 
    # Potentially include rendered variables if used

    # LLM Response details
    llm_text_output: Optional[str] = None
    llm_prompt_tokens: Optional[int] = None
    llm_completion_tokens: Optional[int] = None
    llm_total_tokens: Optional[int] = None
    llm_cost: Optional[float] = None
    llm_latency_ms: Optional[float] = None
    llm_model_name_used: Optional[str] = None
    llm_error: Optional[str] = None
    # llm_raw_response: Optional[Any] = None # Usually too verbose for summary, but could be an option

    metrics: List[MetricOutput] = []
    overall_test_passed: Optional[bool] = None # True if all metrics passed (or no failing thresholds)

class RunOutput(BaseModel):
    run_id: str # E.g., a UUID generated for each run
    run_timestamp_utc: str # ISO 8601 format
    evalloop_version: Optional[str] = "0.1.0" # Placeholder, get from actual package version later
    
    # Summary Stats
    total_tests_configured: int
    total_tests_executed: int # Could be less if errors occur early
    total_tests_passed: Optional[int] = None
    total_tests_failed: Optional[int] = None
    # Could add overall run cost, average latency, etc.

    # Configuration used for this run (optional, for reproducibility)
    # effective_global_config: Optional[EvalLoopConfig] = None # Might be too verbose

    test_results: List[TestCaseOutput] = [] 
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, RootModel, ConfigDict, model_validator

# ... (MetricThreshold, MetricConfig, ModelConfigParameters, ModelConfig, InputData, ExpectedOutput, TestCase, TestFile unchanged)

class ApiKeys(BaseModel):
    openai: Optional[str] = None
    groq: Optional[str] = None
    openrouter: Optional[str] = None
    model_config = ConfigDict(extra='allow')

class DefaultThresholds(BaseModel):
    latency_p95_ms: Optional[int] = None
    cost_per_run_usd: Optional[float] = None

class DefaultModelConfig(BaseModel):
    provider: Optional[str] = "openai"
    model_name: Optional[str] = "gpt-3.5-turbo"
    parameters: Optional[ModelConfigParameters] = Field(default_factory=ModelConfigParameters)

class PromptCheckConfig(BaseModel):
    api_keys: Optional[ApiKeys] = Field(default_factory=ApiKeys)
    default_model: Optional[DefaultModelConfig] = Field(default_factory=DefaultModelConfig)
    default_thresholds: Optional[DefaultThresholds] = Field(default_factory=DefaultThresholds)
    output_options: Optional[OutputOptions] = None # Added for output options

# ... (MetricOutput, TestCaseOutput unchanged)

class RunOutput(BaseModel):
    run_id: str 
    run_timestamp_utc: str 
    promptcheck_version: Optional[str] = None
    
    total_tests_configured: int
    total_tests_executed: int 
    total_tests_passed: Optional[int] = None
    total_tests_failed: Optional[int] = None
    test_results: List[TestCaseOutput] = [] 

class RunConfig(BaseModel):
    test_file_paths: List[str]
    config_file_path: Optional[str] = None
    promptcheck_version: Optional[str] = None
    # parallel: bool = True # TODO: Implement parallel execution
    # fail_fast: bool = False # TODO: Implement fail_fast

# Example Usage in __main__ should be updated if it references PromptCheckConfig by old name
# For brevity, I will assume the if __name__ == '__main__' block in schemas.py is for local testing 
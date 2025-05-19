from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, RootModel, ConfigDict, model_validator
from enum import Enum

# Enumeration of supported metric types (for metric names in tests and outputs)
class MetricType(str, Enum):
    EXACT_MATCH = "exact_match"
    TOKEN_COUNT = "token_count"
    LATENCY = "latency"
    REGEX = "regex"
    COST = "cost"
    ROUGE_L_F1 = "rouge_l_f1"
    ROUGE = "rouge_l_f1"  # Alias for common usage, maps to specific ROUGE type
    BLEU = "bleu"
    # Add other metric types as needed (e.g., "rouge", "embedding_similarity", etc.)

class MetricThreshold(BaseModel):
    """Defines threshold values for metrics (e.g., numeric or boolean pass criteria)."""
    # Flexible to allow different kinds of thresholds for various metrics
    f_score: Optional[float] = None          # e.g., used for rouge F1-score thresholds
    value: Optional[Union[int, float]] = None  # generic value threshold (e.g., latency in ms)
    completion_max: Optional[int] = None     # specific threshold for maximum completion tokens
    operator: Literal[">=", "<="] = ">="     # comparison operator for threshold checks
    # Additional threshold types can be added as needed

class MetricConfig(BaseModel):
    """Configuration for a single metric to evaluate in a test case."""
    metric: MetricType                       # metric type/name to use (e.g., exact_match, latency)
    parameters: Optional[Dict[str, Any]] = None  # additional parameters for the metric, if any
    # 'thresholds' can be specified to define pass/fail criteria for this metric
    thresholds: Optional[MetricThreshold] = None

    @model_validator(mode='before')
    @classmethod
    def _populate_thresholds_from_alias(cls, data: Any) -> Any:
        """Allow using 'threshold' as an alias for 'thresholds' in input data for convenience."""
        if isinstance(data, dict):
            # If 'thresholds' is not present but 'threshold' is provided, move it to 'thresholds'
            if 'thresholds' not in data and 'threshold' in data:
                data['thresholds'] = data.pop('threshold')
        return data

class ModelConfigParameters(BaseModel):
    """Model-specific parameter overrides for LLM calls (e.g., temperature, max_tokens)."""
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature for the LLM call.")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum number of tokens to generate.")
    timeout_s: Optional[float] = Field(None, gt=0, description="Timeout (seconds) for each LLM call attempt, overriding defaults.")
    retry_attempts: Optional[int] = Field(None, ge=0, le=5, description="Number of retry attempts for the LLM call, overriding defaults.")
    # Allow any other model parameters (will be tolerated but not explicitly defined)
    model_config = ConfigDict(extra='allow')

class ModelConfig(BaseModel):
    """Specifies which provider/model to use and any model parameters for a test (or default)."""
    provider: str = "default"
    model_name: str = "default"
    parameters: Optional[ModelConfigParameters] = Field(default_factory=ModelConfigParameters)

class InputData(BaseModel):
    """Input prompt and optional variables for a test case."""
    prompt: str
    variables: Optional[Dict[str, Any]] = None

class ExpectedOutput(BaseModel):
    """Defines the expected output for a test case (for exact match, regex, or reference texts)."""
    exact_match_string: Optional[str] = None       # expected output text for exact match comparison
    regex_pattern: Optional[str] = None            # regex pattern that the output should match
    reference_texts: Optional[List[str]] = None    # list of reference texts for similarity metrics (e.g., embeddings)
    # Allow additional structures for other metric types if needed in the future
    model_config = ConfigDict(extra='allow')

class TestCase(BaseModel):
    """A single test case specification for evaluating the model."""
    __test__ = False # Tell pytest not to collect this as a test class

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    type: str = "llm_generation"  # default test type
    input_data: InputData        # input prompt and variables (alias 'input' in YAML)
    expected_output: ExpectedOutput  # expected result definitions (alias 'expected' in YAML)
    metric_configs: List[MetricConfig]  # list of metrics to evaluate (alias 'metrics' in YAML)
    case_model_config: Optional[ModelConfig] = Field(None, alias="model_config")  # optional model override for this test (alias 'model')
    tags: Optional[List[str]] = None   # arbitrary tags for categorizing or filtering tests

    # (Optionally, a model_validator could be added to handle 'input'/'expected' alias mapping if needed)

class TestFile(RootModel[List[TestCase]]):
    """
    A collection of TestCase objects, corresponding to an entire test file.
    Inherits from Pydantic's RootModel to treat the list of test cases as the root object.
    """
    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)

# Schemas for the global configuration (e.g., promptcheck.config.yaml)
class APIKeys(BaseModel):
    """API keys for various providers (keys are optional and can be left None)."""
    openai: Optional[str] = None
    groq: Optional[str] = None
    openrouter: Optional[str] = None
    # Allow other provider API keys as needed
    model_config = ConfigDict(extra='allow')  # allow extra keys for future providers

class DefaultThresholds(BaseModel):
    """Default threshold values for metrics at a global level (applied if test cases don't override)."""
    latency_p95_ms: Optional[int] = None    # e.g., 95th percentile latency threshold in milliseconds
    cost_per_run_usd: Optional[float] = None  # e.g., maximum allowed cost per run in USD
    # Add other default thresholds as needed

class DefaultModelConfig(BaseModel):
    """Default model configuration to use if not specified in an individual test case."""
    provider: Optional[str] = "openai"        # default provider name (if not given elsewhere)
    model_name: Optional[str] = "gpt-3.5-turbo"  # default model name (if not given elsewhere)
    parameters: Optional[ModelConfigParameters] = Field(default_factory=ModelConfigParameters)

class OutputOptions(BaseModel):
    """Options to control the level of detail in output results."""
    include_prompt_sent: bool = True       # include the prompt that was sent to the LLM in the output
    include_raw_response: bool = False     # include the raw LLM response object (may be very verbose)
    include_metric_details: bool = True    # include detailed info for metrics (beyond basic score and pass/fail)
    # Additional output toggles can be added here as needed
    model_config = ConfigDict(extra='allow')  # allow extra fields for future output options

class PromptCheckConfig(BaseModel):
    """Global configuration settings for the prompt check evaluation (usually loaded from a YAML config file)."""
    api_keys: Optional[APIKeys] = Field(default_factory=APIKeys)
    default_model: Optional[DefaultModelConfig] = Field(default_factory=DefaultModelConfig)
    default_thresholds: Optional[DefaultThresholds] = Field(default_factory=DefaultThresholds)
    output_options: Optional[OutputOptions] = Field(default_factory=OutputOptions)
    # Add other global configurations as needed in the future

# Schemas for run output (e.g., the structure of results in run.json)
class MetricOutput(BaseModel):
    """Result of a single metric evaluation for a test case, as part of the output summary."""
    metric_name: MetricType                       # metric name corresponding to MetricConfig.metric
    score: Union[float, bool, str, Dict[str, Any]]  # the metric's result score (could be numeric, boolean, text, or dict)
    passed: Optional[bool] = None                # whether this metric passed the threshold (if a threshold was defined)
    details: Optional[Dict[str, Any]] = None     # any additional details or sub-metrics from the metric evaluation
    error: Optional[str] = None                  # error message if the metric evaluation failed or was not run

class TestCaseOutput(BaseModel):
    """Aggregated results for a single test case execution, including LLM outputs and metrics."""
    test_case_id: Optional[str] = None            # echoes TestCase.id
    test_case_name: str                           # echoes TestCase.name
    test_case_description: Optional[str] = None   # echoes TestCase.description
    # Input details (may be omitted for brevity based on OutputOptions)
    prompt_sent: Optional[str] = None             # the actual prompt sent to the LLM (after variable substitution)
    # (If variables were used, those could be included as well in the future)
    # LLM response details
    llm_text_output: Optional[str] = None         # the text output from the LLM
    llm_prompt_tokens: Optional[int] = None
    llm_completion_tokens: Optional[int] = None
    llm_total_tokens: Optional[int] = None
    llm_cost: Optional[float] = None              # estimated cost for this call (if applicable)
    llm_latency_ms: Optional[float] = None        # latency in milliseconds for the LLM call
    llm_model_name_used: Optional[str] = None     # which model was actually used (could differ from requested if aliasing)
    llm_error: Optional[str] = None               # error message if the LLM call failed
    # llm_raw_response: Optional[Any] = None      # (optional raw response; controlled by OutputOptions, typically omitted)
    metrics: List[MetricOutput] = []              # results for each metric evaluated
    overall_test_passed: Optional[bool] = None    # True if all metrics passed (or if no failing thresholds)

class RunOutput(BaseModel):
    """Summary of an entire evaluation run, containing results for all test cases and aggregate stats."""
    run_id: str                                   # unique identifier for the run (e.g., a UUID)
    run_timestamp_utc: str                        # timestamp of the run (ISO 8601 format)
    promptcheck_version: Optional[str] = "0.1.0"  # version of the PromptCheck tool (placeholder, to be updated from package version)
    # Summary statistics for the run
    total_tests_configured: int
    total_tests_executed: int                     # could be less than configured if some were skipped or on error
    total_tests_passed: Optional[int] = None
    total_tests_failed: Optional[int] = None
    # (Overall run cost, average latency, etc. could be added here)
    # Configuration used for this run (optional, for reproducibility)
    # effective_global_config: Optional[PromptCheckConfig] = None  # (could be included for full context, if not too verbose)
    test_results: List[TestCaseOutput] = []       # list of outputs for each test case in the run

class RunConfig(BaseModel):
    test_file_paths: List[str]
    config_file_path: Optional[str] = None
    promptcheck_version: Optional[str] = None
    # parallel: bool = True # TODO: Implement parallel execution
    # fail_fast: bool = False # TODO: Implement fail_fast

# Example Usage in __main__ should be updated if it references PromptCheckConfig by old name
# For brevity, I will assume the if __name__ == '__main__' block in schemas.py is for local testing 
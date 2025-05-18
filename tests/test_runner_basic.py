import pytest
from pathlib import Path

from promptcheck.core.schemas import TestCase, PromptCheckConfig, InputData, ExpectedOutput, MetricConfig, ModelConfig
from promptcheck.core.runner import execute_eval_run

# S3.2: tests/test_runner_basic.py
def test_single_exact_match(tmp_path: Path):
    """Tests a single exact match test case using the DummyProvider."""
    test_case = TestCase(
        name="Exact Match Test with Dummy Provider",
        input_data=InputData(prompt="Say hi"),
        expected_output=ExpectedOutput(exact_match_string="Hello world"),
        metric_configs=[MetricConfig(metric="exact_match")],
        # Use the alias 'model_config' for the keyword argument,
        # Pydantic should map this to the case_model_config field.
        model_config=ModelConfig(provider="dummy", model_name="dummy/1") 
        # The example from GPT used model_config directly, which relies on alias parsing for case_model_config
        # model_config={"provider": "dummy", "model_name": "dummy/1"} # This would also work due to alias
    )
    
    # Use a default PromptCheckConfig; API keys are not needed for DummyProvider
    config = PromptCheckConfig()
    
    # The execute_eval_run function expects a list of TestCase objects
    run_result = execute_eval_run(config, [test_case])
    
    assert run_result.total_tests_executed == 1
    assert run_result.total_tests_failed == 0
    assert run_result.total_tests_passed == 1
    assert len(run_result.test_results) == 1
    
    test_output = run_result.test_results[0]
    assert test_output.overall_test_passed is True
    assert test_output.llm_text_output == "Hello world"
    assert test_output.metrics[0].metric_name == "exact_match"
    assert test_output.metrics[0].passed is True
    assert test_output.metrics[0].score is True 
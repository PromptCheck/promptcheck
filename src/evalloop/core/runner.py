from pathlib import Path
from typing import List, Optional, Tuple
import typer # For typer.echo and typer.secho, consider passing a logger or callback for output
import uuid
import datetime

from evalloop.utils.file_handler import load_evalloop_config, ConfigFileLoadError, load_test_cases_from_yaml, TestFileLoadError
from evalloop.core.schemas import (
    EvalLoopConfig, TestCase, MetricOutput, TestCaseOutput, RunOutput,
    ModelConfig as TestCaseModelConfig # Alias for clarity
)
from evalloop.core.providers import LLMResponse, get_llm_provider
from evalloop.core.metrics import MetricResult, get_metric_calculator

class EvalLoopRunner:
    def __init__(self, config: EvalLoopConfig):
        self.global_config = config
        self.provider_cache: Dict[str, Optional[LLMProvider]] = {} # Cache for provider instances

    def _get_provider_instance(self, provider_name: str) -> Optional[LLMProvider]:
        if provider_name not in self.provider_cache:
            self.provider_cache[provider_name] = get_llm_provider(provider_name, self.global_config)
        return self.provider_cache[provider_name]

    def _resolve_model_config(self, test_case_model_cfg: TestCaseModelConfig) -> TestCaseModelConfig:
        provider_name_to_use = test_case_model_cfg.provider
        model_name_to_use = test_case_model_cfg.model_name
        
        global_default_provider = "openai" # Ultimate fallback if no global default
        global_default_model = "gpt-3.5-turbo" # Ultimate fallback

        if self.global_config.default_model:
            global_default_provider = self.global_config.default_model.provider or global_default_provider
            global_default_model = self.global_config.default_model.model_name or global_default_model

        if provider_name_to_use == "default":
            provider_name_to_use = global_default_provider
        if model_name_to_use == "default":
            model_name_to_use = global_default_model
        
        # Merge parameters: global default -> test case default -> test case specific
        # Start with a fresh ModelConfigParameters if global_default_model_cfg.parameters is None
        base_params_dict = {}
        if self.global_config.default_model and self.global_config.default_model.parameters:
            base_params_dict = self.global_config.default_model.parameters.model_dump(exclude_none=True)

        resolved_params_dict = base_params_dict.copy()
        if test_case_model_cfg.parameters:
            test_specific_params_dict = test_case_model_cfg.parameters.model_dump(exclude_none=True)
            resolved_params_dict.update(test_specific_params_dict)
        
        resolved_params = TestCaseModelConfig().parameters.__class__(**resolved_params_dict)

        return TestCaseModelConfig(
            provider=provider_name_to_use,
            model_name=model_name_to_use,
            parameters=resolved_params
        )

    def run_test_case(self, test_case: TestCase) -> TestCaseOutput:
        typer.echo(f"  Executing: {test_case.name} (ID: {test_case.id or 'N/A'})")
        current_llm_response: Optional[LLMResponse] = None
        actual_metric_outputs: List[MetricOutput] = []
        test_case_overall_passed = True # Assume true, set to false on any metric failure

        resolved_test_model_config = self._resolve_model_config(test_case.model_config)
        provider_name_to_use = resolved_test_model_config.provider
        model_name_to_use = resolved_test_model_config.model_name

        llm_provider = self._get_provider_instance(provider_name_to_use)

        if not llm_provider:
            typer.secho(f"    Error: Provider '{provider_name_to_use}' not found. Skipping LLM call.", fg=typer.colors.RED)
            current_llm_response = LLMResponse(error=f"Provider '{provider_name_to_use}' not found.", model_name_used=model_name_to_use)
            test_case_overall_passed = False
        else:
            typer.echo(f"    Using provider: {llm_provider.provider_name}, Model: {model_name_to_use}")
            prompt_to_send = test_case.input_data.prompt
            # TODO: Add variable rendering for prompt_to_send if test_case.input_data.variables exist
            
            current_llm_response = llm_provider.make_llm_call(
                test_case_name=test_case.name,
                prompt=prompt_to_send,
                resolved_model_config=resolved_test_model_config
            )
            if current_llm_response.error:
                typer.secho(f"    LLM call failed: {current_llm_response.error}", fg=typer.colors.RED)
                test_case_overall_passed = False

        if current_llm_response:
            for mc_config_obj in test_case.metric_configs:
                metric_calculator = get_metric_calculator(mc_config_obj.metric, mc_config_obj.model_dump(exclude_none=True))
                if not metric_calculator:
                    typer.secho(f"    Warning: Metric calculator for '{mc_config_obj.metric}' not found. Skipping metric.", fg=typer.colors.YELLOW)
                    actual_metric_outputs.append(MetricOutput(metric_name=mc_config_obj.metric, score="N/A", error="Calculator not found"))
                    continue
                
                metric_result: MetricResult = metric_calculator.calculate(test_case, current_llm_response)
                actual_metric_outputs.append(MetricOutput(**metric_result.model_dump()))
                
                if metric_result.passed is False:
                    test_case_overall_passed = False
        else:
            test_case_overall_passed = False # Should not happen due to error handling above
            typer.secho("    Critical error: No LLMResponse object available.", fg=typer.colors.RED)

        return TestCaseOutput(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            test_case_description=test_case.description,
            prompt_sent=test_case.input_data.prompt,
            llm_text_output=current_llm_response.text_output if current_llm_response else None,
            llm_prompt_tokens=current_llm_response.prompt_tokens if current_llm_response else None,
            llm_completion_tokens=current_llm_response.completion_tokens if current_llm_response else None,
            llm_total_tokens=current_llm_response.total_tokens if current_llm_response else None,
            llm_cost=current_llm_response.cost if current_llm_response else None,
            llm_latency_ms=current_llm_response.latency_ms if current_llm_response else None,
            llm_model_name_used=current_llm_response.model_name_used if current_llm_response else model_name_to_use,
            llm_error=current_llm_response.error if current_llm_response else "Provider not found or pre-call error",
            metrics=actual_metric_outputs,
            overall_test_passed=test_case_overall_passed
        )

def execute_eval_run(config: EvalLoopConfig, all_test_cases: List[TestCase]) -> RunOutput:
    typer.echo("\n--- Beginning Test Execution ---")
    runner = EvalLoopRunner(config)
    executed_test_results: List[TestCaseOutput] = []
    tests_passed_count = 0
    tests_failed_count = 0

    for i, test_case in enumerate(all_test_cases):
        # Note: typer.echo is used here directly from runner.py. Consider callbacks/logging for flexibility.
        test_output = runner.run_test_case(test_case)
        executed_test_results.append(test_output)
        if test_output.overall_test_passed:
            tests_passed_count += 1
            typer.secho(f"    Test '{test_case.name}' PASSED.", fg=typer.colors.GREEN)
        else:
            tests_failed_count += 1
            typer.secho(f"    Test '{test_case.name}' FAILED.", fg=typer.colors.RED)
    
    typer.echo("--- Test Execution Finished ---")

    run_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    ev_version = "0.1.0-dev"
    try:
        import importlib.metadata
        ev_version = importlib.metadata.version("evalloop")
    except importlib.metadata.PackageNotFoundError:
        pass 
        
    return RunOutput(
        run_id=run_id,
        run_timestamp_utc=timestamp,
        evalloop_version=ev_version,
        total_tests_configured=len(all_test_cases),
        total_tests_executed=len(executed_test_results),
        total_tests_passed=tests_passed_count,
        total_tests_failed=tests_failed_count,
        test_results=executed_test_results
    )

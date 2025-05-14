import typer
from pathlib import Path
from typing import List, Optional, Any
import glob # For finding test files
import datetime
import uuid
import json

from evalloop.utils.file_handler import load_evalloop_config, ConfigFileLoadError, load_test_cases_from_yaml, TestFileLoadError
from evalloop.core.schemas import EvalLoopConfig, TestCase, MetricOutput, TestCaseOutput, RunOutput, ModelConfig as TestCaseModelConfig # Alias for clarity
from evalloop.core.providers import LLMResponse, get_llm_provider # Import factory
from evalloop.core.metrics import MetricResult, get_metric_calculator # Import factory

app = typer.Typer(name="run", help="Run an evaluation suite against your LLM prompts and models.")

DEFAULT_TESTS_DIR = "tests"

@app.command()
def run(
    config_path: Path = typer.Option(
        Path("."), 
        "--config", "-c", 
        help="Path to the directory containing evalloop.config.yaml, or path to the config file itself.",
        exists=True,
        resolve_path=True
    ),
    test_files_or_dirs: Optional[List[Path]] = typer.Argument(
        None, 
        help="Paths to specific test YAML files or directories containing test YAML files. Defaults to the 'tests/' directory.",
        exists=True,
        resolve_path=True
    ),
    # TODO: Add more options later, e.g., --tags, --output-dir, --verbose
):
    """
    Runs evaluation tests based on the provided configuration and test files.
    """
    typer.echo("Starting EvalLoop run...")

    # Determine config directory
    if config_path.is_file() and config_path.name == "evalloop.config.yaml":
        config_dir = config_path.parent
    elif config_path.is_dir():
        config_dir = config_path
    else:
        typer.secho(f"Error: Invalid config path '{config_path}'. Must be a directory or evalloop.config.yaml.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Load EvalLoop configuration
    try:
        config = load_evalloop_config(config_dir)
        typer.echo(f"Loaded configuration from: {config_dir / 'evalloop.config.yaml'}")
        if config.api_keys and config.api_keys.openai:
            typer.echo("OpenAI API key found (partially hidden): " + "sk-..." + config.api_keys.openai[-4:])
        if config.default_model:
             typer.echo(f"Default model: {config.default_model.provider} -> {config.default_model.model_name}")

    except ConfigFileLoadError as e:
        typer.secho(f"Error loading configuration: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # Gather test files
    actual_test_files: List[Path] = []
    if not test_files_or_dirs:
        default_dir = Path(DEFAULT_TESTS_DIR)
        if default_dir.is_dir():
            typer.echo(f"No specific test files provided, looking in default directory: ./{DEFAULT_TESTS_DIR}")
            for pattern in ("*.yaml", "*.yml"):
                actual_test_files.extend(list(default_dir.rglob(pattern)))
        else:
            typer.echo(f"Default test directory ./{DEFAULT_TESTS_DIR} not found. Please provide test files or create it.")
    else:
        for path_item in test_files_or_dirs:
            if path_item.is_file() and (path_item.suffix == ".yaml" or path_item.suffix == ".yml"):
                actual_test_files.append(path_item)
            elif path_item.is_dir():
                for pattern in ("*.yaml", "*.yml"):
                    actual_test_files.extend(list(path_item.rglob(pattern)))
            else:
                typer.echo(f"Warning: Path '{path_item}' is not a valid YAML file or directory. Skipping.")

    if not actual_test_files:
        typer.secho("No test files found to execute.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0) # Not an error, but nothing to do

    typer.echo(f"Found {len(actual_test_files)} test file(s) to process:")
    for tf in actual_test_files:
        typer.echo(f"  - {tf.relative_to(Path.cwd()) if tf.is_absolute() else tf}")

    # Load and process test cases
    all_test_cases: List[TestCase] = []
    for test_file_path in actual_test_files:
        try:
            typer.echo(f"\nLoading test cases from: {test_file_path.name}...")
            test_file_content = load_test_cases_from_yaml(test_file_path)
            if not test_file_content.__root__:
                typer.echo(f"  No test cases found in {test_file_path.name}.")
                continue
            all_test_cases.extend(test_file_content.__root__)
            typer.echo(f"  Successfully loaded {len(test_file_content)} test case(s) from {test_file_path.name}.")
        except TestFileLoadError as e:
            typer.secho(f"Error loading test file {test_file_path.name}: {e}\nSkipping this file.", fg=typer.colors.RED)
            continue # Skip to the next file if one is invalid
    
    if not all_test_cases:
        typer.secho("No valid test cases were loaded from any file.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"\nTotal test cases to execute: {len(all_test_cases)}")

    # --- Core Test Execution Engine ---
    typer.echo("\n--- Beginning Test Execution ---")
    
    executed_test_results: List[TestCaseOutput] = []
    tests_passed_count = 0
    tests_failed_count = 0

    # Prepare global config parts that might be needed repeatedly
    global_api_keys = config.api_keys
    global_default_model_cfg = config.default_model

    for i, test_case in enumerate(all_test_cases):
        typer.echo(f"Executing test {i+1}/{len(all_test_cases)}: {test_case.name} (ID: {test_case.id or 'N/A'})")
        
        current_llm_response: Optional[LLMResponse] = None
        actual_metric_outputs: List[MetricOutput] = []
        test_case_overall_passed = True # Assume true, set to false on any metric failure

        # 1. Resolve effective model config & provider
        provider_name_to_use = test_case.model_config.provider
        if provider_name_to_use == "default":
            provider_name_to_use = global_default_model_cfg.provider if global_default_model_cfg else "openai" # Fallback if no global default
        
        model_name_to_use = test_case.model_config.model_name
        if model_name_to_use == "default":
            model_name_to_use = global_default_model_cfg.model_name if global_default_model_cfg else "gpt-3.5-turbo" # Fallback

        # Create a resolved ModelConfig for the provider call
        # Start with global default parameters, then overlay test-case model parameters
        resolved_params = global_default_model_cfg.parameters.model_copy() if global_default_model_cfg and global_default_model_cfg.parameters else TestCaseModelConfig().parameters
        if test_case.model_config.parameters:
            test_specific_params_dict = test_case.model_config.parameters.model_dump(exclude_none=True)
            # Update resolved_params by iterating through test_specific_params_dict
            # This ensures that Pydantic model fields are updated correctly
            current_resolved_params_dict = resolved_params.model_dump()
            current_resolved_params_dict.update(test_specific_params_dict)
            resolved_params = type(resolved_params)(**current_resolved_params_dict)
            
        resolved_test_model_config = TestCaseModelConfig(
            provider=provider_name_to_use, 
            model_name=model_name_to_use,
            parameters=resolved_params
        )

        # 2. Get LLM provider instance
        llm_provider = get_llm_provider(provider_name_to_use, config)

        if not llm_provider:
            typer.secho(f"  Error: Provider '{provider_name_to_use}' not found for test '{test_case.name}'. Skipping LLM call.", fg=typer.colors.RED)
            current_llm_response = LLMResponse(error=f"Provider '{provider_name_to_use}' not found.", model_name_used=model_name_to_use)
            test_case_overall_passed = False
        else:
            typer.echo(f"  Using provider: {llm_provider.provider_name}, Model: {model_name_to_use}")
            # 3. Prepare input (simple prompt for now, rendering can be added later)
            prompt_to_send = test_case.input_data.prompt
            # TODO: Add variable rendering for prompt_to_send if test_case.input_data.variables exist
            
            # 4. Call LLM provider
            current_llm_response = llm_provider.make_llm_call(
                test_case_name=test_case.name,
                prompt=prompt_to_send,
                resolved_model_config=resolved_test_model_config
            )
            if current_llm_response.error:
                typer.secho(f"  LLM call failed: {current_llm_response.error}", fg=typer.colors.RED)
                test_case_overall_passed = False # Mark test as failed if LLM call fails

        # 5. Calculate metrics
        if current_llm_response: # Ensure we have a response (even if it's an error response)
            for mc_config_obj in test_case.metric_configs:
                # mc_config_obj is a MetricConfig Pydantic model.
                # get_metric_calculator expects the raw dict from the YAML for that metric.
                # We need to find the original dict that Pydantic parsed into mc_config_obj
                # This is a bit tricky. For now, let's pass mc_config_obj.model_dump()
                # The Metric constructor in metrics.py takes metric_config: Dict[str, Any]
                metric_calculator = get_metric_calculator(mc_config_obj.metric, mc_config_obj.model_dump(exclude_none=True))
                
                if not metric_calculator:
                    typer.secho(f"  Warning: Metric calculator for '{mc_config_obj.metric}' not found. Skipping metric.", fg=typer.colors.YELLOW)
                    actual_metric_outputs.append(MetricOutput(metric_name=mc_config_obj.metric, score="N/A", error="Calculator not found"))
                    continue

                metric_result: MetricResult = metric_calculator.calculate(test_case, current_llm_response)
                actual_metric_outputs.append(MetricOutput(**metric_result.model_dump()))
                
                if metric_result.passed is False: # Note: None means not applicable or not failed
                    test_case_overall_passed = False
        else: # Should not happen if llm_provider error handling is correct
            test_case_overall_passed = False
            typer.secho("  Critical error: No LLMResponse object available after provider interaction attempt.", fg=typer.colors.RED)

        if test_case_overall_passed:
            tests_passed_count += 1
        else:
            tests_failed_count += 1
        
        # Create TestCaseOutput
        test_output = TestCaseOutput(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            test_case_description=test_case.description,
            prompt_sent=test_case.input_data.prompt, # Store original prompt for now
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
        executed_test_results.append(test_output)
        typer.secho(f"  Test '{test_case.name}' completed. Overall Passed: {test_case_overall_passed}", fg=typer.colors.GREEN if test_case_overall_passed else typer.colors.RED)
    
    typer.echo("--- Test Execution Finished ---")
    # --- End Core Test Execution Engine ---

    # Prepare RunOutput object
    run_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Placeholder for actual evalloop version
    ev_version = "0.1.0-dev"
    try:
        import importlib.metadata
        ev_version = importlib.metadata.version("evalloop")
    except importlib.metadata.PackageNotFoundError:
        pass # Keep placeholder if not installed
        
    run_output_data = RunOutput(
        run_id=run_id,
        run_timestamp_utc=timestamp,
        evalloop_version=ev_version,
        total_tests_configured=len(all_test_cases),
        total_tests_executed=len(executed_test_results),
        total_tests_passed=tests_passed_count,
        total_tests_failed=tests_failed_count,
        test_results=executed_test_results
    )

    # Output run.json artifact
    output_dir = Path(".") # TODO: Make this configurable via CLI option --output-dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_filename = f"evalloop_run_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    json_file_path = output_dir / json_filename

    try:
        with open(json_file_path, "w") as f:
            # Pydantic's .model_dump_json is preferred for Pydantic V2
            # For Pydantic V1 it was .json()
            # Assuming Pydantic V2+ from typical modern installs with `poetry add pydantic`
            f.write(run_output_data.model_dump_json(indent=2))
        typer.echo(f"\nRun results saved to: {json_file_path}")
    except AttributeError: # Fallback for Pydantic V1 if model_dump_json not found
        try:
            with open(json_file_path, "w") as f:
                f.write(run_output_data.json(indent=2)) # Pydantic V1
            typer.echo(f"\nRun results saved to: {json_file_path} (using Pydantic V1 .json() method)")
        except Exception as e:
            typer.secho(f"Error writing JSON output: {e}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Error writing JSON output: {e}", fg=typer.colors.RED)

    typer.echo("\nEvalLoop run completed.")

if __name__ == "__main__":
    # Example of how to run this for local testing:
    # Ensure you have an evalloop.config.yaml and a tests/ directory with some .yaml files
    # You might need to `cd` to the project root if you are not already there.
    # CLI: python evalloop/cli/run_cmd.py ./tests
    # or if installed: evalloop run ./tests
    app()

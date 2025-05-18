import typer
from pathlib import Path
from typing import List, Optional
import sys 
import datetime 
import json 

from promptcheck.utils.file_handler import load_promptcheck_config, ConfigFileLoadError, load_test_cases_from_yaml, TestFileLoadError
from promptcheck.core.runner import execute_eval_run 
from promptcheck.core.schemas import RunOutput, TestCase 

DEFAULT_TESTS_DIR = "tests"
CONFIG_FILENAME = "promptcheck.config.yaml"

def run(
    config_path_cli: Path = typer.Option(
        Path("."), 
        "--config", "-c", 
        help=f"Path to the directory containing {CONFIG_FILENAME}, or path to the config file itself.",
        exists=True, resolve_path=True, show_default="Current directory"
    ),
    test_files_or_dirs: Optional[List[Path]] = typer.Argument(
        None, 
        help="Paths to specific test YAML files or directories containing test YAML files. Defaults to the 'tests/' directory.",
        exists=True, resolve_path=True, show_default="tests/ directory"
    ),
    output_dir_cli: Path = typer.Option(
        Path("."), "--output-dir", "-o",
        help="Directory to save the run JSON results file.",
        file_okay=False, dir_okay=True, writable=True, resolve_path=True, show_default="Current directory"
    ),
    soft_fail: bool = typer.Option(False, "--soft-fail", help="Exit with code 0 even if tests fail...", show_default=False)
):
    """
    Runs evaluation tests based on the provided configuration and test files.
    """
    typer.echo("Starting PromptCheck run...")

    if config_path_cli.is_file() and config_path_cli.name == CONFIG_FILENAME:
        config_dir = config_path_cli.parent
    elif config_path_cli.is_dir():
        config_dir = config_path_cli
    else:
        typer.secho(f"Error: Invalid config path '{config_path_cli}'. Must be a directory or {CONFIG_FILENAME}.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        config = load_promptcheck_config(config_dir)
        typer.echo(f"Loaded configuration from: {config_dir / CONFIG_FILENAME}")
    except ConfigFileLoadError as e:
        typer.secho(f"Error loading configuration: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # ... (file discovery logic unchanged) ...
    actual_test_files: List[Path] = []
    if not test_files_or_dirs:
        default_dir_path = Path.cwd() / DEFAULT_TESTS_DIR
        if default_dir_path.is_dir():
            typer.echo(f"No specific test files provided, looking in default directory: {default_dir_path.relative_to(Path.cwd())}")
            for pattern in ("*.yaml", "*.yml"):
                actual_test_files.extend(list(default_dir_path.rglob(pattern)))
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
        raise typer.Exit(code=0)

    typer.echo(f"Found {len(actual_test_files)} test file(s) to process:")
    for tf in actual_test_files:
        typer.echo(f"  - {tf.relative_to(Path.cwd()) if tf.is_absolute() else tf}")

    all_test_cases: List[TestCase] = []
    for test_file_path in actual_test_files:
        try:
            typer.echo(f"\nLoading test cases from: {test_file_path.name}...")
            test_file_content = load_test_cases_from_yaml(test_file_path)
            if not test_file_content.root:
                typer.echo(f"  No test cases found in {test_file_path.name}.")
                continue
            all_test_cases.extend(test_file_content.root)
            typer.echo(f"  Successfully loaded {len(test_file_content)} test case(s) from {test_file_path.name}.")
        except TestFileLoadError as e:
            typer.secho(f"Error loading test file {test_file_path.name}: {e}\nSkipping this file.", fg=typer.colors.RED)
            continue 
    
    if not all_test_cases:
        typer.secho("No valid test cases were loaded from any file.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"\nTotal test cases to execute: {len(all_test_cases)}")

    run_output_data: RunOutput = execute_eval_run(config, all_test_cases)
    
    output_dir_cli.mkdir(parents=True, exist_ok=True)
    json_filename = f"promptcheck_run_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    json_file_path = output_dir_cli / json_filename

    try:
        with open(json_file_path, "w") as f:
            json_content = run_output_data.model_dump_json(indent=2)
            f.write(json_content)
        typer.echo(f"\nRun results saved to: {json_file_path}")
    except AttributeError: 
        try:
            with open(json_file_path, "w") as f:
                json_content = run_output_data.json(indent=2) # type: ignore
                f.write(json_content)
            typer.echo(f"\nRun results saved to: {json_file_path} (using Pydantic V1 .json() method)")
        except Exception as e_v1:
            typer.secho(f"Error writing JSON output (Pydantic V1 fallback): {e_v1}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Error writing JSON output: {e}", fg=typer.colors.RED)

    typer.echo("\nPromptCheck run completed.")

    if run_output_data.total_tests_failed is not None and run_output_data.total_tests_failed > 0:
        typer.secho(f"{run_output_data.total_tests_failed} test(s) failed.", fg=typer.colors.RED)
        if not soft_fail:
            sys.exit(1) 
        else:
            typer.echo("Soft fail enabled: Exiting with code 0 despite test failures.")
            sys.exit(0)
    else:
        typer.secho("All tests executed passed (or had no failing thresholds defined).", fg=typer.colors.GREEN)
        sys.exit(0) 
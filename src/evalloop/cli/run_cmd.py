import typer
from pathlib import Path
from typing import List, Optional
import sys # For sys.exit
import datetime # For json_filename
import json # For writing json

from evalloop.utils.file_handler import load_evalloop_config, ConfigFileLoadError, load_test_cases_from_yaml, TestFileLoadError
from evalloop.core.runner import execute_eval_run # Import the new runner function
from evalloop.core.schemas import RunOutput # For type hinting

app = typer.Typer(name="run", help="Run an evaluation suite against your LLM prompts and models.")

DEFAULT_TESTS_DIR = "tests"

@app.command()
def run(
    config_path_cli: Path = typer.Option(
        Path("."), 
        "--config", "-c", 
        help="Path to the directory containing evalloop.config.yaml, or path to the config file itself.",
        exists=True,
        resolve_path=True,
        show_default="Current directory"
    ),
    test_files_or_dirs: Optional[List[Path]] = typer.Argument(
        None, 
        help="Paths to specific test YAML files or directories containing test YAML files. Defaults to the 'tests/' directory.",
        exists=True,
        resolve_path=True,
        show_default="tests/ directory"
    ),
    output_dir_cli: Path = typer.Option(
        Path("."),
        "--output-dir", "-o",
        help="Directory to save the run.json results file.",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        show_default="Current directory"
    )
    # TODO: Add more options later, e.g., --tags, --verbose, --soft-fail
):
    """
    Runs evaluation tests based on the provided configuration and test files.
    """
    typer.echo("Starting EvalLoop run...")

    # Determine config directory
    if config_path_cli.is_file() and config_path_cli.name == "evalloop.config.yaml":
        config_dir = config_path_cli.parent
    elif config_path_cli.is_dir():
        config_dir = config_path_cli
    else:
        typer.secho(f"Error: Invalid config path '{config_path_cli}'. Must be a directory or evalloop.config.yaml.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Load EvalLoop configuration
    try:
        config = load_evalloop_config(config_dir)
        typer.echo(f"Loaded configuration from: {config_dir / 'evalloop.config.yaml'}")
        # Basic config loaded info can be logged by the runner if needed or via a verbose flag
    except ConfigFileLoadError as e:
        typer.secho(f"Error loading configuration: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # Gather test files
    actual_test_files: List[Path] = []
    if not test_files_or_dirs:
        default_dir_path = Path.cwd() / DEFAULT_TESTS_DIR # Use absolute path for default
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
        raise typer.Exit(code=0) # Not an error, but nothing to do

    typer.echo(f"Found {len(actual_test_files)} test file(s) to process:")
    for tf in actual_test_files:
        typer.echo(f"  - {tf.relative_to(Path.cwd()) if tf.is_absolute() else tf}")

    # Load and process test cases from all files
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
            continue 
    
    if not all_test_cases:
        typer.secho("No valid test cases were loaded from any file.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"\nTotal test cases to execute: {len(all_test_cases)}")

    # Execute the evaluation run using the core runner
    run_output_data: RunOutput = execute_eval_run(config, all_test_cases)
    
    # Output run.json artifact
    output_dir_cli.mkdir(parents=True, exist_ok=True)
    json_filename = f"evalloop_run_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    json_file_path = output_dir_cli / json_filename

    try:
        with open(json_file_path, "w") as f:
            json_content = run_output_data.model_dump_json(indent=2)
            f.write(json_content)
        typer.echo(f"\nRun results saved to: {json_file_path}")
    except AttributeError: # Fallback for Pydantic V1 if model_dump_json not found
        try:
            with open(json_file_path, "w") as f:
                json_content = run_output_data.json(indent=2) # Pydantic V1
                f.write(json_content)
            typer.echo(f"\nRun results saved to: {json_file_path} (using Pydantic V1 .json() method)")
        except Exception as e_v1:
            typer.secho(f"Error writing JSON output (Pydantic V1 fallback): {e_v1}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Error writing JSON output: {e}", fg=typer.colors.RED)

    typer.echo("\nEvalLoop run completed.")

    if run_output_data.total_tests_failed is not None and run_output_data.total_tests_failed > 0:
        typer.secho(f"{run_output_data.total_tests_failed} test(s) failed.", fg=typer.colors.RED)
        # TODO: Consider --soft-fail option later
        raise typer.Exit(code=1)
    else:
        typer.secho("All tests executed passed (or had no failing thresholds defined).", fg=typer.colors.GREEN)


if __name__ == "__main__":
    # Example of how to run this for local testing:
    # Ensure you have an evalloop.config.yaml and a tests/ directory with some .yaml files
    # You might need to `cd` to the project root if you are not already there.
    # CLI: python evalloop/cli/run_cmd.py 
    # or if installed: evalloop run 
    app()

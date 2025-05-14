import typer
import os
import shutil # For file operations later
from pathlib import Path

app = typer.Typer(name="init", help="Initialize EvalLoop: creates example config and test files.")

CONFIG_FILENAME = "evalloop.config.yaml"
TESTS_DIR_NAME = "tests"
EXAMPLE_TEST_FILENAME = "basic_example.yaml" # New name for the scaffolded file

# Placeholders for file content - will be more detailed later
SAMPLE_CONFIG_CONTENT = """
# EvalLoop Configuration
# api_keys:
#   openai: YOUR_OPENAI_KEY_HERE (or set OPENAI_API_KEY environment variable)
#   groq: YOUR_GROQ_API_KEY_HERE (or set GROQ_API_KEY environment variable)
#   openrouter: YOUR_OPENROUTER_API_KEY_HERE (or set OPENROUTER_API_KEY environment variable)
#
# default_model:
#   provider: "openai" # e.g., openai, groq, openrouter
#   model_name: "gpt-3.5-turbo"
#   parameters:
#     temperature: 0.7
#     max_tokens: 150
#     timeout_s: 30.0
#     retry_attempts: 2
#
# default_thresholds: # Optional: define global pass/fail thresholds for metrics
#   latency:
#     value: 5000 # Latency in ms, fail if actual > value
#   cost:
#     value: 0.10 # Cost in USD, fail if actual > value
#   # For metrics like ROUGE, you might define a threshold for f_score, e.g.:
#   # rouge_l_f1: 
#   #   f_score: 0.6 # Fail if actual f_score < value (example)
"""

# This content will be written to the user's tests/basic_example.yaml
BASIC_EXAMPLE_TEST_CONTENT = """
- id: "openrouter_greet_test_001"
  name: "OpenRouter Basic Greeting Test"
  description: "Tests a basic greeting prompt using a free model on OpenRouter (Mistral 7B Instruct). Requires OPENROUTER_API_KEY."
  type: "llm_generation"

  input_data:
    prompt: "Briefly introduce yourself and greet the user."

  expected_output:
    # For this free-form generation, we use a lenient regex to check for any non-empty response.
    # A human would typically review the actual output for qualitative assessment.
    regex_pattern: ".+" # Matches any non-empty string.

  metric_configs:
    - metric: "regex_match"
    - metric: "token_count"
    - metric: "latency"
      threshold:
        value: 15000 # Allow up to 15 seconds for free tier models
    - metric: "cost"

  model_config:
    provider: "openrouter"
    model_name: "mistralai/mistral-7b-instruct" # A common free model on OpenRouter
    parameters:
      temperature: 0.7
      max_tokens: 75
      timeout_s: 25.0
      retry_attempts: 2

  tags: ["openrouter", "free_model", "basic_example", "greeting"]

# You can add more test cases to this file or create new .yaml files in this directory.
# Refer to the documentation for more details on defining test cases and metrics.
"""

@app.command()
def initialize(
    project_dir: Path = typer.Option(
        ".", 
        help="The directory to initialize EvalLoop in. Defaults to the current directory.",
        exists=True, 
        file_okay=False, 
        dir_okay=True, 
        writable=True, 
        resolve_path=True
    ),
    force: bool = typer.Option(
        False, 
        "--force", "-f", 
        help="Overwrite existing configuration files if they exist."
    )
):
    """
    Creates evalloop.config.yaml and a tests/ directory with basic_example.yaml.
    """
    typer.echo(f"Initializing EvalLoop in: {project_dir}")

    config_file_path = project_dir / CONFIG_FILENAME
    tests_dir_path = project_dir / TESTS_DIR_NAME
    example_test_file_path = tests_dir_path / EXAMPLE_TEST_FILENAME

    # Create config file
    if not config_file_path.exists() or force:
        with open(config_file_path, "w") as f:
            f.write(SAMPLE_CONFIG_CONTENT)
        typer.echo(f"Created configuration file: {config_file_path}")
    else:
        typer.echo(f"Configuration file already exists: {config_file_path}. Use --force to overwrite.")

    # Create tests directory and example test file
    if not tests_dir_path.exists():
        os.makedirs(tests_dir_path)
        typer.echo(f"Created tests directory: {tests_dir_path}")
    
    if not example_test_file_path.exists() or force:
        with open(example_test_file_path, "w") as f:
            f.write(BASIC_EXAMPLE_TEST_CONTENT)
        typer.echo(f"Created example test file: {example_test_file_path}")
    elif tests_dir_path.exists(): 
        typer.echo(f"Example test file already exists: {example_test_file_path}. Use --force to overwrite.")

    typer.echo("\nEvalLoop initialized successfully!")
    typer.echo(f"1. Edit {CONFIG_FILENAME} to add your API keys and set default model preferences.")
    typer.echo(f"   (Ensure you have an OPENROUTER_API_KEY for the example test, or modify it.)")
    typer.echo(f"2. Review and modify the example test in {example_test_file_path}.")
    typer.echo("3. Add your own tests in the '.tests/' directory.")
    typer.echo("4. Run 'evalloop run' to execute your tests.")

if __name__ == "__main__":
    app()

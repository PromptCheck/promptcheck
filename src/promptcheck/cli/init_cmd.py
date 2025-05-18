import typer
import os
from pathlib import Path

app = typer.Typer(name="init", help="Initialize PromptCheck: creates example config and test files.")

CONFIG_FILENAME = "promptcheck.config.yaml"
TESTS_DIR_NAME = "tests"
EXAMPLE_TEST_FILENAME = "basic_example.yaml"

SAMPLE_CONFIG_CONTENT = """
# PromptCheck Configuration
# api_keys:
#   openai: YOUR_OPENAI_KEY_HERE (or set OPENAI_API_KEY environment variable)
#   groq: YOUR_GROQ_API_KEY_HERE (or set GROQ_API_KEY environment variable)
#   openrouter: YOUR_OPENROUTER_API_KEY_HERE (or set OPENROUTER_API_KEY environment variable)
#
# default_model:
#   provider: "openai" 
#   model_name: "gpt-3.5-turbo"
#   parameters:
#     temperature: 0.7
#     max_tokens: 150
#     timeout_s: 30.0
#     retry_attempts: 2
#
# default_thresholds:
#   latency:
#     value: 5000 
"""

BASIC_EXAMPLE_TEST_CONTENT = """
- id: "openrouter_greet_test_001"
  name: "OpenRouter Basic Greeting Test"
  description: "Tests a basic greeting prompt using a free model on OpenRouter (Mistral 7B Instruct). Requires OPENROUTER_API_KEY."
  type: "llm_generation"
  input_data:
    prompt: "Briefly introduce yourself and greet the user."
  expected_output:
    regex_pattern: ".+"
  metric_configs:
    - metric: "regex_match"
    - metric: "token_count"
    - metric: "latency"
      threshold:
        value: 15000
    - metric: "cost"
  model_config:
    provider: "openrouter"
    model_name: "mistralai/mistral-7b-instruct"
    parameters:
      temperature: 0.7
      max_tokens: 75
      timeout_s: 25.0
      retry_attempts: 2
  tags: ["openrouter", "free_model", "basic_example", "greeting"]
"""

@app.command()
def initialize(
    project_dir: Path = typer.Option(
        ".", 
        help="The directory to initialize PromptCheck in. Defaults to the current directory.",
        exists=True, file_okay=False, dir_okay=True, writable=True, resolve_path=True
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration files if they exist.")
):
    """
    Creates promptcheck.config.yaml and a tests/ directory with basic_example.yaml.
    """
    typer.echo(f"Initializing PromptCheck in: {project_dir}")

    config_file_path = project_dir / CONFIG_FILENAME
    tests_dir_path = project_dir / TESTS_DIR_NAME
    example_test_file_path = tests_dir_path / EXAMPLE_TEST_FILENAME

    if not config_file_path.exists() or force:
        with open(config_file_path, "w") as f:
            f.write(SAMPLE_CONFIG_CONTENT)
        typer.echo(f"Created configuration file: {config_file_path}")
    else:
        typer.echo(f"Configuration file already exists: {config_file_path}. Use --force to overwrite.")

    if not tests_dir_path.exists():
        os.makedirs(tests_dir_path)
        typer.echo(f"Created tests directory: {tests_dir_path}")
    
    if not example_test_file_path.exists() or force:
        with open(example_test_file_path, "w") as f:
            f.write(BASIC_EXAMPLE_TEST_CONTENT)
        typer.echo(f"Created example test file: {example_test_file_path}")
    elif tests_dir_path.exists(): 
        typer.echo(f"Example test file already exists: {example_test_file_path}. Use --force to overwrite.")

    typer.echo("\nPromptCheck initialized successfully!")
    typer.echo(f"1. Edit {CONFIG_FILENAME} to add your API keys and set default model preferences.")
    typer.echo(f"   (Ensure you have an OPENROUTER_API_KEY for the example test, or modify it.)")
    typer.echo(f"2. Review and modify the example test in {example_test_file_path}.")
    typer.echo("3. Add your own tests in the 'tests/' directory.")
    typer.echo("4. Run 'promptcheck run' to execute your tests.")

if __name__ == "__main__":
    app() 
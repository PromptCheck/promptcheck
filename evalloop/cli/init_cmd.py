import typer
import os
import shutil # For file operations later
from pathlib import Path

app = typer.Typer(name="init", help="Initialize EvalLoop: creates example config and test files.")

CONFIG_FILENAME = "evalloop.config.yaml"
TESTS_DIR_NAME = "tests"
SAMPLE_TEST_FILENAME = "sample_test.yaml"

# Placeholders for file content - will be more detailed later
SAMPLE_CONFIG_CONTENT = """
# EvalLoop Configuration
# api_keys:
#   openai: YOUR_OPENAI_KEY
#   groq: YOUR_GROQ_KEY
# default_model: "gpt-3.5-turbo"
# default_thresholds:
#   latency_p95_ms: 5000
#   cost_per_run_usd: 1.00
"""

SAMPLE_TEST_CONTENT = """
# Sample EvalLoop Test File (tests/sample_test.yaml)
# A file can contain a list of test cases.

- id: "french_capital_exact_match_001"
  name: "Check Capital of France (Exact Match)"
  description: "Tests if the LLM correctly identifies Paris as the capital of France with an exact match."
  type: "llm_generation"

  input_data:
    prompt: "What is the capital of France?"

  expected_output:
    exact_match_string: "Paris"
    reference_texts: # Useful for other metrics if added, e.g., ROUGE
      - "Paris"
      - "The capital of France is Paris."

  metric_configs:
    - metric: "exact_match"
    - metric: "token_count"
      parameters:
        count_types: ["completion", "total"]
      thresholds:
        completion_max: 10 # Expect a short answer
    - metric: "latency"
      threshold: 1500 # Expect a fast response in ms
    # - metric: "cost" # Uncomment if you want to track cost for this test

  model_config:
    provider: "default" # Uses default_model from evalloop.config.yaml
    model_name: "default" # Uses default_model from evalloop.config.yaml
    # parameters: # Example of overriding default parameters
    #   temperature: 0.1 

  tags: ["geography", "exact_match", "core_knowledge"]

# - id: "another_test_example_002"
#   name: "Another Test Case Example"
#   description: "..."
#   type: "llm_generation"
#   input_data:
#     prompt: "..."
#   expected_output:
#     ...
#   metric_configs:
#     - metric: "rouge_l"
#       threshold:
#         f_score: 0.6
#   model_config:
#     provider: "openai"
#     model_name: "gpt-4o"
#   tags: ["example"]
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
    Creates an example evalloop.config.yaml and a tests/ directory with a sample_test.yaml.
    """
    typer.echo(f"Initializing EvalLoop in: {project_dir}")

    config_file_path = project_dir / CONFIG_FILENAME
    tests_dir_path = project_dir / TESTS_DIR_NAME
    sample_test_file_path = tests_dir_path / SAMPLE_TEST_FILENAME

    # Create config file
    if not config_file_path.exists() or force:
        with open(config_file_path, "w") as f:
            f.write(SAMPLE_CONFIG_CONTENT)
        typer.echo(f"Created configuration file: {config_file_path}")
    else:
        typer.echo(f"Configuration file already exists: {config_file_path}. Use --force to overwrite.")

    # Create tests directory and sample test file
    if not tests_dir_path.exists():
        os.makedirs(tests_dir_path)
        typer.echo(f"Created tests directory: {tests_dir_path}")
    
    if not sample_test_file_path.exists() or force:
        with open(sample_test_file_path, "w") as f:
            f.write(SAMPLE_TEST_CONTENT)
        typer.echo(f"Created sample test file: {sample_test_file_path}")
    elif tests_dir_path.exists(): # only print if tests_dir was already there or just created
        typer.echo(f"Sample test file already exists: {sample_test_file_path}. Use --force to overwrite.")

    typer.echo("\nEvalLoop initialized successfully!")
    typer.echo("Next steps:")
    typer.echo(f"1. Edit {CONFIG_FILENAME} to add your API keys and preferences.")
    typer.echo(f"2. Add your own tests in the '{TESTS_DIR_NAME}' directory.")
    typer.echo("3. Run 'evalloop run' to execute your tests.")

if __name__ == "__main__":
    app()

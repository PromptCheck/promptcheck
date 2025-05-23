#!/bin/sh -l

set -e # Exit immediately if a command exits with a non-zero status.

# GitHub Actions sets inputs as environment variables with INPUT_ prefix
# e.g., input `test_path` becomes `INPUT_TEST_PATH`

echo "Starting PromptCheck Action..."

# Ensure the 'run' subcommand is included and disable virtualenv creation for this run
CMD="POETRY_VIRTUALENVS_CREATE=false poetry run promptcheck run"

# Config directory for the 'run' subcommand
if [ -n "$INPUT_CONFIG_DIR" ]; then
  CMD="$CMD --config $INPUT_CONFIG_DIR"
else
  # Default to current directory for config if not provided, passed to 'run' subcommand
  CMD="$CMD --config ."
fi

# Output directory for the 'run' subcommand
OUTPUT_DIR_PARAM="."
if [ -n "$INPUT_OUTPUT_DIR" ]; then
  OUTPUT_DIR_PARAM="$INPUT_OUTPUT_DIR"
fi
CMD="$CMD --output-dir $OUTPUT_DIR_PARAM"

# Test path (this is an argument to the 'run' subcommand)
TEST_PATH_PARAM=""
if [ -n "$INPUT_TEST_PATH" ]; then
  TEST_PATH_PARAM="$INPUT_TEST_PATH"
fi

# Append test_path_param only if it's not empty
if [ -n "$TEST_PATH_PARAM" ]; then
  CMD="$CMD $TEST_PATH_PARAM"
else
  # If no test path is given, promptcheck run (the subcommand) will use its default (e.g. tests/)
  echo "No explicit test_path input, promptcheck run subcommand will use its default or fail if none found."
fi

echo "Executing command: $CMD"

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR_PARAM"

# Execute the command
# Capture stdout to a file and also print to console
# Also capture stderr
OUTPUT_LOG="promptcheck_action_stdout.log"
ERROR_LOG="promptcheck_action_stderr.log"

# Ensure the command is executed in a way that $GITHUB_OUTPUT can be written to by the Python script
# The Python script should handle writing to the path specified by the GITHUB_OUTPUT env var.
# The GITHUB_OUTPUT env var is automatically available to steps in GitHub Actions.

if eval "$CMD" > "$OUTPUT_LOG" 2> "$ERROR_LOG"; then
  echo "PromptCheck run completed successfully."
  cat "$OUTPUT_LOG"
  if [ -s "$ERROR_LOG" ]; then # if error log is not empty
    echo "--- Errors/Warnings from PromptCheck --- "
    cat "$ERROR_LOG"
    echo "-------------------------------------"
  fi
else
  EXIT_CODE=$?
  echo "PromptCheck run failed with exit code $EXIT_CODE."
  echo "--- Output from PromptCheck --- "
  cat "$OUTPUT_LOG"
  echo "----------------------------"
  echo "--- Errors from PromptCheck --- "
  cat "$ERROR_LOG"
  echo "----------------------------"
  exit $EXIT_CODE
fi

# Set the output for the action using the GITHUB_OUTPUT file path
# The entrypoint script itself should determine the json_file_path based on its own logic
# (it knows where it saved it based on OUTPUT_DIR_PARAM)
# and then write to the $GITHUB_OUTPUT file.

# Example: Find the generated JSON file. 
# This logic for finding the run.json file should ideally be more robust or handled by promptcheck CLI providing the exact path.
RUN_JSON_FILES=$(find "$OUTPUT_DIR_PARAM" -name 'promptcheck_run_*.json' -print -quit)

if [ -n "$RUN_JSON_FILES" ]; then
  echo "Found run.json: $RUN_JSON_FILES"
  echo "run_json_path=$RUN_JSON_FILES" >> "$GITHUB_OUTPUT"
else
  echo "Warning: Could not find promptcheck_run_*.json in $OUTPUT_DIR_PARAM for action output."
  echo "run_json_path=" >> "$GITHUB_OUTPUT"
fi

echo "Action finished." 
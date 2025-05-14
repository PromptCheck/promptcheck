#!/bin/sh -l

set -e # Exit immediately if a command exits with a non-zero status.

# GitHub Actions sets inputs as environment variables with INPUT_ prefix
# e.g., input `test_path` becomes `INPUT_TEST_PATH`

echo "Starting EvalLoop Action..."

# Construct the evalloop command
CMD="poetry run evalloop"

# Config directory
if [ -n "$INPUT_CONFIG_DIR" ]; then
  CMD="$CMD --config $INPUT_CONFIG_DIR"
else
  CMD="$CMD --config ." # Default if not provided
fi

# Output directory for run.json
OUTPUT_DIR_PARAM="."
if [ -n "$INPUT_OUTPUT_DIR" ]; then
  OUTPUT_DIR_PARAM="$INPUT_OUTPUT_DIR"
fi
CMD="$CMD --output-dir $OUTPUT_DIR_PARAM"

# Test path (this is an argument, not an option with a flag)
TEST_PATH_PARAM=""
if [ -n "$INPUT_TEST_PATH" ]; then
  TEST_PATH_PARAM="$INPUT_TEST_PATH"
fi

# Append test_path_param only if it's not empty
if [ -n "$TEST_PATH_PARAM" ]; then
  CMD="$CMD $TEST_PATH_PARAM"
else
  # If no test path is given, evalloop run will use its default (e.g. tests/)
  # Or, we can explicitly pass the default from action.yml if needed,
  # but it's better if the CLI handles its own defaults when no arg is passed.
  # For now, if INPUT_TEST_PATH is empty, we pass no positional argument for tests,
  # relying on evalloop CLI's default behavior (which looks in ./tests).
  # The action.yml default is `tests/basic_example.yaml`, so INPUT_TEST_PATH will usually be set.
  echo "No explicit test_path input, evalloop CLI will use its default search or fail if none found."
fi

echo "Executing command: $CMD"

# Create the output directory if it doesn't exist
# The runner in evalloop_run creates it, but good to ensure here as well for artifact path
mkdir -p "$OUTPUT_DIR_PARAM"

# Execute the command
if $CMD; then
  echo "EvalLoop run completed successfully."
else
  EXIT_CODE=$?
  echo "EvalLoop run failed with exit code $EXIT_CODE."
  exit $EXIT_CODE
fi

# Set the output for the action
# The path should be relative to GITHUB_WORKSPACE, or absolute
# Our OUTPUT_DIR_PARAM is relative to GITHUB_WORKSPACE already.

# Find the generated JSON file. Assuming only one run.json is created per execution.
# This is a bit fragile if multiple JSONs could exist or if naming changes.
# The evalloop CLI prints the path, which is better, but harder to capture here directly.
RUN_JSON_FILES=$(find "$OUTPUT_DIR_PARAM" -name 'evalloop_run_*.json' -print -quit) # -quit for first match

if [ -n "$RUN_JSON_FILES" ]; then
  echo "Found run.json: $RUN_JSON_FILES"
  # GITHUB_OUTPUT is the standard way to set action outputs
  echo "run_json_path=$RUN_JSON_FILES" >> "$GITHUB_OUTPUT"
else
  echo "Warning: Could not find evalloop_run_*.json in $OUTPUT_DIR_PARAM"
  # Optionally, set a default or empty output
  echo "run_json_path=" >> "$GITHUB_OUTPUT"
fi

echo "Action finished." 
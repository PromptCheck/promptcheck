# Quick-Start Guide

EvalLoop lets you test LLM prompts with a simple YAML file and run those tests in CI. This guide shows you how to get your first prompt regression test running in under 5 minutes.

1.  **Install EvalLoop**

    ```bash
    pip install evalloop
    # Or for BLEU metric support:
    # pip install evalloop[bleu]
    ```

2.  **Initialize Your Project**

    Navigate to your project's root directory and run:
    ```bash
    evaloop init
    ```
    This creates:
    *   `evalloop.config.yaml` (for API keys and global settings - add your keys here or set environment variables)
    *   `tests/basic_example.yaml` (a sample test file)

### Write Your First Prompt Test

EvalLoop tests are defined in simple YAML files. These describe the input prompt, the expected output (or characteristics of it), and the metrics to apply. The `tests/basic_example.yaml` file created by `evaloop init` is a great starting point.

3.  **Customize Your Test**
    Open `tests/basic_example.yaml`. You can tweak the `prompt` under `input_data`, adjust the `expected_output` (e.g., the `regex_pattern`), or change the `metric_configs` to experiment.

4.  **Run EvalLoop Locally**

    Execute the tests:
    ```bash
    evaloop run
    # Or to run a specific test file or directory:
    # evaloop run tests/basic_example.yaml
    ```
    You'll see a summary table of pass/fail results in your console and a detailed `evalloop_run_*.json` file will be saved.

### Run in CI with GitHub Actions

EvalLoop can post test results to your pull requests, so you catch GPT or Claude output changes before merging.

5.  **Add to GitHub CI**
    *   Copy the example workflow file from the EvalLoop repository (`example/.github/workflows/evalloop_example.yml`) to your project's `.github/workflows/` directory.
    *   Ensure you have an `evalloop.config.yaml` in your project root (or rely on environment variables for API keys).
    *   Add necessary API keys (e.g., `OPENROUTER_API_KEY`) as secrets in your GitHub repository settings (under Settings > Secrets and variables > Actions).
    *   Commit these changes. Now, EvalLoop will run on your Pull Requests!

    You should see a comment like this on your PRs:

    ![PR Comment](../img/evalloop_pr_comment.gif) <!-- Placeholder: Replace with actual GIF path from project root: docs/img/evalloop_pr_comment.gif -->

Need more examples or advanced configurations? 
*   Check the [`example/`](../example/) directory in the EvalLoop repository.
*   For detailed configuration of test cases and metrics, see the [YAML Reference](yaml_reference.md) (Coming Soon!).
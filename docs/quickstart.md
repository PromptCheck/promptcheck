# Quick-Start Guide

PromptCheck lets you test LLM prompts with a simple YAML file and run those tests in CI. This guide shows you how to get your first prompt regression test running in under 5 minutes.

1.  **Install PromptCheck**

    ```bash
    pip install promptcheck
    # Or for BLEU metric support:
    # pip install promptcheck[bleu]
    ```

2.  **Initialize Your Project**

    Navigate to your project's root directory and run:
    ```bash
    promptcheck init
    ```
    This creates:
    *   `promptcheck.config.yaml` (add your API keys here or set environment variables)
    *   `tests/basic_example.yaml` (a sample test file)

### Write Your First Prompt Test

PromptCheck tests are defined in simple YAML files. We'll create a YAML test file describing the prompt and the expected response pattern. The `promptcheck init` command gives you a great starting point with `tests/basic_example.yaml`.

3.  **Customize Your Test**
    Open `tests/basic_example.yaml`. You can tweak the `prompt` under `input_data`, adjust the `expected_output` (e.g., the `regex_pattern`), or change the `metric_configs` to experiment.

4.  **Run PromptCheck Locally**

    Execute the tests:
    ```bash
    promptcheck run
    # Or to run a specific test file or directory:
    # promptcheck run tests/basic_example.yaml
    ```
    You'll see a summary table of pass/fail results in your console and a detailed `promptcheck_run_*.json` file will be saved.

### Run in CI with GitHub Actions

PromptCheck can post test results to your pull requests, so you catch GPT or Claude output changes before merging.

5.  **Add to GitHub CI**
    *   Copy the example workflow file from the PromptCheck repository (`example/.github/workflows/promptcheck_example.yml`) to your project's `.github/workflows/` directory.
    *   Ensure you have a `promptcheck.config.yaml` in your project root (or rely on environment variables for API keys).
    *   Add necessary API keys (e.g., `OPENROUTER_API_KEY`) as secrets in your GitHub repository settings (under Settings > Secrets and variables > Actions).
    *   Commit these changes. Now, PromptCheck will run on your Pull Requests!

    Your `promptcheck run` output will look something like this:

    ![PR Comment](../img/promptcheck_pr_comment.gif) <!-- Placeholder: Path was docs/img/promptcheck_pr_comment.gif (file missing) -->

    This provides a clear summary of which tests passed or failed, along with key metrics.

Need more examples or advanced configurations? 
*   Check the [`example/`](../example/) directory in the PromptCheck repository.
*   For detailed configuration of test cases and metrics, see the [YAML Reference](yaml_reference.md) (Coming Soon!).

## GitHub Action in Action

![PR Comment](../img/promptcheck_pr_comment.gif) <!-- Placeholder: Path was docs/img/promptcheck_pr_comment.gif (file missing) -->

When a Pull Request is opened, PromptCheck automatically runs your tests and posts a summary comment:
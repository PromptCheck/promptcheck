# Quick-Start Guide

Follow these five steps to get EvalLoop running in under 5 minutes.

1.  **Install**

    ```bash
    pip install evalloop
    # Or for BLEU metric support:
    # pip install evalloop[bleu]
    ```

2.  **Scaffold**

    ```bash
    evaloop init
    # creates:
    #   evalloop.config.yaml  (add your API keys here or set environment variables)
    #   tests/basic_example.yaml
    ```

3.  **Edit your test**
    Open `tests/basic_example.yaml` and tweak the prompt, expected output, or metrics.

4.  **Run locally**

    ```bash
    evaloop run
    # Or to run a specific test file or directory:
    # evaloop run tests/basic_example.yaml
    ```

    You'll see a table of pass/fail results and a JSON file under `evalloop_run_*.json`.

5.  **Add to GitHub CI**
    Copy `.github/workflows/eval.yml` from the main EvalLoop repository or the `example/` folder into your project's `.github/workflows/` directory.
    Add necessary API keys as secrets in your GitHub repository settings.
    EvalLoop will then run on your Pull Requests and post a summary comment like this:

    ![PR Comment](../img/evalloop_pr_comment.gif) <!-- Placeholder: Replace with actual GIF path from project root: docs/img/evalloop_pr_comment.gif -->

Need more examples? Check the [`example/`](../example/) directory in the EvalLoop repository.

For detailed configuration of test cases and metrics, see the [YAML reference](yaml_reference.md) (Coming Soon!). 
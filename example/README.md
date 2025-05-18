# PromptCheck Example Usage

This directory provides a minimal example of how to set up PromptCheck in your own project.

## Files

*   `tests/basic_example.yaml`: A sample test case file. You can adapt this or create your own based on the structure shown in the main project README.
*   `promptcheck.config.yaml.example`: An example configuration file. Copy this to `promptcheck.config.yaml` in the root of *your* project and add your API keys.
*   `.github/workflows/promptcheck_example.yml`: A sample GitHub Actions workflow file. You can copy this to your project's `.github/workflows/` directory to integrate PromptCheck into your CI/CD pipeline for Pull Requests.

## Setup

1.  **Copy Files**: Copy `tests/basic_example.yaml` into a `tests/` directory in your project. Copy `promptcheck.config.yaml.example` to the root of your project and rename it to `promptcheck.config.yaml`, then fill in your API keys.
2.  **Add Workflow**: Copy `promptcheck_example.yml` to your project's `.github/workflows/` directory. You may need to adjust paths or the Python version.
3.  **Secrets**: Add any necessary API keys (e.g., `OPENROUTER_API_KEY`) as secrets in your GitHub repository settings (Settings -> Secrets and variables -> Actions).
4.  **PR Comment Script (Optional)**: If you want PR comments, you'll need to copy the `scripts/post_comment.py` script from the main PromptCheck repository into your own project (e.g., into a `scripts/` directory) and ensure the workflow step for posting comments correctly invokes it.

Refer to the main [PromptCheck README.md](https://github.com/b00gn1sh/promptcheck/blob/main/README.md) for more detailed instructions on installation, configuration, and writing tests. 
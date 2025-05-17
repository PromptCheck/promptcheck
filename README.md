# EvalLoop

Continuous Integration for LLM prompts & agents

EvalLoop is a **CI-first test harness for LLM prompts**.  
Write tests in YAML, gate pull-requests, and see pass/fail summaries posted as
comments—so your prompts don't quietly regress.

[![build](https://github.com/b00gn1sh/evalloop/actions/workflows/eval.yml/badge.svg)](https://github.com/b00gn1sh/evalloop/actions)
[![PyPI](https://img.shields.io/pypi/v/evalloop.svg)](https://pypi.org/project/evalloop/)
[![License](https://img.shields.io/github/license/b00gn1sh/evalloop.svg)](LICENSE)

---

## 🚀 Install & Run

```bash
pip install evalloop          # or: pip install evalloop[bleu]
evaloop init                 # scaffolds config + tests/
evaloop run                  # executes all *.yaml under tests/
```

> **Need full example?** See [`example/`](example/) or the [Quick-Start Guide](docs/quickstart.md).

---

## What does EvalLoop do?

When you tweak a prompt, swap models, or refactor your agent code, **EvalLoop** runs a battery of tests in CI (Rouge, regex, token-cost, latency, etc.) and fails the pull-request if quality regresses or cost spikes.

Think **pytest + coverage**, but for LLM output.

---

## Key features

*   **Easy setup** — drop a YAML test file, add the GitHub Action, done.
*   **Multi‑provider** — OpenAI, Groq, OpenRouter (more soon).
*   **Metrics out‑of‑the‑box** — exact/regex match, ROUGE‑L, BLEU (optional), token‑count, latency, cost.
*   **Readable reports** — Action log output and (coming soon) PR comment bot. `run.json` artifact produced.
*   **Fast to extend** — write your own metric in <30 lines (standard Python).

| Feature | Free | Pro |
|---------|:----:|:---:|
| CLI & GitHub Action | ✅ | ✅ |
| 30-day result history | ✅ | ✅ |
| Unlimited history & charts | — | ✅ |
| Slack alerts | — | ✅ |

---

## What it looks like

![EvalLoop PR Comment](docs/img/pr_comment.gif)

---

## How the YAML works (`tests/*.yaml`)

A test file contains a list of test cases. Here's an example structure:

```yaml
- id: "openrouter_greet_test_001"
  name: "OpenRouter Basic Greeting Test"
  description: "Tests a basic greeting prompt."
  type: "llm_generation"

  input_data:
    prompt: "Briefly introduce yourself and greet the user."

  expected_output:
    # For regex_match, a pattern to find in the LLM's output
    regex_pattern: ".+" # Example: matches any non-empty string

  metric_configs:
    - metric: "regex_match" 
    - metric: "token_count"
      parameters:
        count_types: ["completion", "total"]
    - metric: "latency"
      threshold: # Optional: fail if conditions aren't met
        value: 10000 # e.g., latency_ms <= 10000
    - metric: "cost" 

  model_config:
    provider: "openrouter"
    model_name: "mistralai/mistral-7b-instruct"
    parameters:
      temperature: 0.7
      max_tokens: 50
      timeout_s: 25.0 
      retry_attempts: 2

  tags: ["openrouter", "greeting"] 
```
Add more cases in `tests/`. Thresholds (like `value` for latency, or `f_score` for rouge) are defined within the `threshold` object of a `metric_config`.

---

## Installation variants

```bash
# From PyPI (once 0.1.0+ is live)
# pip install evalloop

# With optional BLEU metric (requires NLTK)
# pip install evalloop[bleu]

# For development:
poetry install # Installs base dependencies
poetry install --extras bleu # Installs with BLEU support
```

---

## Releasing (maintainers)

```bash
# 1. Ensure tests pass and docs are updated
# 2. Bump version in pyproject.toml
poetry version <new_version_例えば_0.1.0>  # e.g., 0.1.0, 0.2.0b1

# 3. Build the package
poetry build

# 4. Publish to TestPyPI first (configured in pyproject.toml or via poetry config)
# poetry config pypi-token.testpypi <YOUR_TESTPYPI_TOKEN>
poetry publish -r testpypi

# 5. Test TestPyPI package thoroughly (e.g., in a clean venv or CI)

# 6. Publish to PyPI (prod)
# poetry config pypi-token.pypi <YOUR_PYPI_TOKEN>
poetry publish

# 7. Tag the release in Git
git tag v<new_version_例えば_0.1.0> # e.g., v0.1.0
git push origin v<new_version_例えば_0.1.0>
```

---

## Documentation

📖 **Docs:** [Quick-Start](docs/quickstart.md) · [YAML reference](docs/yaml_reference.md)

---

## Roadmap

*   PR comment bot (✅/❌ matrix in‑line)
*   Hosted dashboard (Supabase)
*   Async runner for large test suites
*   More metrics and LLM provider integrations

---

## Contributing

1.  Fork & clone the repository.
2.  Set up your development environment: `poetry install --extras bleu` (to include all deps).
3.  Run tests locally: `poetry run evalloop run tests/` (or a specific file). Keep it green!
4.  Make your changes, add tests for new features.
5.  Open a Pull Request.

---

## License

MIT

--- 

*End of Document – keep this file as the project's living reference; version & timestamp changes at top on each major edit.*

<!-- Workflow debug trigger --> 
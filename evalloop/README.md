# evalloop

# EvalLoop – Project Blueprint (Single Source of Truth)

*Version 0.1 – May 14 2025*

---

## 1 Elevator Pitch

**"Don't merge broken prompts."** EvalLoop is a zero-config CI layer that runs an automated battery of evaluations on every pull-request to an LLM-powered repo, tracking quality, latency, and cost deltas over time. Open-source CLI + GitHub Action, with a \$9/mo hosted dashboard for historical analytics.

---

## 2 Problem & Opportunity

* **Brittle prompts & agents** break silently after model upgrades or prompt edits.
* Existing eval libraries (lm-evaluation-harness, LangSmith) require custom wiring; few teams run them in CI.
* Devs waste hours on manual spot-checks and cost accounting.
  **Gap:** a plug-and-play CI harness that feels native to GitHub and costs \$0 to run locally—perfect for indie hackers, consultancies, and small AI product teams.

---

## 3 Target Users / Personas

| Persona                            | Pain                                            | Desired Outcome                                                |
| ---------------------------------- | ----------------------------------------------- | -------------------------------------------------------------- |
| **Indie LLM dev (solo)**           | Fear of shipping regressions; no time for infra | One-line Action that blocks bad PRs, crystal-clear diff report |
| **Startup AI team (3-6 devs)**     | Need reproducible evals, token-cost tracking    | Team dashboard, Slack alerts, audit trail                      |
| **Consultant / AI agency**         | Prove value to clients                          | White-label reports, cost vs quality charts                    |
| **Trash Panda** (internal dogfood) | Ensure summaries stay on-spec                   | Same harness powers in-house QA                                |

---

## 4 Value Proposition

* **Fast start:** `pip install evalloop && evalloop init` --> ready in 60 s.
* **\$0 cloud burn:** Runs on the user's model/provider; CLI can execute locally or via hosted APIs.
* **Quant + Qual metrics:** Rouge/BLEU/F1, custom regex checks, hallucination score, token counts, latency.
* **Historical insight:** Hosted dashboard stores every run; trend lines highlight regressions + cost creep.
* **Extensible:** YAML spec lets users add custom tests, model routes, and providers (OpenAI, Groq, OpenRouter, HF).
* **Witty DX:** Trash-Panda-style grouchy copy keeps docs memorable.

---

## 5 Scope

### 5.1 MVP (Weeks 1-4)

1. **Open-source core**

   * Python CLI (`evalloop run`/`init`/`report`).
   * Built-in test types: exact-match, regex, Rouge, cost, latency.
2. **GitHub Action**

   * YML template (`uses: evalloop/action@v1`).
   * Upload JSON artifact + Markdown summary comment on PR.
3. **Hosted Dashboard (Beta)**

   * Supabase/Postgres storage.
   * Simple chart (quality & cost over commits).
   * Email magic-link auth.
4. **Docs & Demo**

   * Quickstart README, Loom video, sample repo.

### 5.2 V1 (Weeks 5-10)

* Slack/Discord notifications.
* Team roles & project quotas.
* Webhook ingest for non-GitHub pipelines.
* API key rotation / usage caps.
* Billing: Stripe metered (token-stored) + \$9/mo base.

### 5.3 Future Ideas

* **FlowLens DevTools Panel** – time-travel replay & token visualizer.
* **White-label OEM** licensing for SaaS toolchains.
* VS Code and Cursor IDE extensions.
* Auto-generation of failing regression prompts.

---

## 6 Functional Requirements

1. **Test Specification**

   * `tests/*.yaml` declare: `name`, `input`, `expected`, `metric`, `model`.

### 6.1.1 Detailed Test Case YAML Structure

Each `tests/*.yaml` file can contain a list of test case objects. A single test case object should adhere to the following structure:

```yaml
- id: "unique_test_id_001" # Optional, but recommended for tracking.
  name: "Descriptive Test Case Name" # Required: Human-readable name.
  description: "Optional detailed explanation of what this test evaluates." # Optional.
  type: "llm_generation" # Required: Defines the test nature. E.g., 'classification' in future.

  # Input for the LLM
  input_data: # Required
    prompt: "Your prompt text. You can use {{variables}} if needed." # Required
    # variables: # Optional: Values to substitute into the prompt template.
    #   customer_query: "Tell me about your refund policy."
    #   product_docs: "Our refund policy states..."

  # Expected outcomes or reference data for evaluation
  expected_output: # Required, structure depends on the metrics used.
    exact_match_string: "The precise string the LLM must output." # For 'exact_match'.
    regex_pattern: "Th[ei]s is a RegEx p.ttern" # For 'regex_match'.
    reference_texts: # For ROUGE, BLEU, semantic similarity.
      - "This is the first ideal answer or reference summary."
      - "This is another acceptable reference text."
    # custom_data: ... # For future custom metrics

  # Metrics to calculate and their configurations
  metric_configs: # Required: A list of metrics to apply.
    - metric: "exact_match"
    - metric: "regex_match"
      # Pattern from expected_output.regex_pattern
    - metric: "rouge_l" # Measures recall, precision, F1 for overlap.
      threshold: # Optional: Define pass/fail criteria.
        f_score: 0.7 # Example: F1 score must be >= 0.7
    - metric: "bleu" # Measures n-gram precision against references.
      # parameters: { n_gram: 4 } # Default or configurable.
    - metric: "token_count" # Counts tokens.
      parameters:
        count_types: ["completion", "total"] # Specify what to count.
      thresholds: # Optional: Flag if counts are outside expected ranges.
        completion_max: 200
    - metric: "latency" # Measures end-to-end execution time.
      threshold: 3000 # In milliseconds (e.g., p95).
    - metric: "cost" # Estimates monetary cost of the LLM call.
      # threshold: 0.005 # Optional: Flag if single test run exceeds cost in USD.
    # - metric: "hallucination_score" # (Future - from README)
      # parameters: { method: "llm_critique", critique_model: "gpt-4" }

  # LLM provider and model configuration for this test
  model_config: # Required
    provider: "default" # E.g., 'openai', 'groq'. 'default' uses evalloop.config.yaml.
    model_name: "default" # E.g., 'gpt-4o'. 'default' uses evalloop.config.yaml.
    parameters: # Optional: Override global/provider defaults.
      temperature: 0.5
      max_tokens: 150
      # ... other provider-specific parameters

  tags: ["summarization", "customer_service", "mvp"] # Optional: For filtering.
```

2. **Core Metrics**

   * Rouge-L / BLEU-4
   * Exact / regex match
   * LLM-evaluate hallucination score
   * Token counts (prompt, completion)
   * Latency (p95)
3. **CLI Commands**

   * `init` – scaffold examples
   * `run` – execute suite, output JSON
   * `report` – pretty console table / HTML
4. **CI Action**

   * Fails build on threshold breach.
   * Posts GitHub comment with ✅/❌ matrix.
5. **Security & Privacy**

   * No data leaves runner unless dashboard enabled.
   * HTTPS/TLS, JWT, row-level security (Supabase).
6. **Perf Targets**

   * Overhead ≤ 5 s per 10 tests on Groq Llama-3-8B.
   * CLI binary size < 15 MB.

---

## 7 Non-Functional Requirements

* **Reliability:** deterministic replay; pinned model & temperature.
* **Extensibility:** plugin hooks for custom metrics/providers.
* **Usability:** single-command onboarding; clear failure outputs.
* **Cost Transparency:** dashboard shows \$ per test and per run.
* **Brand Tone:** dry, grouchy, Trash-Panda-esque humor in logs/docs (e.g., "👏 Congrats, you only hallucinated 12 times.").

---

## 8 System Architecture

```
Developer → Git push → GitHub Actions Runner
                               │
                               ├── evalloop CLI (Python)  
                               │    ├─ Calls LLM provider (HTTP)
                               │    ├─ Computes metrics
                               │    └─ Emits run.json
                               │
                               └── Upload artifact + PR comment
                                     │
                                     └─ (optional) Post run.json → EvalLoop
                                         Dashboard API (FastAPI, Supabase)
```

*CLI and Action are open-source; Dashboard is a managed microservice.*

---

## 9 Tech Stack

| Layer     | Choice                               | Rationale                  |
| --------- | ------------------------------------ | -------------------------- |
| CLI       | Python 3.11 + Typer                  | Fast dev, easy install     |
| Metrics   | `rouge-score`, regex, custom funcs   | Lightweight deps           |
| Action    | Docker container (`python:slim`)     | Consistent env             |
| Dashboard | FastAPI + Supabase/Postgres + Prisma | Quick CRUD, row-level auth |
| Front-end | Next.js + shadcn/ui                  | Modern DX, Tailwind        |
| Auth      | Supabase Magic Link                  | Password-less simplicity   |
| Billing   | Stripe metered usage                 | Industry-standard          |
| Hosting   | Fly.io or Railway                    | Low \$/auto-scale          |

---

## 10 Data Model (Dashboard)

* **users**: id, email, created_at
* **projects**: id, owner_id, name, plan
* **runs**: id, project_id, git_sha, created_at, total_cost, duration_ms
* **results**: id, run_id, test_name, metric, score, tokens_prompt, tokens_completion, latency_ms, pass
* Row-level security: user can access rows where `project.owner_id = user.id`.

---

## 11 Milestone Timeline

| Week | Goal                      | Deliverables                                           |
| ---- | ------------------------- | ------------------------------------------------------ |
| 1    | Proof-of-concept          | CLI runs 3 hard-coded tests; README draft              |
| 2    | Config spec + YAML parser | `evalloop init/run`; integration with OpenRouter/Groq  |
| 3    | GitHub Action             | Artifact upload; PR comment; blog post soft-launch     |
| 4    | Hosted dashboard alpha    | Supabase tables; basic charts; invite early users      |
| 5    | Stripe billing            | Free vs Pro tier; retention policy                     |
| 6    | Marketing push            | HN "Show HN", Reddit r/MachineLearning, partner tweets |
| 7-8  | Feedback & bug-bash       | Polish CLI; perf optimizations                         |
| 9-10 | v1 release                | Docs v1, logo, official pricing                        |

---

## 12 Go-To-Market & Pricing

* **Free OSS** – CLI + Action + 14-day dashboard retention.
* **Pro (\$9/mo)** – unlimited retention, team seats, Slack alerts, CSV export.
* **Agency (\$49/mo)** – white-label PDF reports, client projects.
* Channels: GitHub Marketplace, HN, X (AI engineering), IndieHackers.
* Lead magnet: free "Prompt Regression Checklist" PDF.

---

## 13 Success KPIs

* 500⭐ GitHub within 3 months.
* 100 monthly active dashboards.
* \$1 k MRR by Month 4 (≈ 90 Pro seats).
* Mean run overhead < 5 s.
* Net promoter score > 50.

---

## 14 Risks & Mitigations

| Risk                                   | Likelihood | Impact | Mitigation                                                 |
| -------------------------------------- | ---------- | ------ | ---------------------------------------------------------- |
| Competing "CI for LLMs" launches       | Med        | Med    | Leverage Trash-Panda brand voice; ship faster, OSS halo    |
| Supabase cost overrun                  | Low        | Low    | Start on free tier, move to RLS-enabled Postgres if needed |
| Provider API changes (pricing, limits) | Med        | Low    | Abstract model adapters; version-pin tests                 |
| Burnout / solo-founder                 | Med        | High   | Scope ruthlessly; weekly milestones; ask community for PRs |

---

## 15 Brand & Tone Guidelines

* Mascot: a mini raccoon engineer with CI hard-hat.
* Tone: dry humor, sarcastic quips ("Your prompts failed harder than my last startup.").
* Colors: reuse Hoff & Pepper secondary palette (#7A8F69, #F3EFE7) with accent orange for pass/fail.

---

## 16 Next Immediate Actions

1. **Grab repo & package names** – `evalloop` on GitHub, PyPI, npm.
2. **Write first failing test** using Trash Panda summary format.
3. **Set up project Kanban** (GitHub Projects) with Week-1 tasks.
4. Schedule check-in with GPT for spec refinement & code scaffolding.

---

## 17 Project Tasks

*Detailed project tasks and their statuses are tracked in the `PROJECT_TASKS.yaml` file in the root of this repository.*

---

## 18 Decision Log

*This section will record key decisions made throughout the project, along with their rationale.*

| Date       | Decision                                                                 | Rationale                                                                                                | Participants |
|------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|--------------|
| 2025-05-15 | Use `README.md` as the single source of truth for tasks and decision log. | Keep project planning and documentation centralized and version-controlled alongside the codebase.         | User, Gemini |
| 2025-05-15 | Defer use of GitHub Projects (Kanban board).                             | `README.md` is sufficient for task tracking at the current project stage and team size. Simplicity.        | User, Gemini |
| 2025-05-16 | Moved detailed task tracking from `README.md` to `PROJECT_TASKS.yaml`.   | Improve reliability of AI-assisted task status updates; better structure for complex task lists.         | User, Gemini |
|            |                                                                          |                                                                                                          |              |

---

*End of Document – keep this file as the project's living reference; version & timestamp changes at top on each major edit.*
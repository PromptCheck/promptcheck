# ... (previous content of README.md section 9) ...
| Layer     | Choice                               | Rationale                  |
| --------- | ------------------------------------ | -------------------------- |
| CLI       | Python 3.11 + Typer                  | Fast dev, easy install     |
| Metrics   | `rouge-score`, regex, custom funcs   | Lightweight deps           |
|           | NLTK (optional for BLEU)             | Standard for BLEU scores.  |
|           |                                      | (Note: For advanced NLTK tokenization, e.g., `punkt`, users may need to download data separately. See NLTK docs.) |
| Action    | Docker container (`python:slim`)     | Consistent env             |
# ... (rest of the table and file) 

--- 

*End of Document – keep this file as the project's living reference; version & timestamp changes at top on each major edit.*

<!-- Workflow debug trigger --> 
import json
import os
import sys
import subprocess
import textwrap
import pathlib

def main():
    if len(sys.argv) < 2:
        print("Usage: python post_comment.py <path_to_run_json>")
        sys.exit(1)

    json_file_path_str = sys.argv[1]
    json_file_path = pathlib.Path(json_file_path_str)

    if not json_file_path.exists():
        print(f"Error: JSON results file not found at {json_file_path}")
        # Don't exit with error, as a soft-fail in promptcheck might mean no file
        # Or, if promptcheck itself errored before creating file.
        # The GH Action step can continue, just no comment will be posted.
        print("No results JSON found, skipping comment.")
        return

    try:
        run_output_data = json.loads(json_file_path.read_text())
    except Exception as e:
        print(f"Error processing PromptCheck results file {json_file_path}: {e}")
        return

    rows = [
        "| Test Case | Overall Result | First Metric | Score    | Error   |",
        "|-----------|:--------------:|--------------|----------|---------|"
    ]

    total_tests = run_output_data.get("total_tests_executed", 0)
    passed_tests = run_output_data.get("total_tests_passed", 0)
    failed_tests = run_output_data.get("total_tests_failed", 0)

    summary_line = f"**Summary: {passed_tests}/{total_tests} tests passed.**"
    if failed_tests > 0:
        summary_line += f" ({failed_tests} failed)"

    for tr in run_output_data.get("test_results", []):
        test_name = tr.get("test_case_name", "N/A")
        overall_passed_raw = tr.get("overall_test_passed")
        emoji = "✅" if overall_passed_raw is True else ("❌" if overall_passed_raw is False else "⚠️")
        
        first_metric_name = "N/A"
        first_metric_score = "N/A"
        first_metric_error = tr.get("llm_error", "") # Overall LLM error for the test case

        metrics_data = tr.get("metrics", [])
        if metrics_data:
            first_metric = metrics_data[0]
            first_metric_name = first_metric.get("metric_name", "N/A")
            raw_score = first_metric.get("score")
            if isinstance(raw_score, dict):
                # For dict scores like token_count, just show a summary
                first_metric_score = json.dumps(raw_score)
            elif isinstance(raw_score, bool):
                first_metric_score = "Pass" if raw_score else "Fail"
            elif raw_score is not None:
                try:
                    first_metric_score = f"{float(raw_score):.4f}"
                except (ValueError, TypeError):
                    first_metric_score = str(raw_score)
            
            if first_metric.get("error"):
                first_metric_error = first_metric.get("error")
        
        rows.append(f"| {test_name} | {emoji} | {first_metric_name} | {first_metric_score} | {textwrap.shorten(first_metric_error or '-', width=50, placeholder='...')} |")

    # Construct Markdown content
    md_body = textwrap.dedent(f"""
    ### PromptCheck Test Results
    {summary_line}

    {os.linesep.join(rows)}
    """)

    pr_number = os.environ.get("PR_NUMBER")
    github_repo = os.environ.get("GITHUB_REPOSITORY")
    github_token = os.environ.get("GH_TOKEN")

    if not pr_number:
        print("PR_NUMBER environment variable not found. Skipping comment.")
        # If running not in a PR context, just print the markdown for local testing.
        print("\n--- Generated Markdown --- ")
        print(md_body)
        print("------------------------")
        return

    if not github_repo:
        print("GITHUB_REPOSITORY environment variable not found. Skipping comment.")
        return
    
    if not github_token:
        print("GH_TOKEN environment variable not found. Skipping comment.")
        return

    print(f"Posting comment to PR #{pr_number} in repo {github_repo}")
    # Use subprocess to call gh CLI
    try:
        process = subprocess.run([
            "gh", "pr", "comment", pr_number,
            "--body", md_body,
            "--repo", github_repo
        ], check=True, capture_output=True, text=True, env=dict(os.environ, GH_TOKEN=github_token))
        print(f"GH CLI output: {process.stdout}")
        if process.stderr:
             print(f"GH CLI errors: {process.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error calling gh CLI: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
    except FileNotFoundError:
        print("Error: `gh` CLI not found. Ensure it is installed and in PATH in the GitHub Actions runner.")

if __name__ == "__main__":
    main() 
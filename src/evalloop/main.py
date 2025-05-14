import typer
from typing_extensions import Annotated

from evalloop.cli import init_cmd
from evalloop.cli import run_cmd # Import the new run command module

app = typer.Typer(
    name="evalloop",
    help="EvalLoop: Don't merge broken prompts. Automated evaluations for LLM-powered repos.",
    add_completion=False, # We can enable this later if desired
    no_args_is_help=True
)

# Register subcommands
app.add_typer(init_cmd.app, name="init", help="Initialize EvalLoop configuration and example files.")
app.add_typer(run_cmd.app, name="run", help="Run an evaluation suite.")
# app.add_typer(report_cmd.app, name="report", help="Generate a report from evaluation results.") # Placeholder

@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show the application's version and exit.", callback=lambda x: x # Temp callback
        )
    ] = False,
):
    """
    EvalLoop CLI
    """
    if version:
        # This will be replaced with actual version fetching later
        print("EvalLoop CLI version: 0.1.0 (developer preview)") 
        raise typer.Exit()

if __name__ == "__main__":
    app()

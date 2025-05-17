import typer
from typing_extensions import Annotated
import importlib.metadata as _im

from evalloop.cli import init_cmd
from evalloop.cli.run_cmd import run as run_command_func

# Determine application version dynamically
APP_VERSION: str
try:
    APP_VERSION = _im.version("evalloop")
except _im.PackageNotFoundError:
    APP_VERSION = "0.0.0-dev" # Fallback for local development when not installed

app = typer.Typer(
    name="evalloop",
    help="EvalLoop: Don't merge broken prompts. Automated evaluations for LLM-powered repos.",
    add_completion=False,
    no_args_is_help=True
)

# Register subcommands
app.add_typer(init_cmd.app, name="init", help="Initialize EvalLoop configuration and example files.")
app.command("run")(run_command_func) # Register the run function as a command
# app.add_typer(report_cmd.app, name="report", help="Generate a report from evaluation results.") # Placeholder

@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v", 
            help="Show the application's version and exit.", 
            callback=lambda value: (
                print(f"EvalLoop CLI version: {APP_VERSION}") or typer.Exit() 
                if value 
                else None
            ),
            is_eager=True # Ensures --version is processed before other commands/args
        )
    ] = False,
):
    """
    EvalLoop CLI
    """
    # The callback logic is now handled by typer.Option's callback for --version
    pass

if __name__ == "__main__":
    app()

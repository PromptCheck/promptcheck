import typer
from typing_extensions import Annotated
import importlib.metadata as _im

from promptcheck.cli import init_cmd # Will be correct after dir rename
from promptcheck.cli.run_cmd import run as run_command_func # Will be correct after dir rename

APP_VERSION: str
try:
    APP_VERSION = _im.version("promptcheck") # RENAMED
except _im.PackageNotFoundError:
    APP_VERSION = "0.0.0-dev" 

app = typer.Typer(
    name="promptcheck", # RENAMED
    help="PromptCheck: Don't merge broken prompts. Automated evaluations for LLM-powered repos.", # RENAMED
    add_completion=False,
    no_args_is_help=True
)

app.add_typer(init_cmd.app, name="init", help="Initialize PromptCheck configuration and example files.") # RENAMED
app.command("run")(run_command_func)

@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v", 
            help="Show the application's version and exit.", 
            callback=lambda value: (
                print(f"PromptCheck CLI version: {APP_VERSION}") or typer.Exit() # RENAMED
                if value 
                else None
            ),
            is_eager=True 
        )
    ] = False,
):
    """
    PromptCheck CLI
    """
    pass

if __name__ == "__main__":
    app() 
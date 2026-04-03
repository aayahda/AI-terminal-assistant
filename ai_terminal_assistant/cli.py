from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import click


def _history_path() -> Path:
    path = Path.home() / ".ai-cmd" / "history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save_history_entry(query: str, command: str, model: str) -> None:
    path = _history_path()
    try:
        entries = json.loads(path.read_text()) if path.exists() else []
    except (json.JSONDecodeError, OSError):
        entries = []

    entries.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "command": command,
        "model": model,
    })
    path.write_text(json.dumps(entries, indent=2))


def _load_history(limit: int = 10) -> list[dict]:
    path = _history_path()
    try:
        entries = json.loads(path.read_text()) if path.exists() else []
    except (json.JSONDecodeError, OSError):
        entries = []
    return entries[-limit:]


def get_system_prompt() -> str:
    shell = os.environ.get("SHELL", "/bin/bash")
    os_name = platform.system()
    return (
        f"You are a shell command translator. The user is on {os_name} "
        f"using {shell}.\n\n"
        "Given a natural language description, respond with ONLY the shell "
        "command(s) that accomplish the task. No explanations, no markdown "
        "fences, no commentary — just the raw command(s). If multiple "
        "commands are needed, separate them with ' && '. "
        "If the request is ambiguous, output the most likely intended command."
    )


def translate(query: str, model: str) -> str:
    """Send the natural language query to Claude and return the command."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=get_system_prompt(),
        messages=[{"role": "user", "content": query}],
    )
    return response.content[0].text.strip()


@click.command()
@click.argument("query", nargs=-1, required=False)
@click.option(
    "-e", "--execute", is_flag=True, help="Execute the command after confirmation."
)
@click.option(
    "-y", "--yes", is_flag=True, help="Skip confirmation (use with -e)."
)
@click.option(
    "--model",
    default="claude-sonnet-4-6",
    show_default=True,
    help="Claude model to use.",
)
@click.option(
    "-H", "--history", "show_history", is_flag=True,
    help="Show recent command translations.",
)
@click.option(
    "--history-limit", default=10, show_default=True,
    help="Number of history entries to show.",
)
@click.option(
    "--history-clear", is_flag=True,
    help="Clear all command history.",
)
def main(
    query: tuple[str, ...],
    execute: bool,
    yes: bool,
    model: str,
    show_history: bool,
    history_limit: int,
    history_clear: bool,
) -> None:
    """Translate natural language into shell commands using Claude.

    Examples:

    \b
        ai-cmd list all python files recursively
        ai-cmd -e find large files over 100MB
        ai-cmd -ey show disk usage sorted by size
        ai-cmd --history
        ai-cmd --history-clear
    """
    if history_clear:
        _history_path().unlink(missing_ok=True)
        click.secho("History cleared.", fg="yellow")
        return

    if show_history:
        entries = _load_history(history_limit)
        if not entries:
            click.secho("No history yet.", fg="yellow")
            return
        for entry in entries:
            click.secho(f"[{entry['timestamp']}]  ", fg="bright_black", nl=False)
            click.echo(f"\"{entry['query']}\"")
            click.secho(f"  → {entry['command']}", fg="green")
            click.echo()
        return

    if not query:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        raise SystemExit(0)

    prompt = " ".join(query)

    try:
        command = translate(prompt, model)
    except (anthropic.AuthenticationError, TypeError):
        click.secho(
            "Error: ANTHROPIC_API_KEY is not set or is invalid.", fg="red", err=True
        )
        raise SystemExit(1)
    except anthropic.APIError as exc:
        click.secho(f"API error: {exc.message}", fg="red", err=True)
        raise SystemExit(1)

    try:
        _save_history_entry(prompt, command, model)
    except Exception:
        pass

    click.secho("Command:", fg="green", bold=True)
    click.echo(f"  {command}")

    if execute:
        if not yes:
            click.confirm("\nRun this command?", abort=True)

        click.echo()
        result = subprocess.run(command, shell=True)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

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


WEB_SEARCH_KEYWORDS = {
    "latest", "install", "version", "update", "upgrade",
    "new", "download", "release", "current", "setup",
}


def needs_web_search(query: str) -> bool:
    words = set(query.lower().split())
    return bool(words & WEB_SEARCH_KEYWORDS)


def get_steps_system_prompt() -> str:
    shell = os.environ.get("SHELL", "/bin/bash")
    os_name = platform.system()
    return (
        f"You are a shell command translator. The user is on {os_name} "
        f"using {shell}.\n\n"
        "Break the task into sequential shell commands. "
        "Respond with a JSON array ONLY — no explanation, no markdown fences. "
        "Each item must have:\n"
        '  "command": the exact shell command\n'
        '  "description": a short human-readable label for this step\n\n'
        "Keep each command atomic (one action per step). "
        "Do not chain commands with &&."
    )


def translate_steps(query: str, model: str, web_search: bool = False) -> list[dict]:
    """Ask Claude to break a task into sequential steps, returned as a list of dicts."""
    client = anthropic.Anthropic()

    kwargs: dict = dict(
        model=model,
        max_tokens=2048,
        system=get_steps_system_prompt(),
        messages=[{"role": "user", "content": query}],
    )

    if web_search:
        kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search"}]

    response = client.messages.create(**kwargs)

    text_blocks = [b for b in response.content if b.type == "text"]
    if not text_blocks:
        raise ValueError("No response received from Claude.")

    raw = text_blocks[-1].text.strip()
    # Strip accidental markdown fences if Claude adds them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(raw)


def run_steps(steps: list[dict], yes: bool) -> None:
    """Display the plan, confirm, then execute each step sequentially."""
    total = len(steps)

    click.secho("\nPlan:", bold=True)
    for i, step in enumerate(steps, 1):
        click.secho(f"  {i}/{total} ", fg="bright_black", nl=False)
        click.echo(step["description"])
        click.secho(f"       $ {step['command']}", fg="cyan")

    click.echo()
    if not yes:
        click.confirm("Execute all steps?", abort=True)
    click.echo()

    cwd = os.getcwd()

    for i, step in enumerate(steps, 1):
        cmd = step["command"]
        desc = step["description"]

        click.secho(f"Step {i}/{total}: ", fg="bright_black", nl=False)
        click.echo(desc)
        click.secho(f"  $ {cmd}", fg="cyan", nl=False)

        # Handle cd specially — update working dir instead of running subprocess
        if cmd.startswith("cd "):
            target = cmd[3:].strip()
            new_cwd = os.path.join(cwd, target)
            if os.path.isdir(new_cwd):
                cwd = os.path.abspath(new_cwd)
            click.secho("  ✓", fg="green")
            continue

        result = subprocess.run(cmd, shell=True, cwd=cwd)
        if result.returncode != 0:
            click.secho("  ✗", fg="red")
            click.secho(f"\nStep {i} failed (exit {result.returncode}). Stopping.", fg="red")
            raise SystemExit(result.returncode)

        click.secho("  ✓", fg="green")

    click.echo()
    click.secho("Done!", fg="green", bold=True)


def translate(query: str, model: str, web_search: bool = False) -> str:
    """Send the natural language query to Claude and return the command."""
    client = anthropic.Anthropic()

    kwargs: dict = dict(
        model=model,
        max_tokens=1024,
        system=get_system_prompt(),
        messages=[{"role": "user", "content": query}],
    )

    if web_search:
        kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search"}]

    response = client.messages.create(**kwargs)

    # With web search, content may contain server_tool_use blocks before the text.
    # Find the last text block which has the final command.
    text_blocks = [b for b in response.content if b.type == "text"]
    if not text_blocks:
        raise ValueError("No text response received from Claude.")
    return text_blocks[-1].text.strip()


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
@click.option(
    "-w", "--web", "force_web", is_flag=True,
    help="Force web search before generating the command.",
)
@click.option(
    "--no-search", is_flag=True,
    help="Disable automatic web search even for version-sensitive queries.",
)
@click.option(
    "-s", "--steps", "multi_step", is_flag=True,
    help="Break the task into sequential steps and execute them one by one.",
)
def main(
    query: tuple[str, ...],
    execute: bool,
    yes: bool,
    model: str,
    show_history: bool,
    history_limit: int,
    history_clear: bool,
    force_web: bool,
    no_search: bool,
    multi_step: bool,
) -> None:
    """Translate natural language into shell commands using Claude.

    Examples:

    \b
        ai-cmd list all python files recursively
        ai-cmd -e find large files over 100MB
        ai-cmd -ey show disk usage sorted by size
        ai-cmd install the latest version of node.js        (auto web search)
        ai-cmd --no-search update homebrew                  (skip web search)
        ai-cmd -s "set up a python project called myapp"    (multi-step)
        ai-cmd -sy "create a venv and install flask"        (multi-step, no confirm)
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

    use_web = (force_web or needs_web_search(prompt)) and not no_search

    if use_web:
        click.secho("Searching the web...", fg="bright_black")

    # --- Multi-step mode ---
    if multi_step:
        try:
            steps = translate_steps(prompt, model, web_search=use_web)
        except (anthropic.AuthenticationError, TypeError):
            click.secho(
                "Error: ANTHROPIC_API_KEY is not set or is invalid.", fg="red", err=True
            )
            raise SystemExit(1)
        except anthropic.APIError as exc:
            click.secho(f"API error: {exc.message}", fg="red", err=True)
            raise SystemExit(1)
        except (json.JSONDecodeError, ValueError) as exc:
            click.secho(f"Failed to parse steps from Claude: {exc}", fg="red", err=True)
            raise SystemExit(1)

        run_steps(steps, yes=yes)
        return

    # --- Single-command mode ---
    try:
        command = translate(prompt, model, web_search=use_web)
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

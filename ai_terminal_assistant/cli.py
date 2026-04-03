from __future__ import annotations

import os
import platform
import subprocess
import sys

import anthropic
import click


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
@click.argument("query", nargs=-1, required=True)
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
def main(query: tuple[str, ...], execute: bool, yes: bool, model: str) -> None:
    """Translate natural language into shell commands using Claude.

    Examples:

    \b
        ai-cmd list all python files recursively
        ai-cmd -e find large files over 100MB
        ai-cmd -ey show disk usage sorted by size
    """
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

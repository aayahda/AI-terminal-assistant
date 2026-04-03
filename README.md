# AI Terminal Assistant

A CLI tool that converts natural language into shell commands using the Claude API. Just describe what you want to do in plain English and get the exact shell command.

## Features

- Translates natural language to shell commands
- Auto-detects your OS and shell for accurate commands
- Optional command execution with confirmation prompt
- Configurable Claude model

## Installation

```bash
git clone git@github.com:aayahda/AI-terminal-assistant.git
cd AI-terminal-assistant
pip install -e .
```

## Setup

Get your API key from [console.anthropic.com](https://console.anthropic.com) and set it:

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

To make it permanent:

```bash
echo 'export ANTHROPIC_API_KEY="your-api-key"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

```bash
# Show the command
ai-cmd list all python files recursively

# Show and execute (with confirmation)
ai-cmd -e find files modified in the last 24 hours

# Show and execute immediately (no confirmation)
ai-cmd -ey show disk usage sorted by size
```

### Options

| Flag | Description |
|------|-------------|
| `-e, --execute` | Execute the command after showing it |
| `-y, --yes` | Skip confirmation (use with `-e`) |
| `--model` | Choose a Claude model (default: `claude-sonnet-4-6`) |

## Examples

```bash
$ ai-cmd count lines of code in all python files
Command:
  find . -name "*.py" -exec cat {} + | wc -l

$ ai-cmd compress the logs folder into a tar.gz
Command:
  tar -czf logs.tar.gz logs/

$ ai-cmd show top 10 processes by memory usage
Command:
  ps aux --sort=-%mem | head -11
```

## License

MIT

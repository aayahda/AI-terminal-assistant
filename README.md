# AI Terminal Assistant

A CLI tool that converts natural language into shell commands using the Claude API. Just describe what you want to do in plain English and get the exact shell command.

## Features

- Translates natural language to shell commands
- Auto-detects your OS and shell for accurate commands
- Optional command execution with confirmation prompt
- Command history — stores past translations for quick reference
- Smart web search — automatically searches the web for queries containing words like "install", "latest", "version", "update"
- Multi-step execution — breaks complex tasks into sequential steps and runs them one by one
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
| `-H, --history` | Show recent command translations |
| `--history-limit N` | Number of history entries to show (default: 10) |
| `--history-clear` | Clear all command history |
| `-w, --web` | Force web search regardless of query keywords |
| `--no-search` | Disable automatic web search |
| `-s, --steps` | Break task into sequential steps and execute one by one |

## Examples

### Basic Commands

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

### Web Search (auto-triggered)

```bash
$ ai-cmd install the latest version of node.js
Searching the web...
Command:
  brew install node

$ ai-cmd what version of python is installed
Searching the web...
Command:
  python3 --version

$ ai-cmd --no-search update homebrew
Command:
  brew update
```

### Command History

```bash
$ ai-cmd --history
[2026-04-05 10:22:01]  "list all python files recursively"
  → find . -name "*.py"

[2026-04-05 10:25:14]  "show disk usage sorted by size"
  → du -sh * | sort -rh

$ ai-cmd --history --history-limit 5   # show last 5 entries
$ ai-cmd --history-clear               # wipe history
```

### Multi-step Execution

```bash
$ ai-cmd -s "set up a new python project called weather-app with a venv, install requests and fastapi, and create a main.py"

Plan:
  1/5 Create project directory
       $ mkdir weather-app
  2/5 Navigate into the directory
       $ cd weather-app
  3/5 Create a virtual environment
       $ python3 -m venv venv
  4/5 Install dependencies
       $ pip install requests fastapi
  5/5 Create main.py
       $ touch main.py

Execute all steps? [y/N]: y

Step 1/5: Create project directory
  $ mkdir weather-app  ✓
Step 2/5: Navigate into the directory
  $ cd weather-app  ✓
Step 3/5: Create a virtual environment
  $ python3 -m venv venv  ✓
Step 4/5: Install dependencies
  $ pip install requests fastapi  ✓
Step 5/5: Create main.py
  $ touch main.py  ✓

Done!

# Skip confirmation with -y
$ ai-cmd -sy "create a logs directory and an empty app.log file"
```

## License

MIT

# Choosing Your Clean Hands Executor

The executor is **pluggable** — any process that can read a task packet and write a compact result works. Pick by your needs: cost, model quality, platform, and whether you want headless (Auto mode) or visual (Watched mode).

## Requirements

A valid clean hands executor must:

1. **Read files** — parse the task packet (JSON/Markdown)
2. **Follow instructions** — execute only what the packet says
3. **Write files** — output compact result + raw quarantine
4. **Signal completion** — print a marker or exit cleanly
5. **Stay in scope** — no strategy decisions, no scope expansion

## Recommended Executors

### CLI-based (headless — best for Auto mode)

| Executor | Command pattern | Cost tier | Notes |
|---|---|---|---|
| **OpenAI Codex CLI** | `codex exec -s workspace-write $prompt` | Low–Mid | Built for file-level tasks, `--skip-git-repo-check` for non-git dirs |
| **Claude Code CLI** | `claude --print -p "$prompt"` | Mid–High | `--print` for non-interactive, `--allowedTools` to restrict |
| **Aider** | `aider --message "$prompt" --yes-always` | Configurable | Multi-model, auto-commit, good for code-heavy tasks |
| **Google Gemini CLI** | `gemini -p "$prompt"` | Low | Large context window, good for bulk parsing |
| **Ollama + custom script** | `ollama run <model> "$prompt"` | Free (local) | No cloud cost, limited by local GPU, good for offline/air-gapped |
| **Custom Python/Bash script** | `python executor.py packet.json` | Free | No LLM needed for deterministic tasks (regex, parsing, formatting) |

### IDE-based (visual — best for Watched mode)

| Executor | How to use as clean hands | Notes |
|---|---|---|
| **Cursor** | Open workspace, paste packet as prompt, watch it work | Good for complex multi-file refactors |
| **Windsurf (Codeium)** | Cascade mode with packet instructions | Flow-based, stays on task well |
| **VS Code + Continue.dev** | Feed packet to Continue chat, watch file writes | Open source, multi-model |
| **VS Code + GitHub Copilot** | Copilot Chat with packet as context | Integrated, widely available |
| **JetBrains + AI Assistant** | AI chat with packet, watch file output | Good for JVM/typed languages |

### Non-LLM (deterministic — free, fast, predictable)

For many clean-hands tasks (log parsing, regex extraction, format conversion, batch grep), you don't need an LLM at all:

- **Python script** — like `demo/executor.py`, pure stdlib
- **jq / yq** — JSON/YAML transformation
- **ripgrep + awk** — pattern extraction from large files
- **Custom ETL pipeline** — any script that reads input → writes output

The demo's `executor.py` is a working example of this. An LLM executor is only needed when the task requires language understanding (summarization, classification, code analysis).

## Configuration

### Launcher template (PowerShell — adapt for your shell)

```powershell
# Encoding header (required for non-ASCII paths on Windows PS 5.1)
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Set-Location "<WORKSPACE_ROOT>"

$prompt = @"
Read the task packet at <PACKET_PATH> (UTF-8 encoding).
Execute it exactly. Write results to the paths specified in the packet.
When done print CLEAN_HANDS_DONE.
"@

# --- SWAP THIS LINE for your executor ---
# Codex CLI:
codex exec --skip-git-repo-check -s workspace-write -c model="<MODEL>" $prompt

# Claude Code CLI:
# claude --print -p $prompt --allowedTools "Read,Write,Bash"

# Aider:
# aider --message $prompt --yes-always --no-git

# Custom script:
# python executor.py <PACKET_PATH>
```

### Launcher template (Bash — Linux/macOS)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "<WORKSPACE_ROOT>"

PROMPT="Read the task packet at <PACKET_PATH> (UTF-8). Execute it exactly. Write results to the paths in the packet. When done print CLEAN_HANDS_DONE."

# --- SWAP THIS LINE for your executor ---
# Codex CLI:
codex exec --skip-git-repo-check -s workspace-write -c model="<MODEL>" "$PROMPT"

# Claude Code CLI:
# claude --print -p "$PROMPT" --allowedTools "Read,Write,Bash"

# Aider:
# aider --message "$PROMPT" --yes-always --no-git

# Ollama (local):
# ollama run <model> "$PROMPT"

# Custom script:
# python executor.py <PACKET_PATH>
```

## Cross-Vendor Cost Arbitrage

One of the pattern's real advantages: the rich brain and clean hands can run on **different models from different vendors**. This lets you optimize cost:

| Rich brain (decides) | Clean hands (executes) | Why |
|---|---|---|
| Claude Opus / Sonnet | Codex CLI (GPT) | Strong reasoning brain + cheap bulk executor |
| Claude Opus | Gemini | Large context for massive file parsing |
| GPT-4o | Ollama (local Llama) | Zero cloud cost for clean hands |
| Any premium model | Custom Python script | Zero LLM cost for deterministic tasks |

The key insight: the clean hands executor doesn't need to be smart — it needs to be obedient, cheap, and good at following a narrow packet. Use your expensive model for the brain, your cheap one for the hands.

## Adding a New Executor

To wire up an executor not listed here:

1. Verify it can: read files, follow instructions, write files, run non-interactively (for Auto mode)
2. Write a one-liner launch command that passes the task packet prompt
3. Test with the demo: `python demo/run_demo.py` (replace the subprocess call with your executor)
4. For Auto mode: ensure it exits cleanly (no "press Enter" prompts)
5. For Watched mode: run in a visible terminal and watch

The pattern doesn't care what the executor is — only that the **file hand-off discipline** is maintained.

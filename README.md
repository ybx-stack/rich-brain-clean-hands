# Rich Brain / Clean Hands

> A two-brain delegation pattern for LLM agents — keep the deciding brain's context clean, exile the heavy deterministic work to an isolated executor, and only ever pull back compressed results.

**Status: v0.2** — runnable demo + multi-mode architecture. Feedback welcome.

一句话中文：**富脑负责决策、净手负责脏活**——把大输出、低决策的确定性重活丢给一个隔离的执行器进程，主脑永远只读回压缩后的结果，从机制上挡住上下文污染和 token 浪费。

---

## Quick Start

```bash
git clone https://github.com/ybx-stack/rich-brain-clean-hands.git
cd rich-brain-clean-hands/demo
python run_demo.py
```

No API keys, no external deps — pure Python stdlib. See [`demo/`](demo/) for details.

## The Problem

LLM agents are **stateless**: every turn re-sends the *entire* context to the model. As an agent works, its context fills with raw tool output — decompiler dumps, 2 MB JS bundles, log floods — and two things go wrong:

1. **Context pollution** — the deciding model drowns in noise it doesn't need in order to decide.
2. **Token cost** — every polluted turn is re-sent in full, so the noise is paid for again, and again, and again.

Sub-agents help by isolating work in a separate context. But they have a quiet failure mode: **the sub-agent's final message flows straight back into the main context.** One chatty return re-pollutes everything you just isolated.

## The Pattern

Split the agent into two roles:

- **Rich Brain (富脑)** — decides, routes, reads only compact results. Its context is kept deliberately clean and small.
- **Clean Hands (净手)** — a separate, isolated executor *process* that does the heavy deterministic work: bulk extraction, decompilation parsing, bundle analysis, batch processing.

Three disciplines make it more than "just a sub-agent":

1. **Process isolation** — clean hands runs as its own process with its own context window. It can even be a **different model / vendor** (the reference implementation uses a cross-vendor CLI). The rich brain's token budget never absorbs the executor's.
2. **File as the only hand-off** — raw output goes to a `RAW/` quarantine the rich brain is *forbidden* to read; refined output goes to a compact result file.
3. **The read-back is forcibly compressed** — the rich brain only ever reads a small structured result (JSON), never the executor's full log. This is exactly what sub-agents don't enforce: **the return channel is clamped shut, so it can't re-pollute.**

> Pull raw → write to file → forget → let clean hands refine → read only the digest.

## Three-Way Task Split (decide first)

Before any delegation mechanics, decide **who** does the work:

| Class | Who does it | When |
|---|---|---|
| **Rich brain solo** | Rich brain only | Browser/interactive work, live decisions, output < 50 lines |
| **Rich brain pulls + clean hands refines** | Both | Data behind a barrier (login, WAF, CAPTCHA) — rich brain does minimal pull, clean hands does bulk parsing |
| **Clean hands full** | Clean hands only | Local / offline / no access barrier |

Only the last two delegate. Launch styles below apply only to them.

## Two Data Acquisition Modes

| Mode | Data flow | When |
|---|---|---|
| **Mode A — Clean Hands Full** | Clean hands pulls raw → refines → writes compact result | Source is local, offline, or freely accessible |
| **Mode B — Rich Brain Pulls** | Rich brain pulls data → writes to RAW/ → clean hands refines | Source needs browser, MCP, login, WAF bypass, CAPTCHA |

Key rule for Mode B: the rich brain pulls data and **immediately writes it to file**. Do NOT keep large raw data in the conversation context. Pull → save → forget → delegate.

## Three Launch Styles

| Style | Rich brain's posture | Completion signal | When |
|---|---|---|---|
| **Auto — background** (default) | Fires executor, lets go | Process exit → harness auto-resumes | Long/unknown-duration work |
| **Auto — foreground** | Blocks on the call | Call returns when executor exits | Clearly tiny tasks only (seconds) |
| **Watched** | Opens a visible window | Human reports "done" | New task type, fuzzy boundary, debugging |

**Default to background.** Agents systematically underestimate task duration. Guessing wrong on foreground risks hitting the harness timeout wall → killed process → stuck state. When in doubt, background.

## Related Work / Prior Art

This pattern is **convergent** with existing ideas, stated plainly:

- **Sub-agents** (e.g. Claude Code's Task tool) — isolated context, but **no enforced compression of the return message**.
- **CrewAI / AutoGen / LangGraph handoffs** — multi-agent orchestration, typically same-vendor and in-process.
- **Blackboard systems** — shared external store as the coordination medium; the file-mediated hand-off here is a descendant.
- **External memory / RAG** — moving state out of the window; the same instinct applied at the agent orchestration layer.

**What this contributes is the discipline layer, not a new paradigm:** cross-vendor process isolation + a file-mediated, forcibly-compressed return channel that *structurally* prevents return-pollution.

## Executor — Choose Your Own

The clean hands executor is **pluggable**. Use whatever fits your stack:

| Type | Examples |
|---|---|
| **LLM CLI** (headless, Auto mode) | OpenAI Codex CLI, Claude Code CLI, Aider, Gemini CLI, Ollama |
| **IDE** (visual, Watched mode) | Cursor, Windsurf, VS Code + Continue/Copilot, JetBrains AI |
| **No LLM** (deterministic) | Python scripts, jq/ripgrep pipelines, custom ETL |

Full comparison and launcher templates: [`docs/EXECUTORS.md`](docs/EXECUTORS.md).

The rich brain and clean hands can run on **different models from different vendors** — use your expensive model for the brain, your cheap one for the hands.

## Reference Implementation

- **Runnable demo** — [`demo/`](demo/). Self-contained, no API keys needed, `python run_demo.py`.
- **Full pattern write-up** — [`docs/PATTERN.md`](docs/PATTERN.md). Detailed mechanics, field notes, encoding fixes.
- **Executor guide** — [`docs/EXECUTORS.md`](docs/EXECUTORS.md). CLI/IDE/script options, launcher templates, cost arbitrage.
- **Production SKILL reference** — [`examples/codex-reference/`](examples/codex-reference/). Full decision tree, three worked examples.

## Why the name

A **rich brain** hoards context and makes judgment calls — it must stay unpolluted to think. **Clean hands** do the dirty, bulky, repetitive work and hand back only what's clean enough to eat. The metaphor *is* the architecture.

## Roadmap

- [x] Runnable demo (no API keys needed)
- [x] Multi-mode architecture (Mode A/B + Auto/Watched/Background)
- [x] Pluggable executor guide (CLI / IDE / script — choose your own)
- [x] Cross-platform launchers (PowerShell + Bash templates)
- [x] Worked examples (binary RE, JS bundle, log analysis)
- [ ] pip-installable library with executor adapters
- [ ] Interactive setup wizard ("what's your executor? here's your config")

## License

[MIT](LICENSE) © 2026 ybx-stack

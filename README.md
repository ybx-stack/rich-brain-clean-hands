# Rich Brain / Clean Hands

> A two-brain delegation pattern for LLM agents — keep the deciding brain's context clean, exile the heavy deterministic work to an isolated executor, and only ever pull back compressed results.

**Status: v0.1** — concept + reference implementation. Rough edges expected; the *ideas* are the point. Feedback and discussion welcome.

一句话中文：**富脑负责决策、净手负责脏活**——把大输出、低决策的确定性重活丢给一个隔离的执行器进程，主脑永远只读回压缩后的结果，从机制上挡住上下文污染和 token 浪费。

---

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

1. **Process isolation** — clean hands runs as its own process with its own context window. It can even be a **different model / vendor** (the reference implementation drives a separate CLI). The rich brain's token budget never absorbs the executor's.
2. **File as the only hand-off** — raw output goes to a `RAW/` quarantine the rich brain is *forbidden* to read; refined output goes to a compact result file.
3. **The read-back is forcibly compressed** — the rich brain only ever reads a small structured result (JSON), never the executor's full log. This is exactly what sub-agents don't enforce, and it's the whole point: **the return channel is clamped shut, so it can't re-pollute.**

> Pull raw → write to file → forget → let clean hands refine → read only the digest.

## Three-Way Task Split (the rich brain decides first)

Before any delegation mechanics, decide **who** does the work:

1. **Rich brain solo** — clean hands can't or shouldn't touch it: anything needing a browser / interactive debugging, live decisions, or output too small to be worth delegating. Stays in the rich brain.
2. **Rich brain pulls + clean hands refines** — data is behind a barrier (login, WAF, dynamic runtime), but the *refining* is the heavy part. Rich brain does the minimal pull, hands off the bulk parsing.
3. **Clean hands full** — local / offline / no barrier; clean hands both pulls and refines.

Only #2 and #3 delegate. Launch styles below apply only to them.

## Two Launch Styles

| Style | Rich brain's posture | Completion signal | When |
|---|---|---|---|
| **Auto** (自动挡) | fires the executor and lets go | process exit → auto-resume (short: blocking call; long: background callback) | trusted, deterministic, clear-boundary work |
| **Watched** (监督挡) | opens a visible window and watches | human reports "done" | new task type, fuzzy boundary, debugging — keep an eye on it |

Both share one launcher; only the ending line and the launch command differ. Auto is hands-off; Watched keeps a human in the loop.

## Related Work / Prior Art

This pattern is **convergent** with a lot of existing ideas, and that is stated plainly so there's no confusion about what's actually new:

- **Sub-agents** (e.g. Claude Code's Task tool) — isolated context, but **no enforced compression of the return message**.
- **CrewAI / AutoGen / LangGraph handoffs** — multi-agent orchestration, typically same-vendor and in-process.
- **Blackboard systems** — a shared external store as the coordination medium; the file-mediated hand-off here is a descendant of that idea.
- **External memory / RAG** — moving state out of the window; this is the same instinct applied at the *agent orchestration* layer.

**What this contributes is the discipline layer, not a new paradigm:** cross-vendor process isolation + a file-mediated, forcibly-compressed return channel that *structurally* prevents return-pollution. It is a strict, opinionated take on delegation — deliberately narrow, deliberately enforced.

## Reference Implementation

See [`examples/codex-reference/`](examples/codex-reference/). It drives a separate CLI as the clean-hands executor via a task-packet contract (objective / input / allowed / forbidden / output / stop). **The executor is pluggable** — the reference happens to use one CLI, but any isolated process that reads a packet and writes a compact result fits.

Full write-up of the mechanics: [`docs/PATTERN.md`](docs/PATTERN.md).

## Why the name

A **rich brain** hoards context and makes judgment calls — it must stay unpolluted to think. **Clean hands** do the dirty, bulky, repetitive work and hand back only what's clean enough to eat. The metaphor *is* the architecture: keep the thinker's hands out of the mud, and keep the mud out of the thinker's head.

## Roadmap

- [ ] Decouple from the reference CLI — pluggable executor interface
- [ ] Cross-platform launcher (currently Windows/PowerShell notes included)
- [ ] Minimal quickstart others (and their AIs) can deploy in one shot
- [ ] Worked examples beyond the reference

## License

[MIT](LICENSE) © 2026 ybx-stack

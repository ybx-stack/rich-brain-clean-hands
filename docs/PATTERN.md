# The Rich Brain / Clean Hands Pattern

Detailed mechanics behind the [README](../README.md).

## 1. Why: the stateless re-send tax

An LLM forward pass is a stateless function of its input. There is no persistent memory across calls — "conversation memory" is implemented by **re-sending the entire history every turn**. Prefix/prompt caching lowers the *compute* cost of that re-send, but the context window still fills and is still transmitted, and it still has a ceiling.

The consequence that drives the whole design: **anything that lands in the deciding agent's context is paid for on every subsequent turn.** A 2 MB decompiler dump doesn't cost you once — it costs you every turn until it leaves the window, if it ever does.

Design goal, stated narrowly: **keep large, low-decision-value data out of the deciding agent's context entirely.**

## 2. The two roles

- **Rich Brain (富脑)** — the strategist. Holds the plan, makes judgment calls, routes work, and reads only compact digests. Kept deliberately small and clean so it can *think*.
- **Clean Hands (净手)** — the executor. A separate process that does bulk, deterministic, low-judgment work and writes results to files. Replaceable and re-runnable; it is not the decision-maker.

The rich brain never does bulk work itself. The clean hands never decide strategy.

## 3. The three disciplines

What separates this from "just spawn a sub-agent":

### 3.1 Process isolation
Clean hands is its own OS process with its own context window — and may be a **different model or vendor**. The rich brain's token budget never absorbs the executor's. A blocking or backgrounded call to the executor is, from the rich brain's side, a single tool call it waits on — zero re-send while it waits (structurally identical to a well-behaved sub-agent, but cross-process and cross-vendor).

### 3.2 File as the only hand-off
Raw, noisy output goes to a `RAW/` quarantine directory the rich brain is **forbidden to read**. Refined output goes to a separate compact result file. The filesystem is the coordination medium — a lineage of the classic blackboard pattern.

### 3.3 Forcibly compressed read-back
The rich brain reads **only** a small structured result (JSON preferred), never the executor's full log. This is the discipline sub-agents don't enforce: a sub-agent's final message can be arbitrarily long and flows straight back into the main context. Here the return channel is clamped to a schema, so it **cannot** re-pollute what was just isolated.

> Pull raw → write to file → forget → let clean hands refine → read only the digest.

## 4. Task split — who executes (decide first)

Before any launch mechanics, the rich brain classifies the work:

1. **Rich brain solo** — needs a browser, interactive debugging, live decisions, MCP tools, or output is small enough that delegating costs more than doing it. Never leaves the rich brain; launch styles below do not apply.
2. **Rich brain pulls + clean hands refines** — data is behind a barrier (login, WAF, CAPTCHA, dynamic runtime); the rich brain does the minimal pull to a `RAW/` file, then delegates the bulk parsing. (= Mode B.)
3. **Clean hands full** — local, offline, no barrier; clean hands both pulls and refines. (= Mode A.)

Only #2 and #3 delegate to clean hands.

## 5. Two data acquisition modes

These describe **who gets the data**, not how the executor is launched (that's §6).

### Mode A — Clean Hands Full

Data source is local, offline, or freely accessible. Clean hands handles both acquisition and refinement:

```
Clean hands pulls raw data      → RAW/
Clean hands refines             → outputs/
Rich brain reads compact result → decides next step
```

### Mode B — Rich Brain Pulls, Clean Hands Refines

Data acquisition requires browser interaction, authenticated APIs, WAF bypass, CAPTCHA, or runtime capture (MCP, debugger, Frida). The rich brain does the minimum pull, writes to `RAW/`, then delegates:

```
Rich brain uses browser/MCP to pull → writes to RAW/ (immediately, minimal context)
Rich brain writes task packet        → points clean hands at RAW/ data
Clean hands reads RAW/, refines      → outputs/
Rich brain reads compact result      → decides next step
```

**Key rule for Mode B:** the rich brain pulls data and **immediately writes it to file**. Do NOT keep large raw data in the conversation context. Pull → save → forget → let clean hands process it.

## 6. Launch styles — how the rich brain waits

Applies only to delegated work (#2 / #3). All styles share one launcher; only the ending line and the launch command differ.

### Auto — background (default)

The rich brain fires the executor **detached** and lets go. When the process exits, the harness resumes the rich brain, which then reads the result. No polling, no timeout ceiling.

**This is the default.** Agents systematically underestimate task duration — "parse this file" routinely takes longer than expected. Guessing wrong on foreground risks hitting the harness timeout wall (~8–10 min), which kills the executor mid-work, leaves a zombie process, and causes the rich brain to hallucinate results. When in doubt, use background.

### Auto — foreground

The rich brain runs the executor as a **blocking** call. When the executor exits, the call returns. Use ONLY when the task is clearly tiny (seconds, < 50 lines). If you're weighing whether it qualifies, it doesn't — use background.

### Watched

The executor runs in a **visible window**; a human watches it and reports completion. Use for new task types, fuzzy boundaries, or debugging — anything where you want eyes on the executor so it can't silently drift.

> ⚠️ In Auto, the launcher must **not** end with an interactive prompt (e.g. "press Enter") — nothing is there to answer it, and it will hang forever. Watched keeps such a prompt to hold the window open.

**Rule of thumb:**
- Trusted + deterministic + clear boundary → **Auto background** (default)
- Clearly tiny task (seconds) → **Auto foreground**
- New / risky / needs supervision → **Watched**

## 7. The task packet (delegation contract)

Every delegation is an explicit, traceable contract written to a file before the executor starts:

```json
{
  "objective":         "one sentence: what to extract / process",
  "input":             "exact source paths",
  "allowed_actions":   ["read", "parse", "extract", "format"],
  "forbidden_actions": ["modify input", "decide strategy", "expand scope"],
  "output": {
    "result":          "path for compact JSON result",
    "raw":             "path under RAW/ for noisy output"
  },
  "output_format":     {},
  "stop_conditions":   ["when to stop"]
}
```

The packet doubles as an audit trail: you can see, after the fact, exactly what each executor run was asked to do.

## 8. The result contract

The executor writes a compact JSON result:

```json
{
  "status":    "success | partial | failed | halted",
  "summary":   "1-3 sentences",
  "evidence":  ["key finding 1", "key finding 2"],
  "paths":     { "result": "...", "raw": "..." },
  "omissions": "what was not done"
}
```

The rich brain reads ONLY this file. Never the executor's full log. Never the RAW/ quarantine.

## 9. Field notes (implementation gotchas)

### Windows / PowerShell + non-ASCII (e.g. CJK) paths

If your workspace uses non-ASCII directory names and the executor is launched through Windows PowerShell 5.1, paths can garble. Root cause is **PowerShell 5.1, not the characters** — Git Bash and most native tooling handle them fine. Two fixes, both required:

1. **Save the launcher script as UTF-8 *with BOM*.** PS 5.1 decodes a BOM-less UTF-8 script as the system ANSI code page (e.g. GBK/936), corrupting non-ASCII literals *before the script even runs*.
2. **Set a full UTF-8 block at the top of the launcher:** `chcp 65001`, `[Console]::OutputEncoding`/`InputEncoding` = UTF-8, `$OutputEncoding` = UTF-8. This fixes the encoding of argv passed to the executor child process.

Don't rename paths to ASCII to dodge this — fix the encoding instead.

### Default-to-background rationale

The "default to background" rule exists because of a specific failure chain observed in production:

1. Rich brain guesses a task is short → launches foreground
2. Task takes longer than expected → hits harness timeout (~8–10 min)
3. Foreground call is killed → executor process may zombie
4. Rich brain sees no result → may hallucinate one (fabricate a "result" it never received)

Background launch has none of these failure modes: no timeout ceiling, harness auto-wakes on exit, result is read from file (not fabricated). The only downside is slightly more latency on genuinely tiny tasks — but that's a rounding error compared to the cost of the failure chain above.

### `-ExecutionPolicy Bypass` caution

Some harness configurations deny `-ExecutionPolicy Bypass` for PowerShell. Use plain `-File` to launch scripts. This is not a security recommendation — it's a practical note about what some environments block.

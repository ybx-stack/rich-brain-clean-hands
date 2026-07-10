# Reference Implementation — CLI executor as clean hands

This is *one* concrete wiring of the pattern: the rich brain (an agentic coding CLI) delegates bounded task packets to a **separate CLI process** acting as clean hands. The executor is pluggable — anything that reads a packet and writes a compact result works. Paths below are placeholders (`<WORKSPACE_ROOT>`, `<TARGET>`); adapt to your layout.

## When to delegate

Delegate when ALL hold:
1. Input is deterministic (same input → same output).
2. No browser / interactive judgment / real-time decisions needed.
3. Output would be large enough to pollute the rich brain's context.
4. It's primarily extraction / parsing / formatting / batch work.

Do NOT delegate: browser-driven work, MCP-dependent work, live decisions, or output small enough to handle inline (< 50 lines).

## Task split — who executes (rich brain decides first)

Before any launch mechanics, classify the work:

1. **Rich brain solo** — needs browser/interactive (breakpoints, hooks, CAPTCHA), MCP tools, live judgment, or too small to delegate. Never leaves the rich brain.
2. **Rich brain pulls + clean hands refines** — data is behind a barrier but refining is the heavy part. Rich brain pulls via browser/MCP, dumps to `RAW/`, then hands off bulk parsing. (= Mode B.)
3. **Clean hands full** — local / offline / no barrier; clean hands both pulls and refines. (= Mode A.)

Only #2 and #3 delegate. Launch styles below apply only to them.

## Data acquisition modes

### Mode A — Clean Hands Full (no access barriers)

```
Clean hands pulls raw data      → RAW/
Clean hands refines             → outputs/
Rich brain reads compact result → decides next step
```

### Mode B — Rich Brain Pulls, Clean Hands Refines (access barriers)

```
Rich brain pulls via browser/MCP → writes to RAW/ (immediately, forget)
Rich brain writes task packet     → points clean hands at RAW/ data
Clean hands reads RAW/, refines   → outputs/
Rich brain reads compact result   → decides next step
```

## Flow

```
1. Rich brain writes a task packet to file        (traceability)
2. Rich brain launches the executor               (Auto bg / Auto fg / Watched)
3. Completion signal                              (bg: harness wake / fg: call returns / watched: human)
4. Rich brain reads ONLY the compact result JSON   (context stays clean)
```

## Launcher template (`run_packet.ps1`)

Save as **UTF-8 with BOM** if any path is non-ASCII (see PATTERN.md field notes). Body is identical for all launch styles:

```powershell
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Set-Location "<WORKSPACE_ROOT>"
$packet = "<PACKET_RELATIVE_PATH>"
$prompt = @"
Read the task packet at $packet (UTF-8). Execute it exactly. Write results to the paths in the packet. When done print CLEAN_HANDS_DONE.
"@
<EXECUTOR_CLI> exec --workspace-write -c model="<MODEL>" $prompt
```

Then append ONE ending line:
- **Auto**: `Write-Host "CLEAN_HANDS_LAUNCHER_DONE"` — NO interactive read (would hang forever).
- **Watched**: `Read-Host "Press Enter to close"` — holds the window open.

## Launch commands

### Auto — background (DEFAULT)

```bash
<shell> -NoProfile -File "<FULL_PATH>/run_packet.ps1" > "<LOG_PATH>" 2>&1
# run detached (harness background); auto-resumes rich brain on exit
# then: grep CLEAN_HANDS_DONE in log, read compact result JSON
```

**Default to background.** Agents systematically underestimate task duration. Guessing wrong on foreground → timeout wall → killed process → rich brain hallucinating results. When in doubt, background.

### Auto — foreground (tiny tasks ONLY)

Same command, NOT detached. Blocks then returns. Use ONLY when the task is clearly tiny (seconds, < 50 lines). If you're weighing whether it qualifies, it doesn't — use background.

### Watched (visible window, human reports)

```bash
<shell> -Command "Start-Process <shell> -ArgumentList '-NoExit','-File','<FULL_PATH>/run_packet.ps1'"
```

The executor runs in a visible window; a human watches and reports completion. Use for new task types, fuzzy boundaries, or debugging.

## Executor contract (what clean hands must obey)

- Execute ONLY the packet. Do not decide strategy, expand scope, or explore.
- Do not ask questions; if ambiguous, make the conservative choice and note it.
- Write raw/noisy output to the RAW quarantine path; return only summaries + key findings.
- Emit a compact result file:

```json
{
  "status": "success | partial | failed | halted",
  "summary": "1-3 sentences",
  "evidence": ["key finding 1", "key finding 2"],
  "paths": { "result": "...", "raw": "..." },
  "omissions": "what was not done"
}
```

## Task packet template

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

## Result packet example

```json
{
  "status": "success",
  "summary": "Extracted 42 API endpoints from the bundle.",
  "evidence": ["/api/v1/login [POST]", "/api/v1/user [GET]"],
  "paths": {
    "result": "<TARGET>/outputs/endpoints.json",
    "raw": "<TARGET>/RAW/bundle_grep_raw.txt"
  },
  "omissions": "none"
}
```

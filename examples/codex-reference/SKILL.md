# Reference Implementation — CLI executor as clean hands

This is *one* concrete wiring of the pattern: the rich brain (an agentic coding CLI) delegates bounded task packets to a **separate CLI process** acting as clean hands. The executor is pluggable — anything that reads a packet and writes a compact result works. Paths below are placeholders (`<WORKSPACE_ROOT>`, `<TARGET>`); adapt to your layout.

## When to delegate

Delegate when ALL hold:
1. Input is deterministic (same input → same output).
2. No browser / interactive judgment / real-time decisions needed.
3. Output would be large enough to pollute the rich brain's context.
4. It's primarily extraction / parsing / formatting / batch work.

Do NOT delegate: browser-driven work, decisions ("what next?"), or output small enough to handle inline.

## Flow

```
1. Rich brain writes a task packet to file        (traceability)
2. Rich brain launches the executor               (Auto or Watched)
3. Completion signal                              (Auto: process exit / Watched: human)
4. Rich brain reads ONLY the compact result JSON  (context stays clean)
```

## Launcher template (`run_packet.ps1`)

Save as **UTF-8 with BOM** if any path is non-ASCII (see PATTERN.md field notes). Body is identical for both launch styles:

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
- **Auto**: `Write-Host "CLEAN_HANDS_LAUNCHER_DONE"` — NO interactive read (would hang forever in Auto).
- **Watched**: `Read-Host "Press Enter to close"` — holds the window open for inspection.

## Launch commands

**Auto — short (foreground, blocks then returns):**
```bash
<shell> -File "<FULL_PATH>/run_packet.ps1" > "<LOG_PATH>" 2>&1
# then: grep CLEAN_HANDS_DONE in the log, read the compact result JSON
```

**Auto — long (background):** run the same command detached; resume and read the result when the process exits.

**Watched (visible window, human reports completion):**
```bash
<shell> -Command "Start-Process <shell> -ArgumentList '-NoExit','-File','<FULL_PATH>/run_packet.ps1'"
```

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

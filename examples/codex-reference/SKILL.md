# Clean Hands Delegation — Full Reference Implementation

This is the production-grade SKILL file that the rich brain loads when it needs to delegate. It covers the complete decision tree: when to delegate, who pulls data, how to launch, how to wait, how to read results. Paths use `<WORKSPACE>` / `<TARGET>` placeholders — adapt to your layout.

The executor is **pluggable**. This reference uses a CLI executor, but any process that reads a packet and writes a compact result works. See [`docs/EXECUTORS.md`](../../docs/EXECUTORS.md) for alternatives.

---

## When to Use

Delegate when the task meets ALL of these criteria:

1. Input is deterministic (same input = same output every time)
2. Does not require interactive judgment, browser, MCP, or real-time decision making
3. Would produce large output that pollutes rich brain context
4. Is primarily extraction, formatting, parsing, or batch processing

### High-frequency delegation targets

**Software reverse engineering:**
- Batch extract function signatures, strings, xrefs from disassembly output
- Parse large decompilation output by function granularity
- Symbol table / import-export table extraction and formatting
- YARA rule batch scanning
- Binary diff (patch diffing) between versions
- Large disassembly listing filtering and structuring

**Web / JS reverse engineering:**
- Webpack/Vite bundle splitting and endpoint extraction
- Batch grep API routes, encryption functions, token logic from JS files
- Source map restoration and batch code analysis
- HAR/traffic file batch processing and classification
- Large response body parsing and normalization

**General:**
- Log file analysis and pattern extraction
- Configuration audit across multiple files
- Dependency tree analysis
- Large CSV/JSON dataset transformation

### DO NOT delegate when

- Browser interaction needed (breakpoints, hooks, CAPTCHA)
- MCP tools needed (IDA MCP, browser automation MCP, Burp MCP)
- Strategy decision needed ("what should we try next?")
- Output is small enough to handle inline (< 50 lines)

---

## Task Split — Who Executes (rich brain decides first)

Before any launch mechanics, decide WHO does the work. Three classes:

1. **Rich brain solo (富脑独做)** — clean hands can't or shouldn't touch it. Needs browser/interactive (web verification bypass, breakpoints, hooks, Frida, CAPTCHA, watching responses to adjust live), or MCP (browser automation / Burp / IDA), or judgment (what to try next, which chain is worth it), or too small (< 50 lines — delegating costs more than doing it). The launch styles in Step 2 DO NOT apply here; the rich brain just does it.

2. **Rich brain pulls + clean hands refines** — data is behind a barrier but the refining is the heavy part. Rich brain uses MCP/browser to get past verification/login and dumps raw to `RAW/`, then hands off only the bulk parsing. (= Operating Mode B below.)

3. **Clean hands full** — local / offline / no barrier; clean hands both pulls and refines. (= Operating Mode A below.)

Only #2 and #3 delegate to clean hands, so only they reach Step 2's launch styles (Auto / Watched). #1 never leaves the rich brain.

---

## Two Operating Modes

### Mode A — Clean Hands Full (no access barriers)

Use when the data source is local, offline, or freely accessible. Clean hands handles both data acquisition and refinement.

```
Clean hands pulls raw data      → RAW/
Clean hands refines             → outputs/
Rich brain reads refined result → decides next step
```

Applies to: local binaries, downloaded source code, saved JS bundles, offline samples, log files, already-fetched artifacts.

### Mode B — Rich Brain Pulls, Clean Hands Refines (access barriers present)

Use when data acquisition requires browser interaction, MCP tools, login state, WAF bypass, CAPTCHA solving, or any interactive/authenticated access. Rich brain does the minimum pull, then delegates refinement.

```
Rich brain uses MCP/browser to pull data → writes to RAW/ (minimal context pollution)
Rich brain writes task packet             → points clean hands at RAW/ data
Clean hands reads RAW/, refines           → outputs/
Rich brain reads refined result           → decides next step
```

Applies to: WAF-protected pages, authenticated API responses, CAPTCHA-gated content, dynamic JS that needs runtime capture, browser-rendered content.

Key rule for Mode B: the rich brain pulls data and **immediately writes it to file** under `RAW/`. Do NOT keep large raw data in the conversation context. Pull → save → forget → let clean hands process it.

---

## Delegation Flow

```
Step 1: Write task packet to file (traceability)
Step 2: Launch & wait — Auto (fg/bg, no human) or Watched (new window, human reports)
Step 3: Completion signal — Auto: on-exit / harness wake; Watched: user confirms
Step 4: Rich brain reads compact result (context stays clean)
```

## Step 1: Write Task Packet

Before delegating, write a packet file to the target's `packets/` directory.

Filename format: `packet_YYYYMMDD_HHMMSS_<brief-label>.md`

Packet template:

```markdown
# Task Packet

## Objective
[One sentence: what to extract/process]

## Input
[Exact file paths or data sources to read]

## Allowed Actions
[What the executor may do: read, parse, extract, format, run script]

## Forbidden Actions
[What the executor must NOT do: no strategy, no scope expansion, no file deletion]

## Output Path
- Result: [exact path for compact JSON result]
- Raw: [exact path under RAW/ for large output]

## Output Format
[JSON schema or description of expected result structure]

## Stop Conditions
[When to stop: file processed, all functions extracted, error encountered]
```

## Step 2: Launch & Wait — Auto vs Watched

This is about HOW the rich brain waits once a task is delegated to clean hands (only Task-Split #2/#3 reach here). Do NOT confuse with Operating Mode A/B above (which decides who pulls the data). Both launch styles share ONE launcher (encoding header + BOM mandatory on Windows PS 5.1); only the **ending line** and the **launch command** differ.

| Launch style | Use when | Observability |
|---|---|---|
| **Auto** (自动挡) | Mature/trusted deterministic work, clear boundary, don't want to sit in the loop | Black box — rich brain reads log + result after exit |
| **Watched** (监督挡) | First time on a task type, fuzzy boundary, want to watch executor not drift, debugging the packet | Live window — human reports completion |

### Launcher core (`run_packet.ps1` / `run_packet.sh`)

**PowerShell** — save as UTF-8 with BOM (see field notes in PATTERN.md):

```powershell
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Set-Location "<WORKSPACE>"
$prompt = @"
Read the task packet at [PACKET_RELATIVE_PATH] (use UTF-8 encoding when reading). Execute it exactly. Write results to the paths specified in the packet. When done print CLEAN_HANDS_DONE.
"@
<EXECUTOR_COMMAND> $prompt
```

**Bash:**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "<WORKSPACE>"
PROMPT="Read the task packet at [PACKET_RELATIVE_PATH] (UTF-8). Execute it exactly. Write results to the paths in the packet. When done print CLEAN_HANDS_DONE."
<EXECUTOR_COMMAND> "$PROMPT"
```

Then append ONE ending line, by style:
- **Auto**: `Write-Host "CLEAN_HANDS_LAUNCHER_DONE"` (PS) / `echo CLEAN_HANDS_LAUNCHER_DONE` (Bash) — NO interactive read (nothing presses Enter in Auto; it would hang forever).
- **Watched**: `Read-Host "Press Enter to close"` (PS) / `read -p "Press Enter to close"` (Bash) — keeps the window open for inspection.

### Auto launch (自动挡 — no human handshake, rich brain reads result itself)

**Default to background.** Agents systematically underestimate task duration. Guessing wrong on foreground risks hitting the harness timeout wall → killed process → zombie → rich brain hallucinating results. When in doubt, background.

**Background (default) — long or unknown-duration task:**

Run detached. The harness auto-wakes the rich brain when the process exits. No polling, no timeout ceiling:

```bash
# PowerShell launcher:
powershell.exe -NoProfile -File "<FULL_PATH>/run_packet.ps1" > "<LOG_PATH>" 2>&1

# Bash launcher:
bash "<FULL_PATH>/run_packet.sh" > "<LOG_PATH>" 2>&1 &
```

**Foreground — ONLY when the task is clearly tiny** (seconds, < 50 lines, no big-file parse). Same command without detaching; blocks then returns. If you're weighing whether it qualifies, it doesn't — use background.

After exit either way: `grep CLEAN_HANDS_DONE "<LOG_PATH>"`, then read ONLY the compact result JSON. Never pull the executor's full log into context.

### Watched launch (监督挡 — human in the loop)

```bash
# PowerShell:
powershell.exe -Command "Start-Process powershell -ArgumentList '-NoExit', '-File', '<FULL_PATH>/run_packet.ps1'"

# Bash (new terminal):
gnome-terminal -- bash "<FULL_PATH>/run_packet.sh"
# or: open -a Terminal "<FULL_PATH>/run_packet.sh"  (macOS)
```

Executor runs in a visible window; the human watches and reports completion.

## Step 3: Get Completion Signal — by launch style

Never poll or loop.
- **Auto — background (default)**: the harness re-invokes the rich brain on exit — then proceed to Step 4.
- **Auto — foreground (tiny tasks only)**: the call blocks and returns when executor exits — proceed straight to Step 4.
- **Watched**: tell the user *"Executor is running in the new window. Let me know when it's done, or tell me what you see,"* then proceed to Step 4 on their confirmation.

## Step 4: Read Results

When the task signals done:

1. Read the compact result JSON from the output path specified in the packet
2. Do NOT read files under `RAW/` quarantine
3. Summarize findings and decide next action

---

## Example: Software RE Task

Rich brain finds a large binary with 500+ functions in IDA. Needs to extract all crypto-related functions.

**Packet** (`packets/packet_20260701_020000_crypto_func_extract.md`):

```markdown
# Task Packet

## Objective
Extract all functions containing crypto-related operations from the decompiled output.

## Input
- <TARGET>/decompiled_output.c

## Allowed Actions
- Read the decompiled source
- Grep for crypto patterns: AES, DES, RSA, SHA, MD5, HMAC, encrypt, decrypt, cipher, hash, key, iv, salt, nonce
- Extract matching function bodies with their addresses

## Forbidden Actions
- Do not modify the input file
- Do not analyze or judge the crypto strength
- Do not suggest next steps

## Output Path
- Result: <TARGET>/outputs/crypto_functions_extract.json
- Raw: <TARGET>/RAW/crypto_grep_raw.txt

## Output Format
{
  "status": "success|partial|failed",
  "summary": "Found N crypto-related functions",
  "functions": [
    {"name": "sub_401234", "address": "0x401234", "crypto_patterns": ["AES", "encrypt"], "line_count": 45}
  ],
  "paths": {"result": "...", "raw": "..."}
}

## Stop Conditions
- All lines of the input file processed
- Or file exceeds 10MB, process first 10MB and note truncation
```

## Example: Web JS RE Task

Rich brain sees a 2MB webpack bundle. Needs API endpoint inventory.

**Packet** (`packets/packet_20260701_021000_js_endpoint_extract.md`):

```markdown
# Task Packet

## Objective
Extract all API endpoint URLs and fetch/axios call patterns from the webpack bundle.

## Input
- <TARGET>/RAW/app.bundle.js

## Allowed Actions
- Read and parse the JS bundle
- Regex for URL patterns: /api/, /v1/, /v2/, fetch(, axios(, .get(, .post(, .put(, .delete(
- Extract endpoint paths with HTTP methods where identifiable

## Forbidden Actions
- Do not execute the JS
- Do not make any network requests
- Do not judge which endpoints are interesting

## Output Path
- Result: <TARGET>/outputs/js_endpoints.json
- Raw: <TARGET>/RAW/js_endpoint_grep_raw.txt

## Output Format
{
  "status": "success|partial|failed",
  "summary": "Found N unique API endpoints",
  "endpoints": [
    {"path": "/api/v1/user/login", "method": "POST", "source_line": 1234}
  ],
  "paths": {"result": "...", "raw": "..."}
}

## Stop Conditions
- Entire bundle processed
- Or bundle exceeds 5MB, process in chunks and note coverage
```

## Example: Log Analysis Task

Rich brain has a 50MB access log. Needs security-relevant entries.

**Packet** (`packets/packet_20260711_100000_log_security_scan.md`):

```markdown
# Task Packet

## Objective
Extract security-relevant entries from the server access log.

## Input
- <TARGET>/RAW/access.log

## Allowed Actions
- Read the log file
- Grep for patterns: path traversal (../), SQL injection ('OR, UNION SELECT), credential exposure (password, token, secret, api_key), admin endpoints (/admin, /debug, /internal), anomalous status codes (500, 403 bursts), suspicious user-agents

## Forbidden Actions
- Do not modify the log file
- Do not make network requests to any extracted URLs
- Do not prioritize or triage findings

## Output Path
- Result: <TARGET>/outputs/security_findings.json
- Raw: <TARGET>/RAW/security_grep_raw.txt

## Output Format
{
  "status": "success|partial|failed",
  "summary": "Scanned N lines, found M findings across K categories",
  "findings": [
    {"line_num": 42, "category": "credential_exposure", "content": "...", "matched_pattern": "token"}
  ],
  "paths": {"result": "...", "raw": "..."}
}

## Stop Conditions
- All lines processed
- Or file exceeds 50MB, process in 10MB chunks and note coverage
```

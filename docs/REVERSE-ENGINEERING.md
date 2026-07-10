# Reverse Engineering with Rich Brain / Clean Hands

Program reverse engineering is where this pattern pays off the most. RE generates massive low-decision-value output (disassembly listings, decompiled source, string dumps, import tables) that destroys context if the deciding brain touches it directly. This guide covers real-world lessons on how to split RE work between the two brains.

## Why RE is the ideal use case

1. **Output volume** — a single IDA decompile can dump 10,000+ lines. One `strings` run on a packed binary fills pages. The rich brain doesn't need any of that raw noise to decide what to investigate next.
2. **High determinism** — "extract all functions matching pattern X" has one right answer. No judgment needed. Pure clean-hands work.
3. **Strategy is expensive** — deciding *which* function matters, *what* the algorithm does, *where* to set breakpoints — that's the hard part. Every token of noise that displaces strategic reasoning is a direct loss.
4. **Iteration depth** — RE is loops: static → hypothesis → dynamic → refine → repeat. Each loop generates more raw output. Without delegation, the context fills by loop 3.

## The RE task split in practice

| Work type | Who does it | Why |
|---|---|---|
| Decompiler/disassembler output parsing | Clean hands | Bulk, deterministic, huge output |
| String/symbol extraction and filtering | Clean hands | Pattern match, no judgment |
| Import/export table analysis | Clean hands | Structured extraction |
| Binary diff between versions | Clean hands | Deterministic comparison |
| YARA rule batch scanning | Clean hands | Pattern match |
| Function signature bulk extraction | Clean hands | Structured extraction |
| Setting breakpoints, stepping, watching registers | Rich brain | Interactive, needs live judgment |
| Deciding which function to analyze next | Rich brain | Strategy |
| Understanding an algorithm from decompiled code | Rich brain | Reasoning, not extraction |
| Frida hook design and runtime observation | Rich brain | Interactive, adaptive |
| Anti-debug / anti-tamper bypass decisions | Rich brain | Strategy, needs runtime feedback |
| Writing the final analysis / exploit script | Rich brain | Synthesis |

**Rule of thumb:** if it's "extract/list/count/grep/diff", delegate. If it's "understand/decide/adapt/bypass", keep.

## Workflow patterns

### Pattern 1: Static triage (most common)

You have a binary you've never seen. First pass is always bulk extraction.

```
Rich brain:  "New binary. Start static triage."
    ↓
Clean hands packet 1: extract file type, architecture, compiler, packer detection
Clean hands packet 2: extract all strings, filter for URLs/paths/keys/crypto constants
Clean hands packet 3: extract import/export table, flag suspicious APIs (VirtualAlloc, CreateRemoteThread, NtLoadDriver...)
    ↓
Rich brain reads 3 compact results → decides: "packed, anti-debug likely, crypto strings present → focus on unpacking entry, then crypto routine"
```

The rich brain never sees the raw string dump or full import table — only the filtered, categorized digest.

### Pattern 2: Decompiler output processing

IDA/Ghidra produces massive decompiled output. Don't read it all — delegate the parsing.

```
Rich brain:  uses IDA MCP to trigger decompilation → dumps output to RAW/
    ↓ (Mode B: rich brain pulled via MCP, clean hands refines)
Clean hands packet: "Parse the decompiled output. Extract: function list with addresses and line counts, functions containing crypto patterns, functions with network/socket calls, functions referencing registry/file operations. Write structured JSON."
    ↓
Rich brain reads the function inventory → picks 3 functions to analyze in depth → reads ONLY those 3 from the decompiled source (targeted read, not bulk)
```

Key insight: the rich brain goes from "10,000 lines of decompiled C" to "3 functions worth reading" without ever loading the other 9,900 lines.

### Pattern 3: Multi-layer PE/ELF analysis

Complex binaries have layers: outer packer → loader → payload → config. Each layer generates its own bulk output.

```
Layer 1: Rich brain identifies packer → clean hands extracts resource table, section headers, overlay data
Layer 2: Rich brain unpacks (may need dynamic) → clean hands parses unpacked PE headers, new import table
Layer 3: Rich brain identifies payload format → clean hands extracts embedded configs, C2 strings, encoded data
```

Each layer's raw output stays in RAW/. The rich brain carries forward only the compact findings from each layer, keeping its context clean for the next layer's strategic decisions.

### Pattern 4: JS bundle reverse engineering

Modern web apps ship 1–5 MB webpack/vite bundles. Reading them raw is context suicide.

```
Clean hands packet 1: "Split the bundle by webpack module boundaries. List all module IDs with their first-line summary."
    ↓
Rich brain reads module inventory → identifies interesting modules (auth, crypto, API client, payment)
    ↓
Clean hands packet 2: "Extract ONLY modules [id1, id2, id3]. For each, list: exported functions, imported dependencies, string literals, fetch/axios calls."
    ↓
Rich brain reads targeted extraction → analyzes sign/token/nonce generation logic in detail
```

Two rounds of delegation turn a 2 MB blob into 50 lines of relevant code that the rich brain can actually reason about.

### Pattern 5: APK analysis pipeline

Android RE has a natural multi-stage structure:

```
Stage 1 (clean hands): AndroidManifest.xml → package name, entry activities, permissions, network security config
Stage 2 (clean hands): JADX decompile → grep for crypto/sign/verify/certificate/pinning/root-detection patterns
Stage 3 (rich brain decision): based on findings, decide: hook SSL pinning? Analyze native .so? Trace specific method?
Stage 4 (if native .so exists, clean hands): extract .so, run strings + symbol table + import analysis
Stage 5 (rich brain): Frida hook design based on all findings — this is interactive, stays in rich brain
```

### Pattern 6: Patch diffing between versions

Comparing two versions of a binary to find what changed:

```
Clean hands packet: "Diff these two binaries. List: new functions, removed functions, modified functions with change summary. For modified functions, extract both versions side-by-side."
    ↓
Rich brain reads diff summary → focuses on security-relevant changes (auth checks added/removed, crypto changes, new input validation)
```

## Lessons learned

### What works

- **Batch extraction is the #1 delegation target.** Strings, imports, exports, function lists, xrefs, section headers — all deterministic, all huge, all perfect for clean hands.
- **Two-round refinement beats one-round exhaustive.** First packet: broad extraction → compact inventory. Second packet: targeted deep-dive on what the rich brain identified as interesting. This is cheaper and more focused than one giant "extract everything" packet.
- **Mode B is the norm for RE.** Most RE data comes through interactive tools (IDA MCP, debugger, Frida). The rich brain does the minimal pull, immediately writes to RAW/, then delegates the parsing. Pull → save → forget → delegate.
- **The function inventory is the highest-value clean-hands output.** A structured list of all functions with names/addresses/sizes/call-patterns lets the rich brain make strategic decisions without ever reading disassembly.

### What doesn't work

- **Don't delegate "understand this algorithm."** Clean hands will produce a surface-level summary that's often wrong for obfuscated/non-standard code. Algorithm understanding is rich brain work.
- **Don't delegate dynamic analysis decisions.** "Should I set a breakpoint here or there?" requires judgment about the binary's behavior. Keep it in the rich brain.
- **Don't put the entire decompiled output in one packet.** If the input is > 5 MB, split by section/function range. A clean hands executor that chokes on massive input produces nothing.
- **Don't skip the raw quarantine.** It's tempting to have clean hands return a "detailed" result with full function bodies. Resist — that's just raw output with a JSON wrapper. The result should be an index/inventory/summary; the rich brain reads specific functions on demand when it needs depth.

### Pitfalls

- **Packed binaries: static analysis hits a wall.** Clean hands extracts strings from a packed binary and finds nothing useful — because the real strings are encrypted in the payload. The rich brain needs to recognize this early and switch to dynamic (unpack first, then delegate the parsing of unpacked output).
- **Anti-analysis triggers in automated runs.** Some samples detect automated/headless execution and behave differently. If clean hands runs a binary as part of analysis, it might trigger anti-analysis. Keep execution decisions in the rich brain; clean hands should only read files, not run them.
- **Context budget for multi-layer targets.** Each layer of a complex binary generates its own extraction round. After 4–5 layers, even compact results add up. Summarize and drop older layers' details when they're no longer decision-relevant.

## Packet templates for common RE tasks

### String extraction with filtering

```json
{
  "objective": "Extract and categorize strings from binary",
  "input": "<TARGET>/sample.exe",
  "allowed_actions": ["read binary", "extract strings (min length 6)", "categorize by pattern"],
  "forbidden_actions": ["execute the binary", "modify the binary"],
  "output": {
    "result": "<TARGET>/outputs/strings_categorized.json",
    "raw": "<TARGET>/RAW/strings_raw.txt"
  },
  "output_format": {
    "categories": {
      "urls": ["http://...", "https://..."],
      "file_paths": ["C:\\...", "/etc/..."],
      "crypto_constants": ["AES", "RSA", ...],
      "registry_keys": ["HKLM\\...", ...],
      "suspicious": ["cmd.exe", "powershell", "VirtualAlloc", ...]
    },
    "stats": { "total": 0, "categorized": 0, "uncategorized": 0 }
  }
}
```

### Function inventory from decompiler output

```json
{
  "objective": "Build function inventory from decompiled source",
  "input": "<TARGET>/RAW/decompiled_full.c",
  "allowed_actions": ["parse C source", "extract function boundaries", "count lines", "identify call patterns"],
  "forbidden_actions": ["analyze algorithm logic", "judge security impact", "suggest next steps"],
  "output": {
    "result": "<TARGET>/outputs/function_inventory.json",
    "raw": "<TARGET>/RAW/function_parse_raw.txt"
  },
  "output_format": {
    "total_functions": 0,
    "functions": [
      {
        "name": "sub_401000",
        "address": "0x401000",
        "line_count": 45,
        "calls": ["CreateFileW", "ReadFile", "VirtualAlloc"],
        "tags": ["file_io", "memory_alloc"]
      }
    ]
  }
}
```

### Binary diff

```json
{
  "objective": "Diff two versions of decompiled output, list changes",
  "input": ["<TARGET>/RAW/v1_decompiled.c", "<TARGET>/RAW/v2_decompiled.c"],
  "allowed_actions": ["read both files", "diff by function", "summarize changes"],
  "forbidden_actions": ["judge security impact of changes", "suggest patches"],
  "output": {
    "result": "<TARGET>/outputs/binary_diff.json",
    "raw": "<TARGET>/RAW/diff_raw.txt"
  },
  "output_format": {
    "added_functions": [{"name": "...", "address": "...", "line_count": 0}],
    "removed_functions": [{"name": "...", "address": "..."}],
    "modified_functions": [{"name": "...", "address": "...", "change_summary": "..."}],
    "stats": { "added": 0, "removed": 0, "modified": 0, "unchanged": 0 }
  }
}
```

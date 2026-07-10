# Demo: Rich Brain / Clean Hands in Action

A self-contained demo — no API keys, no external deps, pure Python stdlib.

## Run

```bash
cd demo
python run_demo.py
```

## What happens

1. **Rich brain** creates a workspace with 500 lines of noisy server logs
2. **Rich brain** writes a task packet (the delegation contract)
3. **Rich brain** launches **clean hands** as a separate subprocess
4. **Clean hands** scans all 500 lines, writes raw matches + compact findings to files
5. **Rich brain** reads ONLY the compact JSON result (never the raw output)
6. **Rich brain** makes a decision based on the 4-item digest

The rich brain's context stays completely clean — it never sees the 500 noisy lines.

## Files after a run

```
workspace/
├── packets/
│   └── packet_demo.json          ← delegation contract (rich brain wrote)
├── raw/
│   ├── server_access.log         ← sample input (500 lines of noise)
│   └── grep_raw.txt              ← full grep output (QUARANTINE — rich brain never reads)
└── outputs/
    └── security_findings.json    ← compact result (ONLY thing rich brain reads back)
```

## Replace the executor

`executor.py` is a mock — it uses regex, not an LLM. Replace it with anything that:

1. Reads a task packet (JSON)
2. Does the heavy work
3. Writes raw output to the `raw` path in the packet
4. Writes a compact JSON result to the `result` path in the packet
5. Prints `CLEAN_HANDS_DONE`

The executor can be: another LLM CLI, a Docker container, a cloud function, a shell script.
The pattern works as long as the hand-off is file-mediated and the read-back is compressed.

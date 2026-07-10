#!/usr/bin/env python3
"""
Rich Brain / Clean Hands — Runnable Demo

Two separate processes communicate only through files.
No API keys, no external deps — pure Python stdlib.

Run:  python run_demo.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).parent.resolve()
WORKSPACE = DEMO_DIR / "workspace"
RAW_DIR = WORKSPACE / "raw"
OUTPUTS_DIR = WORKSPACE / "outputs"
PACKETS_DIR = WORKSPACE / "packets"


def banner(step, msg):
    w = 62
    print(f"\n{'=' * w}")
    print(f"  Step {step}: {msg}")
    print(f"{'=' * w}")


def generate_sample_log():
    lines = []
    for i in range(500):
        if i == 42:
            lines.append(
                '2026-07-11 08:42:01 POST /api/v1/admin/login 200 '
                '{"user":"admin","token":"eyJhbGciOiJIUzI1NiJ9.test"}'
            )
        elif i == 137:
            lines.append(
                '2026-07-11 09:15:33 GET /api/internal/debug?dump=env 200 '
                '{"DB_HOST":"10.0.0.5","DB_PASS":"s3cret!"}'
            )
        elif i == 256:
            lines.append(
                '2026-07-11 10:01:44 POST /api/v1/payment/callback 200 '
                '{"sign":"md5(amount+key)","amount":"0.01","order":"ORD-99"}'
            )
        elif i == 389:
            lines.append(
                "2026-07-11 11:30:22 GET /api/v1/user/1/../../../etc/passwd 403"
            )
        else:
            lines.append(
                f"2026-07-11 {8 + i // 60:02d}:{i % 60:02d}:00 "
                f"GET /static/asset_{i}.js 200 {i * 100}B"
            )
    return "\n".join(lines)


def main():
    print("=" * 62)
    print("  Rich Brain / Clean Hands — Live Demo")
    print("  Two brains, one filesystem, zero context pollution.")
    print("=" * 62)

    # ------------------------------------------------------------------
    banner(1, "Rich brain sets up workspace + sample data")
    # ------------------------------------------------------------------

    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    for d in [RAW_DIR, OUTPUTS_DIR, PACKETS_DIR]:
        d.mkdir(parents=True)

    sample_input = RAW_DIR / "server_access.log"
    log_text = generate_sample_log()
    sample_input.write_text(log_text, encoding="utf-8")

    line_count = len(log_text.splitlines())
    print(f"  Workspace : {WORKSPACE}")
    print(f"  Input     : {sample_input.name} ({sample_input.stat().st_size:,} bytes, {line_count} lines)")
    print(f"  RAW/      : quarantine zone — rich brain NEVER reads this")
    print(f"  outputs/  : compact results — ONLY thing rich brain reads")

    # ------------------------------------------------------------------
    banner(2, "Rich brain writes a task packet (delegation contract)")
    # ------------------------------------------------------------------

    packet = {
        "objective": "Extract security-relevant lines from the server log",
        "input": str(sample_input),
        "allowed_actions": ["read", "grep", "extract", "format"],
        "forbidden_actions": [
            "modify input",
            "make network requests",
            "decide strategy",
        ],
        "output": {
            "result": str(OUTPUTS_DIR / "security_findings.json"),
            "raw": str(RAW_DIR / "grep_raw.txt"),
        },
        "output_format": {
            "status": "success|partial|failed",
            "summary": "string",
            "findings": [
                {"line_num": "int", "category": "string", "content": "string"}
            ],
        },
        "stop_conditions": ["all lines processed"],
    }
    packet_path = PACKETS_DIR / "packet_demo.json"
    packet_path.write_text(
        json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Written   : {packet_path.name}")
    print(f"  Objective : {packet['objective']}")
    print(f"  Forbidden : {', '.join(packet['forbidden_actions'])}")

    # ------------------------------------------------------------------
    banner(3, "Rich brain launches clean hands (SEPARATE PROCESS)")
    # ------------------------------------------------------------------

    executor = DEMO_DIR / "executor.py"
    print(f"  Command   : python executor.py {packet_path.name}")
    print(f"  Isolation : subprocess — rich brain context is untouched")
    print(f"  Mode      : Auto foreground (blocking, short task)")
    print()

    proc = subprocess.run(
        [sys.executable, str(executor), str(packet_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if proc.returncode != 0:
        print(f"  FAILED: {proc.stderr.strip()}")
        sys.exit(1)

    marker = "CLEAN_HANDS_DONE" in proc.stdout
    print(f"  Marker    : CLEAN_HANDS_DONE = {marker}")

    # ------------------------------------------------------------------
    banner(4, "Rich brain reads ONLY the compact result")
    # ------------------------------------------------------------------

    result_path = Path(packet["output"]["result"])
    raw_path = Path(packet["output"]["raw"])

    print(f"  Reading   : outputs/{result_path.name} ({result_path.stat().st_size:,} bytes)")
    print(f"  Ignoring  : raw/{raw_path.name} ({raw_path.stat().st_size:,} bytes of noise)")
    print()

    findings = json.loads(result_path.read_text(encoding="utf-8"))
    print(f"  Status    : {findings['status']}")
    print(f"  Summary   : {findings['summary']}")
    print()
    for f in findings["findings"]:
        tag = f["category"].upper()
        print(f"    [{tag:^22}] Line {f['line_num']:>3}: {f['content'][:72]}")

    # ------------------------------------------------------------------
    banner(5, "Rich brain decides (based on digest, not raw noise)")
    # ------------------------------------------------------------------

    categories = sorted(set(f["category"] for f in findings["findings"]))
    print(f"  Categories: {', '.join(categories)}")
    print(f"  Decision  : escalate [{categories[0]}] for immediate review")
    print()
    print(f"  --- Context pollution report ---")
    print(f"  Lines in raw input     : {line_count}")
    print(f"  Lines rich brain saw   : 0")
    print(f"  Bytes rich brain read  : {result_path.stat().st_size:,} (compact JSON)")
    print(f"  Context pollution      : ZERO")
    print()
    print("Done. Inspect workspace/ to see the file hand-off.")


if __name__ == "__main__":
    main()

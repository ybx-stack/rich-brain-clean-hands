#!/usr/bin/env python3
"""
Clean Hands Executor — runs in a SEPARATE process from the rich brain.
Reads a task packet, does the heavy work, writes compact results.
Replace this with any executor: another LLM CLI, a container, a remote API.
"""
import json
import re
import sys
from pathlib import Path


def execute_packet(packet_path: str):
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))

    input_path = Path(packet["input"])
    lines = input_path.read_text(encoding="utf-8").splitlines()

    patterns = {
        "credential_exposure": r"(password|token|secret|DB_PASS|api[_\-]?key)",
        "path_traversal": r"\.\./",
        "payment_anomaly": r"(payment|callback|sign|amount.*0\.01)",
        "admin_access": r"(admin|debug|internal)",
    }

    raw_matches = []
    findings = []

    for i, line in enumerate(lines, 1):
        for category, pattern in patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                raw_matches.append(f"L{i}: [{category}] {line}")
                findings.append(
                    {"line_num": i, "category": category, "content": line.strip()}
                )
                break

    raw_path = Path(packet["output"]["raw"])
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("\n".join(raw_matches), encoding="utf-8")

    result = {
        "status": "success",
        "summary": (
            f"Scanned {len(lines)} lines, found {len(findings)} security-relevant "
            f"entries across {len(set(f['category'] for f in findings))} categories"
        ),
        "findings": findings,
        "paths": {
            "result": str(packet["output"]["result"]),
            "raw": str(packet["output"]["raw"]),
        },
    }

    result_path = Path(packet["output"]["result"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("CLEAN_HANDS_DONE")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <packet.json>", file=sys.stderr)
        sys.exit(1)
    execute_packet(sys.argv[1])

"""Append-only, hash-chained audit log (JSONL)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _entry_hash(prev_hash: str, ts: str, event: str, details: dict) -> str:
    canon = json.dumps({"prev": prev_hash, "ts": ts, "event": event,
                        "details": details}, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()


def append(base: Path, event: str, details: dict) -> dict:
    log = base / "audit.jsonl"
    prev = "GENESIS"
    if log.exists():
        lines = log.read_text().strip().splitlines()
        if lines:
            prev = json.loads(lines[-1])["hash"]
    ts = datetime.now(timezone.utc).isoformat()
    h = _entry_hash(prev, ts, event, details)
    entry = {"ts": ts, "event": event, "details": details,
             "prev_hash": prev, "hash": h}
    with log.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def verify(base: Path) -> tuple[bool, str]:
    log = base / "audit.jsonl"
    if not log.exists():
        return True, "no audit log yet"
    prev = "GENESIS"
    for i, line in enumerate(log.read_text().strip().splitlines()):
        e = json.loads(line)
        if e["prev_hash"] != prev:
            return False, f"chain broken at entry {i}"
        if e["hash"] != _entry_hash(e["prev_hash"], e["ts"], e["event"], e["details"]):
            return False, f"tamper detected at entry {i}"
        prev = e["hash"]
    return True, f"chain intact ({i + 1} entries)"

"""Versioned snapshot storage.

Layout under the data dir:
  snapshots/<source_id>/<utc-ts>_<sha8>.json   canonical snapshot
  snapshots/<source_id>/latest.json            {"file": ..., "sha256": ...}
  assessments/<assessment_id>.json             registered assessments
  outbox/<utc-ts>_<kind>.json                  notifications
  audit.jsonl                                  hash-chained audit log
  last_report.json                             most recent check report
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def data_dir(path: str | None) -> Path:
    d = Path(path) if path else Path.home() / ".regwatch"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256_of_units(units: list[dict]) -> str:
    canon = json.dumps(units, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def save_snapshot(base: Path, source: dict, url: str, units: list[dict]) -> dict:
    """Persist a snapshot; return its metadata. Idempotent on identical text."""
    sha = _sha256_of_units(units)
    sdir = base / "snapshots" / source["id"]
    sdir.mkdir(parents=True, exist_ok=True)
    latest = sdir / "latest.json"
    if latest.exists():
        prev = json.loads(latest.read_text())
        if prev.get("sha256") == sha:
            return {"source": source["id"], "sha256": sha, "file": prev["file"],
                    "fetched_at": prev["fetched_at"], "unchanged": True,
                    "units": len(units)}
    ts = utc_now()
    fname = f"{ts}_{sha[:8]}.json"
    payload = {
        "source": source["id"], "source_name": source["name"], "url": url,
        "fetched_at": ts, "sha256": sha, "units": units,
    }
    (sdir / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    latest.write_text(json.dumps(
        {"file": fname, "sha256": sha, "fetched_at": ts, "units": len(units)}, indent=1))
    return {"source": source["id"], "sha256": sha, "file": fname,
            "fetched_at": ts, "unchanged": False, "units": len(units)}


def load_latest(base: Path, source_id: str) -> dict | None:
    latest = base / "snapshots" / source_id / "latest.json"
    if not latest.exists():
        return None
    meta = json.loads(latest.read_text())
    snap = json.loads((base / "snapshots" / source_id / meta["file"]).read_text())
    return snap


def list_snapshots(base: Path, source_id: str) -> list[dict]:
    sdir = base / "snapshots" / source_id
    if not sdir.exists():
        return []
    out = []
    for f in sorted(sdir.glob("*.json")):
        if f.name == "latest.json":
            continue
        snap = json.loads(f.read_text())
        out.append({"file": f.name, "fetched_at": snap["fetched_at"],
                    "sha256": snap["sha256"], "units": len(snap["units"])})
    return out

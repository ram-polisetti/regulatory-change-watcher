"""Notifications: always write to the local outbox; optionally fan out.

Outbox files are the durable record — a real run writes them, a human or a
downstream job delivers them. Webhook/SMTP delivery is attempted only when
explicitly configured via environment; otherwise it is skipped and logged.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from .snapshot import utc_now


def notify(base: Path, kind: str, subject: str, payload: dict) -> dict:
    """Write an outbox notification; attempt configured deliveries."""
    outbox = base / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    record = {"kind": kind, "subject": subject, "created_at": utc_now(),
              "payload": payload, "deliveries": []}
    fname = f"{record['created_at']}_{kind}.json"
    (outbox / fname).write_text(json.dumps(record, ensure_ascii=False, indent=1))

    webhook = os.environ.get("REGWATCH_WEBHOOK_URL")
    if webhook:
        try:
            req = urllib.request.Request(
                webhook, data=json.dumps(record).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                record["deliveries"].append({"channel": "webhook",
                                             "status": r.status})
        except Exception as e:
            record["deliveries"].append({"channel": "webhook",
                                         "status": f"failed: {e}"})
    else:
        record["deliveries"].append({"channel": "webhook",
                                     "status": "skipped: REGWATCH_WEBHOOK_URL not set"})
    # SMTP is intentionally a documented stub: sending mail needs
    # credentials Charan hasn't provided. The outbox is the real channel.
    record["deliveries"].append({"channel": "smtp",
                                 "status": "stub: not configured (see docs/LIMITATIONS.md)"})
    (outbox / fname).write_text(json.dumps(record, ensure_ascii=False, indent=1))
    return {"file": fname, "deliveries": record["deliveries"]}

"""Assessment registry.

Reads ai-act-checker JSON reports (their ``findings``,
``transparency_obligations`` and ``conformity_checklist`` entries each carry
an ``article`` string), normalizes every cited provision, and stores the
assessment with its instrument + provision tokens so the mapper can test
overlap against changed provisions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .articles import parse_refs


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "unnamed").lower()).strip("-")
    return s or "assessment"


def _collect_article_strings(report: dict) -> list[str]:
    found: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "article" and isinstance(v, str) and v.strip():
                    found.append(v.strip())
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(report)
    # de-dupe, keep order
    seen, out = set(), []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def from_aiact_report(report: dict, assessment_id: str | None = None) -> dict:
    """Build a regwatch assessment record from an ai-act-checker report."""
    cited = _collect_article_strings(report)
    tokens: set[str] = set()
    for s in cited:
        tokens |= parse_refs(s)
    aid = assessment_id or _slug(report.get("system_name", "assessment"))
    return {
        "id": aid,
        "system_name": report.get("system_name", aid),
        "instrument": "eu-ai-act",
        "source": "ai-act-checker",
        "risk_tier": report.get("risk_tier"),
        "act": report.get("act"),
        "knowledge_date": report.get("knowledge_date"),
        "cited_provisions": cited,
        "provision_tokens": sorted(tokens),
        "report_path": None,
    }


def manual_assessment(assessment_id: str, system_name: str, instrument: str,
                      cited_provisions: list[str], notes: str = "") -> dict:
    tokens: set[str] = set()
    for s in cited_provisions:
        tokens |= parse_refs(s)
    return {
        "id": assessment_id,
        "system_name": system_name,
        "instrument": instrument,
        "source": "manual",
        "risk_tier": None,
        "act": None,
        "knowledge_date": None,
        "cited_provisions": cited_provisions,
        "provision_tokens": sorted(tokens),
        "notes": notes,
        "report_path": None,
    }


def register(base: Path, record: dict) -> Path:
    adir = base / "assessments"
    adir.mkdir(parents=True, exist_ok=True)
    path = adir / f"{record['id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1))
    return path


def list_all(base: Path) -> list[dict]:
    adir = base / "assessments"
    if not adir.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(adir.glob("*.json"))]

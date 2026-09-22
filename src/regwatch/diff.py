"""Paragraph-level diffing of snapshot units.

Compares two snapshots unit-by-unit (matched on ``ref``). Within a matched
unit, paragraphs are diffed with difflib; added/removed units are reported
whole. Each change event carries a one-line plain-language summary.
"""
from __future__ import annotations

import difflib
import re

_SENT = re.compile(r"[^.!?]+[.!?]")


def _first_sentence(text: str, limit: int = 160) -> str:
    m = _SENT.search(text or "")
    s = (m.group(0) if m else (text or ""))[:limit].strip()
    return s or "(empty)"


def diff_units(old_units: list[dict], new_units: list[dict]) -> list[dict]:
    old = {u["ref"]: u for u in old_units}
    new = {u["ref"]: u for u in new_units}
    events: list[dict] = []

    for ref in old:
        if ref not in new:
            events.append({
                "ref": ref,
                "change": "removed",
                "title": old[ref].get("title", ref),
                "removed_paragraphs": old[ref]["paragraphs"],
                "added_paragraphs": [],
                "summary": f"{ref} was removed ({len(old[ref]['paragraphs'])} paragraphs).",
            })

    for ref, unit in new.items():
        if ref not in old:
            events.append({
                "ref": ref,
                "change": "added",
                "title": unit.get("title", ref),
                "removed_paragraphs": [],
                "added_paragraphs": unit["paragraphs"],
                "summary": f"{ref} was added ({len(unit['paragraphs'])} paragraphs).",
            })
            continue
        before, after = old[ref]["paragraphs"], unit["paragraphs"]
        if before == after:
            continue
        sm = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
        added, removed = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("insert", "replace"):
                added.extend(after[j1:j2])
            if tag in ("delete", "replace"):
                removed.extend(before[i1:i2])
        sample = _first_sentence(added[0] if added else removed[0])
        events.append({
            "ref": ref,
            "change": "modified",
            "title": unit.get("title", ref),
            "removed_paragraphs": removed,
            "added_paragraphs": added,
            "summary": (
                f"{ref} modified: {len(removed)} paragraph(s) removed, "
                f"{len(added)} added. e.g. {sample}"
            ),
        })
    return events

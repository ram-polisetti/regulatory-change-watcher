"""Changed provisions -> affected assessments.

A change event flags an assessment when:
  1. the event's instrument matches the assessment's instrument, and
  2. any changed provision token overlaps any provision token the
     assessment cited.

For provision-aware instruments (eu-ai-act) the event ref is normalized to
tokens ("Article 9" -> {"article:9"}). For generic instruments the ref is a
page heading; overlap is tested on the raw heading text appearing in the
assessment's cited provisions, plus a blanket match when the assessment
cited the instrument's "general" provisions.
"""
from __future__ import annotations

from .articles import overlaps, ref_label_to_tokens


def _event_tokens(event: dict, provision_aware: bool) -> set[str]:
    if provision_aware:
        return ref_label_to_tokens(event["ref"])
    return set()


def flag_assessments(events_by_source: dict[str, list[dict]],
                     assessments: list[dict],
                     provision_aware: dict[str, bool]) -> list[dict]:
    """events_by_source: {source_id: [change events]}. Returns flag records."""
    flags: list[dict] = []
    for assessment in assessments:
        inst = assessment["instrument"]
        events = events_by_source.get(inst, [])
        if not events:
            continue
        cited = set(assessment.get("provision_tokens", []))
        matched: list[dict] = []
        for ev in events:
            if provision_aware.get(inst):
                changed = _event_tokens(ev, True)
                hits = overlaps(changed, cited)
            else:
                # Generic instrument: refs are page headings. Flag when the
                # changed heading text appears in what the assessment cited,
                # or when the assessment watches the whole instrument
                # (no specific provisions recorded).
                hits = set()
                if not cited:
                    hits = {"general"}
                else:
                    blob = " ".join(assessment.get("cited_provisions", [])).lower()
                    if ev["ref"].lower() in blob:
                        hits = {ev["ref"]}
            if hits:
                matched.append({
                    "changed_ref": ev["ref"],
                    "change": ev["change"],
                    "summary": ev["summary"],
                    "overlapping_provisions": sorted(hits),
                })
        if matched:
            flags.append({
                "assessment_id": assessment["id"],
                "system_name": assessment.get("system_name"),
                "instrument": inst,
                "risk_tier": assessment.get("risk_tier"),
                "reason": (
                    f"{len(matched)} changed provision(s) in {inst} overlap "
                    f"provisions this assessment was decided on"
                ),
                "changes": matched,
            })
    return flags

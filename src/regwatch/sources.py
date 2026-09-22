"""Official source registry.

Every tracked instrument points at an official source. ``kind`` selects the
extraction strategy: ``eulex_articles`` parses EUR-Lex OJ HTML into
article/annex units; ``generic`` extracts headed paragraphs from any page.
"""
from __future__ import annotations

SOURCES = [
    {
        "id": "eu-ai-act",
        "name": "EU Artificial Intelligence Act — Regulation (EU) 2024/1689, OJ English text",
        "jurisdiction": "EU",
        "url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
        "kind": "eulex_articles",
        "provision_aware": True,
        "notes": (
            "Consolidated/consolidating view of the Act as published in the "
            "Official Journal. Delegated and implementing acts amending it "
            "appear as separate instruments on EUR-Lex; when a new one is "
            "published, add it here as its own source entry."
        ),
    },
    {
        "id": "eu-ai-act-implementation",
        "name": "European Commission — Regulatory framework on AI (implementation page)",
        "jurisdiction": "EU",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
        "kind": "generic",
        "provision_aware": False,
        "notes": (
            "Commission landing page for AI Act implementation: guidelines, "
            "implementing/delegating acts, GPAI codes of practice. Changes "
            "here usually signal new secondary legislation worth adding as "
            "a dedicated source."
        ),
    },
    {
        "id": "nist-ai-rmf",
        "name": "NIST AI Risk Management Framework (AI RMF 1.0)",
        "jurisdiction": "US-federal",
        "url": "https://www.nist.gov/itl/ai-risk-management-framework",
        "kind": "generic",
        "provision_aware": False,
        "notes": (
            "NIST's AI RMF program page. The framework itself is versioned; "
            "a 2.0 or profile update would surface here first."
        ),
    },
    {
        "id": "colorado-sb24-205",
        "name": "Colorado SB24-205 — Consumer Protections for Artificial Intelligence",
        "jurisdiction": "US-CO",
        "url": "https://leg.colorado.gov/bills/sb24-205",
        "kind": "generic",
        "provision_aware": False,
        "notes": (
            "First comprehensive US state AI law (signed 2024-05-17; "
            "enforceable 2026-06-30). Official Colorado General Assembly page."
        ),
    },
    {
        "id": "texas-hb149",
        "name": "Texas HB 149 — Texas Responsible AI Governance Act (TRAIGA)",
        "jurisdiction": "US-TX",
        "url": "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=HB149",
        "kind": "generic",
        "provision_aware": False,
        "notes": "Official Texas Legislature Online history page for HB 149 (89R).",
    },
    {
        "id": "california-sb942",
        "name": "California SB 942 — California AI Transparency Act",
        "jurisdiction": "US-CA",
        "url": "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942",
        "kind": "generic",
        "provision_aware": False,
        "notes": (
            "Official California Legislative Information page. Requires "
            "disclosure of AI-generated content by large providers."
        ),
    },
]


def get_source(source_id: str) -> dict:
    for s in SOURCES:
        if s["id"] == source_id:
            return s
    raise KeyError(f"unknown source: {source_id!r}")


def source_ids() -> list[str]:
    return [s["id"] for s in SOURCES]

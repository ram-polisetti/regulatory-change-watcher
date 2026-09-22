"""Provision-reference normalization.

ai-act-checker reports cite provisions as free text, e.g.
  "Article 6(2); Annex III, point 4(a)-(b)"
  "Article 11, Annex IV"
  "Article 50(1)"

``parse_refs`` turns these into normalized tokens:
  "article:6", "annex:III:4", "article:11", "annex:IV", "article:50"

Matching is base-level: a change to "Article 9" matches a citation of
"Article 9(1)" and vice versa — the assessment was made against that
article, so any change to it is potentially material. This deliberately
over-flags rather than under-flags; the human decides materiality.
"""
from __future__ import annotations

import re

_ARTICLE = re.compile(r"\bArticle\s+(\d+)[a-z]?", re.IGNORECASE)
_ANNEX = re.compile(r"\bAnnex(?:es)?\s+([IVXLCDM]+)(?:\s*,?\s*point\s+(\d+))?", re.IGNORECASE)


def parse_refs(text: str) -> set[str]:
    tokens: set[str] = set()
    for m in _ARTICLE.finditer(text or ""):
        tokens.add(f"article:{m.group(1)}")
    for m in _ANNEX.finditer(text or ""):
        if m.group(2):
            tokens.add(f"annex:{m.group(1).upper()}:{m.group(2)}")
        else:
            tokens.add(f"annex:{m.group(1).upper()}")
    return tokens


def ref_label_to_tokens(ref: str) -> set[str]:
    """Normalize a snapshot unit ref ("Article 9", "Annex III") to tokens."""
    return parse_refs(ref)


def overlaps(changed_tokens: set[str], cited_tokens: set[str]) -> set[str]:
    """Return the non-empty intersection, with annex-point matching its annex.

    A change to "Annex III" (whole-annex) overlaps a citation of
    "Annex III, point 4"; a change to "annex:III:4" overlaps a citation of
    "annex:III" too — either direction is a shared provision family.
    """
    hits: set[str] = set()
    for c in changed_tokens:
        for s in cited_tokens:
            if c == s:
                hits.add(c)
            elif c.startswith(s + ":") or s.startswith(c + ":"):
                hits.add(f"{s}~{c}")
    return hits

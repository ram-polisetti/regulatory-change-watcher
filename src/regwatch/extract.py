"""HTML -> canonical text units. Stdlib only.

Two strategies:
- ``extract_eulex_articles``: EUR-Lex OJ HTML. Articles live in
  ``<div class="eli-subdivision" id="art_N">`` with an ``oj-ti-art`` header
  ("Article N") and ``oj-sti-art`` title; annexes in ``id="anx_X"``.
  Output units: {"ref": "Article 9", "title": ..., "paragraphs": [...]}.
- ``extract_generic``: any page. Strips scripts/styles/nav, splits the body
  into paragraphs, attributes each paragraph to the nearest preceding
  heading (h1-h6). Output units: {"ref": heading or "general", ...}.
"""
from __future__ import annotations

import html as htmlmod
import re

_WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    text = htmlmod.unescape(text)
    text = text.replace("\xa0", " ")
    return _WS.sub(" ", text).strip()


def _strip_tags(fragment: str) -> str:
    fragment = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
    return _clean(fragment)


def extract_eulex_articles(html: str) -> list[dict]:
    """Parse EUR-Lex OJ HTML into article + annex units."""
    units: list[dict] = []

    # Articles: <div class="eli-subdivision" id="art_N"> ... </div> blocks.
    # We slice from each art_N div to the next art_/anx_ div boundary.
    marks = [
        (m.start(), "article", m.group(1))
        for m in re.finditer(r'<div class="eli-subdivision" id="art_(\d+)"', html)
    ]
    anx_marks = [
        (m.start(), "annex", m.group(1))
        for m in re.finditer(r'<div[^>]*id="anx_([IVX]+)"', html)
    ]
    marks = sorted(marks + anx_marks)
    for i, (start, kind, num) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(html)
        block = html[start:end]
        if kind == "article":
            ref = f"Article {num}"
            t = re.search(r'<p[^>]*class="oj-ti-art"[^>]*>(.*?)</p>', block, re.S)
            title_m = re.search(r'<p[^>]*class="oj-sti-art"[^>]*>(.*?)</p>', block, re.S)
            ti_text = _clean(t.group(1)) if t else ref
            sti_text = _clean(title_m.group(1)) if title_m else ""
            title = f"{ti_text} — {sti_text}" if sti_text else ti_text
            paras = [
                _clean(p)
                for p in re.findall(r"<p[^>]*>(.*?)</p>", block, re.S)
                if _clean(p) and _clean(p) not in (ti_text, sti_text)
                and not re.fullmatch(r"Article\s+\d+", _clean(p))
            ]
        else:
            ref = f"Annex {num}"
            title = ref
            paras = [_clean(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", block, re.S) if _clean(p)]
        # drop pure heading echo paragraphs
        paras = [p for p in paras if p != title and len(p) > 1]
        if paras:
            units.append({"ref": ref, "title": title, "paragraphs": paras})
    return units


_HEADING = re.compile(r"(?is)<h([1-6])[^>]*>(.*?)</h\1>")


def extract_generic(html: str) -> list[dict]:
    """Extract headed paragraph units from an arbitrary page."""
    # Split body into segments at headings; attribute paragraphs to headings.
    segments: list[tuple[str, str]] = []  # (heading, html)
    pos = 0
    current = "general"
    for m in _HEADING.finditer(html):
        segments.append((current, html[pos : m.start()]))
        current = _strip_tags(m.group(2))[:120] or "general"
        pos = m.end()
    segments.append((current, html[pos:]))

    by_ref: dict[str, list[str]] = {}
    for heading, frag in segments:
        for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", frag):
            text = _strip_tags(p)
            if len(text) >= 40:  # skip nav crumbs / boilerplate stubs
                by_ref.setdefault(heading or "general", []).append(text)
    units = [
        {"ref": ref, "title": ref, "paragraphs": paras}
        for ref, paras in by_ref.items()
        if paras
    ]
    if not units:
        # Fallback: whole body as one unit so a fetch is never silently empty.
        text = _strip_tags(html)
        if len(text) >= 40:
            units = [{"ref": "general", "title": "general",
                      "paragraphs": [text[i : i + 2000] for i in range(0, len(text), 2000)]}]
    return units


def extract(source_kind: str, html: str) -> list[dict]:
    if source_kind == "eulex_articles":
        return extract_eulex_articles(html)
    return extract_generic(html)

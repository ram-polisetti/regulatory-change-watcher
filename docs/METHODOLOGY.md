# Methodology

## Source model

Each tracked instrument is an official publication with a stable URL
(`src/regwatch/sources.py`). Two extraction strategies:

- **`eulex_articles`** (EU AI Act): EUR-Lex OJ HTML marks every article as
  `<div class="eli-subdivision" id="art_N">` with `oj-ti-art` ("Article N")
  and `oj-sti-art` (title) headers, and annexes as `id="anx_X"`. Extraction
  slices the document at these markers, so each snapshot unit is exactly one
  article or annex with its paragraphs in order. Verified against the live
  OJ text on 2026-09-22 (113 articles, 8 annexes parsed).
- **`generic`** (everything else): scripts/styles/nav stripped, body split
  into paragraphs, each attributed to its nearest preceding heading
  (`h1`–`h6`). Paragraphs under 40 chars are dropped as chrome. If nothing
  survives, the whole body becomes one `general` unit so a fetch is never
  silently empty.

Snapshots are canonical JSON (`source`, `url`, `fetched_at`, `units`);
identity is the SHA-256 of the canonical units, so re-crawling unchanged
text stores nothing new.

## Diffing

Units match on `ref`. Added/removed units are reported whole. For matched
units, `difflib.SequenceMatcher` (autojunk off) runs over the paragraph
lists; opcodes yield added/removed paragraph sets. The summary quotes the
first changed sentence. This is paragraph-granular, not word-granular, by
design: legal edits are paragraph-scoped and the summary must stay readable.

## Provision normalization

ai-act-checker citations are free text. Normalization (`articles.py`):

- `Article 6(2)` → `article:6`; `Article 11, Annex IV` → `article:11`, `annex:IV`;
  `Annex III, point 4(a)-(b)` → `annex:III:4`.
- Matching is base-level and bidirectional: a change to `article:9`
  overlaps a citation of `article:9(1)`; a change to `annex:III` overlaps a
  citation of `annex:III:4` and vice versa. Rationale: the assessment was
  decided against that provision family; any edit to it is potentially
  material. The tool deliberately over-flags — materiality is a human call.

## Flagging

`mapper.flag_assessments` takes `{source_id: [change events]}` and the
registered assessments. A flag requires instrument match **and** provision
overlap. For generic instruments (no article structure), an assessment with
no recorded provisions is treated as watching the whole instrument; one with
cited headings matches on heading-text overlap.

## Notifications and audit

Flags produce one JSON notification in `outbox/` per run (durable even if
delivery is unconfigured). `REGWATCH_WEBHOOK_URL` enables real webhook
POST; SMTP remains a stub (see LIMITATIONS). Every crawl/diff/flag/notify
event is appended to `audit.jsonl` with `prev_hash` chaining; `regwatch
audit` recomputes the chain and reports tampering.

## Exit codes

`regwatch check`: `0` no flags, `1` one or more assessments flagged,
`2` operational errors (e.g. all crawls failed).

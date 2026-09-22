# Changelog

## 0.1.0 — 2026-09-22
- Initial release.
- Six official sources tracked: EU AI Act (EUR-Lex OJ, article/annex-aware),
  Commission AI Act implementation page, NIST AI RMF, Colorado SB24-205,
  Texas HB 149, California SB 942.
- Crawl → snapshot (content-hashed, idempotent) → paragraph-level diff →
  provision-overlap flagging against ai-act-checker assessments → outbox
  notifications → hash-chained audit log.
- CLI: `sources`, `crawl`, `diff`, `check` (exit 0/1/2), `assessments add/list`,
  `report`, `audit`.
- 21/21 tests pass (stdlib unittest, fixture-backed). Live demo: real NIST
  crawl + simulated Article 9 amendment flags exactly the citing assessment.

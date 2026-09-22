# regulatory-change-watcher

Watches official AI-regulation sources and tells your governance stack when a
conformity assessment has gone stale.

**The problem it solves:** an EU AI Act conformity check is a snapshot. The
day a delegated act amends Article 9, every high-risk assessment decided on
Article 9 is quietly out of date. This service crawls the official sources,
diffs versioned snapshots paragraph-by-paragraph, and flags exactly the
assessments whose cited provisions changed — with the changed provision
linked to the affected assessment.

Built by [Ram Charan Satya Sai Teja Polisetti](https://github.com/ram-polisetti)
— an operator-built governance tool, designed to sit next to
[`ai-act-checker`](https://github.com/ram-polisetti/ai-act-checker).

## Quickstart

```bash
pip install -e .
regwatch sources                      # list tracked official sources
regwatch crawl                        # fetch all sources, store snapshots
regwatch assessments add report.json  # register an ai-act-checker report
regwatch check                        # crawl + diff + flag + notify (JSON to stdout)
# exit 0 = no flags, 1 = assessments need re-assessment, 2 = errors
regwatch report                       # print the last check report
regwatch audit                        # verify the audit-log hash chain
```

State lives in `~/.regwatch` (override with `--data-dir`).

## How it works

1. **Crawl** — fetches each tracked source (polite UA, 30s timeout), extracts
   canonical text units, stores a content-hashed snapshot. EUR-Lex OJ pages
   are parsed into article/annex units (`Article 9`, `Annex III`); other pages
   into headed paragraph units. A byte-identical re-fetch stores nothing new.
2. **Diff** — compares the two latest snapshots unit-by-unit; within a unit,
   paragraphs are diffed with `difflib`. Each change event names the
   provision and carries a one-line plain-language summary.
3. **Flag** — assessments registered from `ai-act-checker` JSON reports have
   every cited provision normalized (`"Article 6(2); Annex III, point 4(a)-(b)"`
   → `article:6`, `annex:III:4`). A change flags an assessment when the
   changed provision overlaps anything the assessment was decided on.
   Matching is deliberately base-level (any change to Article 9 flags an
   assessment citing Article 9(1)) — it over-flags; a human judges materiality.
4. **Notify** — every flag run writes a JSON notification to the local outbox
   (`REGWATCH_WEBHOOK_URL` enables real webhook delivery; SMTP is a documented stub).
5. **Audit** — every crawl, diff, flag, and notification is appended to a
   SHA-256 hash-chained JSONL log; `regwatch audit` detects tampering.

## Tracked sources (all official)

| ID | Instrument | Source |
|---|---|---|
| `eu-ai-act` | EU AI Act, Reg. 2024/1689 (OJ EN text) | eur-lex.europa.eu |
| `eu-ai-act-implementation` | Commission AI Act implementation page | digital-strategy.ec.europa.eu |
| `nist-ai-rmf` | NIST AI Risk Management Framework | nist.gov |
| `colorado-sb24-205` | Colorado AI Act (SB24-205) | leg.colorado.gov |
| `texas-hb149` | Texas Responsible AI Governance Act (HB 149) | capitol.texas.gov |
| `california-sb942` | California AI Transparency Act (SB 942) | leginfo.legislature.ca.gov |

Full URLs and notes: `docs/SOURCES.md`. Methodology: `docs/METHODOLOGY.md`.
Limitations (read these): `docs/LIMITATIONS.md`.

## Demo

```bash
python3 examples/demo.py
```

Stage 1 performs a **live** crawl of the NIST AI RMF page. Stage 2 runs the
full pipeline against a simulated Article 9 amendment (fixture captured from
EUR-Lex's real HTML structure): the high-risk CV-ranker assessment is flagged,
the Article-50-only chatbot and the provision-free spam filter are not.

## Tests

```bash
python3 -m unittest discover -s tests
```

21 tests, fixture-backed (no network needed).

## License

Apache-2.0. See `LICENSE`.

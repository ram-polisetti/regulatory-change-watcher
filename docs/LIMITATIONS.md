# Limitations

Read before relying on this tool for real compliance work.

1. **It watches text, not law.** A detected change means the source page's
   text changed — that can be a substantive amendment, a corrigendum, a
   page redesign, or CMS noise. The generic extractor drops short
   paragraphs and attributes text to headings heuristically; a site
   redesign can produce phantom "changes". Treat every diff as a lead,
   not a legal conclusion.
2. **Over-flagging is intentional.** Any edit to a cited provision family
   flags the assessment. Most flags will be immaterial on human review.
   That is the design trade-off; the alternative (silent staleness) is worse.
3. **EUR-Lex "consolidated" nuance.** The tracked OJ text is the Act as
   published; consolidated versions incorporating amendments appear under
   separate CELEX numbers. When a real amending act lands, add it as its
   own source rather than assuming this URL absorbs it.
4. **Provision-awareness is EU-only.** NIST and US-state instruments are
   diffed at heading/paragraph level; assessments against them are matched
   coarsely (whole-instrument or heading text). Finer mapping needs
   per-instrument section parsing, not yet built.
5. **SMTP is a stub.** Outbox JSON files are the durable notification
   channel. Webhook delivery works via `REGWATCH_WEBHOOK_URL`; email
   needs credentials that have not been provided.
6. **Demo stage 2 is simulated.** The end-to-end flagging demo uses a
   fixture with EUR-Lex's real HTML structure, not a live amendment —
   because no real amendment occurred during the build. Stage 1 (NIST
   crawl) is live.
7. **Politeness.** One polite request per source per run, 30s timeout,
   failures audit-logged without killing the run. Do not point this at a
   schedule tighter than daily against official sites.
8. **Not legal advice.** This is an operator's tripwire, not counsel.
   Re-assessment decisions belong to a qualified human.

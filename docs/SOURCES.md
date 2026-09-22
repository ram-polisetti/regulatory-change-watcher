# Sources

All tracked instruments point at official publications. Verified reachable
2026-09-22.

| ID | Instrument | Official URL | Jurisdiction |
|---|---|---|---|
| `eu-ai-act` | EU Artificial Intelligence Act — Regulation (EU) 2024/1689, OJ English text | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | EU |
| `eu-ai-act-implementation` | European Commission — Regulatory framework on AI (guidelines, implementing/delegating acts, GPAI codes) | https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai | EU |
| `nist-ai-rmf` | NIST AI Risk Management Framework (AI RMF 1.0) program page | https://www.nist.gov/itl/ai-risk-management-framework | US federal |
| `colorado-sb24-205` | Colorado SB24-205 — Consumer Protections for Artificial Intelligence (signed 2024-05-17; enforceable 2026-06-30) | https://leg.colorado.gov/bills/sb24-205 | US-CO |
| `texas-hb149` | Texas HB 149 — Texas Responsible AI Governance Act (89R) | https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=HB149 | US-TX |
| `california-sb942` | California SB 942 — California AI Transparency Act | https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942 | US-CA |

## How to add a source

Append an entry to `SOURCES` in `src/regwatch/sources.py` with `id`,
`name`, `jurisdiction`, `url`, `kind` (`eulex_articles` for EUR-Lex OJ
texts, `generic` otherwise), `provision_aware`, and a `notes` field
documenting what the page is. Delegated/implementing acts amending the AI
Act should be added as their own instruments when published — the
Commission implementation page (`eu-ai-act-implementation`) is the
tripwire that tells you one exists.

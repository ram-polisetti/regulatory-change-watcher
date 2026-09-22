#!/usr/bin/env python3
"""End-to-end demo of the regulatory change watcher.

Stage 1 (live): crawl one real source (NIST AI RMF page) to prove the
    fetcher works against official sources. Tolerates network failure.
Stage 2 (simulated, honestly labeled): seed a baseline eu-ai-act snapshot
    from a fixture captured from EUR-Lex's real HTML structure, register
    three real ai-act-checker sample assessments, then apply a simulated
    amendment to Article 9 and show the watcher flagging exactly the
    affected assessments.
Stage 3: verify the audit-log hash chain and show the outbox notification.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
FIX = ROOT / "tests" / "fixtures"

from regwatch import (  # noqa: E402
    assessments, audit, diff, extract, fetch, mapper, notify, snapshot, sources,
)


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="regwatch-demo-"))
    print(f"demo data dir: {base}\n")

    # ---- Stage 1: live crawl of a real source ----
    print("== Stage 1: live crawl (https://www.nist.gov/itl/ai-risk-management-framework)")
    nist = sources.get_source("nist-ai-rmf")
    try:
        status, url, body = fetch.fetch(nist["url"])
        units = extract.extract(nist["kind"], body.decode("utf-8", errors="replace"))
        meta = snapshot.save_snapshot(base, nist, url, units)
        audit.append(base, "crawl", {"source": nist["id"], "http_status": status,
                                     "units": meta["units"]})
        print(f"   OK: HTTP {status}, {meta['units']} text units snapshotted "
              f"(sha {meta['sha256'][:12]})")
    except Exception as e:  # network may be unavailable; demo continues
        print(f"   SKIPPED (network): {e}")

    # ---- Stage 2: simulated amendment, real pipeline ----
    print("\n== Stage 2: simulated EU AI Act amendment -> assessment flagging")
    eu = sources.get_source("eu-ai-act")
    v1 = extract.extract("eulex_articles", (FIX / "eulex_sample.html").read_text())
    m1 = snapshot.save_snapshot(base, eu, "SIMULATED:fixture-v1 (EUR-Lex structure)", v1)
    audit.append(base, "crawl", {"source": "eu-ai-act", "simulated": True,
                                 "sha256": m1["sha256"][:12]})
    print(f"   baseline snapshot: {m1['units']} units (Article 9/10/50, Annex III)")

    for name in ["hire-screen.report.json", "support-chatbot.report.json",
                 "spam-filter.report.json"]:
        report = json.loads((ROOT / "examples" / name).read_text())
        rec = assessments.from_aiact_report(report)
        assessments.register(base, rec)
        print(f"   registered assessment {rec['id']:28} "
              f"tier={rec['risk_tier']:12} provisions={len(rec['provision_tokens'])}")

    v2 = extract.extract("eulex_articles", (FIX / "eulex_sample_v2.html").read_text())
    m2 = snapshot.save_snapshot(base, eu, "SIMULATED:fixture-v2 (Article 9 amended)", v2)
    print(f"   amended snapshot stored (sha {m2['sha256'][:12]})")

    old = json.loads((base / "snapshots/eu-ai-act" / m1["file"]).read_text())
    new = json.loads((base / "snapshots/eu-ai-act" / m2["file"]).read_text())
    events = diff.diff_units(old["units"], new["units"])
    print(f"   diff: {len(events)} change event(s)")
    for ev in events:
        print(f"     - {ev['summary']}")
    audit.append(base, "diff", {"source": "eu-ai-act", "changes": len(events)})

    flags = mapper.flag_assessments(
        {"eu-ai-act": events}, assessments.list_all(base), {"eu-ai-act": True})
    audit.append(base, "flag", {"flags": len(flags),
                                "assessments": [f["assessment_id"] for f in flags]})
    print(f"   flags: {len(flags)} assessment(s) need re-assessment")
    for f in flags:
        changed = ", ".join(c["changed_ref"] for c in f["changes"])
        print(f"     - {f['assessment_id']} ({f['system_name']}): {f['reason']} [{changed}]")

    flagged_ids = {f["assessment_id"] for f in flags}
    assert flagged_ids == {"hirescreen-cv-ranker"}, f"unexpected flags: {flagged_ids}"
    print("   ASSERTION OK: only the CV-ranker assessment (cites Article 9) flagged;")
    print("                 chatbot (Article 50 only) and spam filter (no provisions) untouched.")

    if flags:
        n = notify.notify(base, "reassessment-needed",
                          f"{len(flags)} assessment(s) need re-assessment",
                          {"flags": flags})
        audit.append(base, "notify", {"file": n["file"]})
        print(f"   outbox notification written: {n['file']}")

    # ---- Stage 3: audit chain ----
    print("\n== Stage 3: audit log verification")
    ok, msg = audit.verify(base)
    print(f"   {msg}")
    assert ok, "audit chain broken"

    report = {
        "demo": "regulatory-change-watcher end-to-end",
        "stage1_live_crawl": "attempted (see above)",
        "stage2_simulated_amendment": "Article 9 modified",
        "flags": flags,
        "audit": msg,
    }
    (base / "demo-report.json").write_text(json.dumps(report, indent=1))
    print(f"\nDEMO COMPLETE. State kept at {base} for inspection.")
    print("Exit code semantics: 1 = flags raised (as designed).")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())

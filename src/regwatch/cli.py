"""regwatch CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from . import assessments as assess_mod
from . import audit as audit_mod
from . import diff as diff_mod
from . import extract as extract_mod
from . import fetch as fetch_mod
from . import mapper as mapper_mod
from . import notify as notify_mod
from . import snapshot as snap_mod
from . import sources as sources_mod


def _base(args) -> Path:
    return snap_mod.data_dir(args.data_dir)


def cmd_sources(args):
    for s in sources_mod.SOURCES:
        print(f"{s['id']:28} {s['jurisdiction']:10} {s['url']}")
    return 0


def cmd_crawl(args):
    base = _base(args)
    ids = [args.source] if args.source else sources_mod.source_ids()
    results = []
    for sid in ids:
        src = sources_mod.get_source(sid)
        try:
            status, final_url, body = fetch_mod.fetch(src["url"])
            html = body.decode("utf-8", errors="replace")
            units = extract_mod.extract(src["kind"], html)
            if not units:
                raise fetch_mod.FetchError("extraction produced no units")
            meta = snap_mod.save_snapshot(base, src, final_url, units)
            audit_mod.append(base, "crawl", {
                "source": sid, "http_status": status, "url": final_url,
                "sha256": meta["sha256"][:12], "units": meta["units"],
                "unchanged": meta["unchanged"]})
            results.append({"source": sid, "ok": True, **meta})
            print(f"[crawl] {sid}: {meta['units']} units "
                  f"{'(unchanged)' if meta['unchanged'] else '(new snapshot)'}")
        except fetch_mod.FetchError as e:
            audit_mod.append(base, "crawl_failed", {"source": sid, "error": str(e)})
            results.append({"source": sid, "ok": False, "error": str(e)})
            print(f"[crawl] {sid}: FAILED — {e}", file=sys.stderr)
        except Exception as e:  # never let one source kill the run
            audit_mod.append(base, "crawl_failed", {"source": sid, "error": str(e)})
            results.append({"source": sid, "ok": False, "error": str(e)})
            print(f"[crawl] {sid}: FAILED — {e}", file=sys.stderr)
    return 0


def cmd_diff(args):
    base = _base(args)
    snaps = snap_mod.list_snapshots(base, args.source)
    if len(snaps) < 2:
        print(f"need 2+ snapshots for {args.source} "
              f"(have {len(snaps)}); run `crawl` twice", file=sys.stderr)
        return 2
    old = json.loads((base / "snapshots" / args.source / snaps[-2]["file"]).read_text())
    new = json.loads((base / "snapshots" / args.source / snaps[-1]["file"]).read_text())
    events = diff_mod.diff_units(old["units"], new["units"])
    audit_mod.append(base, "diff", {"source": args.source,
                                    "old": old["sha256"][:12],
                                    "new": new["sha256"][:12],
                                    "changes": len(events)})
    if not events:
        print("no changes")
    for ev in events:
        print(f"- [{ev['change']}] {ev['ref']}: {ev['summary']}")
    return 0


def cmd_check(args):
    """Full run: crawl everything, diff, flag assessments, notify, report."""
    base = _base(args)
    errors = []
    # 1. crawl
    crawl_summaries = []
    for src in sources_mod.SOURCES:
        sid = src["id"]
        try:
            status, final_url, body = fetch_mod.fetch(src["url"])
            units = extract_mod.extract(src["kind"], body.decode("utf-8", errors="replace"))
            if not units:
                raise fetch_mod.FetchError("extraction produced no units")
            meta = snap_mod.save_snapshot(base, src, final_url, units)
            audit_mod.append(base, "crawl", {"source": sid, "http_status": status,
                                             "sha256": meta["sha256"][:12],
                                             "units": meta["units"],
                                             "unchanged": meta["unchanged"]})
            crawl_summaries.append({"source": sid, "ok": True,
                                    "unchanged": meta["unchanged"]})
        except Exception as e:
            audit_mod.append(base, "crawl_failed", {"source": sid, "error": str(e)})
            crawl_summaries.append({"source": sid, "ok": False, "error": str(e)})
            errors.append(sid)

    # 2. diff each source with 2+ snapshots
    events_by_source: dict[str, list[dict]] = {}
    for src in sources_mod.SOURCES:
        sid = src["id"]
        snaps = snap_mod.list_snapshots(base, sid)
        if len(snaps) < 2:
            continue
        old = json.loads((base / "snapshots" / sid / snaps[-2]["file"]).read_text())
        new = json.loads((base / "snapshots" / sid / snaps[-1]["file"]).read_text())
        events = diff_mod.diff_units(old["units"], new["units"])
        if events:
            events_by_source[sid] = events
        audit_mod.append(base, "diff", {"source": sid, "changes": len(events)})

    # 3. flag assessments
    provision_aware = {s["id"]: s["provision_aware"] for s in sources_mod.SOURCES}
    all_assess = assess_mod.list_all(base)
    flags = mapper_mod.flag_assessments(events_by_source, all_assess, provision_aware)
    audit_mod.append(base, "flag", {"flags": len(flags),
                                    "assessments": [f["assessment_id"] for f in flags]})

    # 4. notify
    notifications = []
    if flags:
        n = notify_mod.notify(
            base, "reassessment-needed",
            f"{len(flags)} assessment(s) need re-assessment",
            {"flags": flags,
             "changes": {k: [e["summary"] for e in v]
                         for k, v in events_by_source.items()}})
        notifications.append(n)
        audit_mod.append(base, "notify", {"kind": "reassessment-needed",
                                          "file": n["file"]})

    report = {
        "checked_at": snap_mod.utc_now(),
        "crawl": crawl_summaries,
        "changes": {k: v for k, v in events_by_source.items()},
        "flags": flags,
        "notifications": notifications,
    }
    (base / "last_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if errors and not flags:
        return 2
    return 1 if flags else 0


def cmd_assessments(args):
    base = _base(args)
    if args.action == "add":
        report = json.loads(Path(args.report).read_text())
        rec = assess_mod.from_aiact_report(report, args.id)
        rec["report_path"] = str(Path(args.report).resolve())
        path = assess_mod.register(base, rec)
        audit_mod.append(base, "assessment_registered",
                         {"id": rec["id"], "instrument": rec["instrument"],
                          "provisions": len(rec["provision_tokens"])})
        print(f"registered {rec['id']} ({len(rec['provision_tokens'])} provision tokens) -> {path}")
    elif args.action == "list":
        for a in assess_mod.list_all(base):
            print(f"{a['id']:30} {a['instrument']:12} "
                  f"{len(a.get('provision_tokens', [])):3} provisions  {a.get('system_name')}")
    return 0


def cmd_report(args):
    base = _base(args)
    p = base / "last_report.json"
    if not p.exists():
        print("no check has run yet", file=sys.stderr)
        return 2
    print(p.read_text())
    return 0


def cmd_audit(args):
    base = _base(args)
    ok, msg = audit_mod.verify(base)
    print(msg)
    return 0 if ok else 2


def main(argv=None):
    ap = argparse.ArgumentParser(prog="regwatch",
                                 description="Watch AI regulations; flag stale conformity assessments.")
    ap.add_argument("--version", action="version", version=f"regwatch {__version__}")
    ap.add_argument("--data-dir", default=None, help="state directory (default ~/.regwatch)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="list tracked official sources")

    c = sub.add_parser("crawl", help="fetch sources and store snapshots")
    c.add_argument("--source", default=None)

    d = sub.add_parser("diff", help="diff the two latest snapshots of a source")
    d.add_argument("--source", required=True)

    sub.add_parser("check", help="crawl + diff + flag + notify; exit 1 if flags raised")

    a = sub.add_parser("assessments", help="manage watched assessments")
    a.add_argument("action", choices=["add", "list"])
    a.add_argument("report", nargs="?", help="ai-act-checker report JSON (for add)")
    a.add_argument("--id", default=None)

    sub.add_parser("report", help="print the last check report")
    sub.add_parser("audit", help="verify the audit-log hash chain")

    args = ap.parse_args(argv)
    return {
        "sources": cmd_sources, "crawl": cmd_crawl, "diff": cmd_diff,
        "check": cmd_check, "assessments": cmd_assessments,
        "report": cmd_report, "audit": cmd_audit,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

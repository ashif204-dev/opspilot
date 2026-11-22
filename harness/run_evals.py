#!/usr/bin/env python3
"""OpsPilot eval harness.

Calls the eval webhook of every bot (one at a time, because the evals append
to the same Google Sheet), collects each bot's summary, prints a pass-rate
table, writes results/latest.json and exits non-zero if any bot is below the
pass threshold. Standard library only.

Usage:
  export N8N_BASE_URL=https://your-instance.app.n8n.cloud
  python harness/run_evals.py                 # all bots
  python harness/run_evals.py --bot ops hr    # selected bots
  python harness/run_evals.py --threshold 0.9
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# bot key -> (display name, production webhook path of its eval workflow)
BOTS = {
    "knowledge": ("Knowledge Bot", "ai-ops-eval-run"),
    "ops": ("Ops Coordinator", "opspilot-eval-ops"),
    "policy": ("Policy Brain", "opspilot-eval-policy"),
    "data": ("Data Analyst", "opspilot-eval-data"),
    "hr": ("HR Resume Scoring", "opspilot-eval-hr"),
    "guardrails": ("Shared Guardrails", "opspilot-eval-guardrails"),
}


def call_eval(base_url, path, timeout):
    url = base_url.rstrip("/") + "/webhook/" + path
    req = urllib.request.Request(
        url, data=b"{}", method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    # the eval workflows return their Summary node: an object or a one-item list
    return body[0] if isinstance(body, list) and body else body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bot", nargs="*", choices=sorted(BOTS), help="bots to run (default: all)")
    ap.add_argument("--threshold", type=float, default=0.9, help="minimum pass rate per bot (default 0.9)")
    ap.add_argument("--timeout", type=int, default=300, help="seconds to wait per bot")
    ap.add_argument("--out", default="results/latest.json")
    args = ap.parse_args()

    base_url = os.environ.get("N8N_BASE_URL")
    if not base_url:
        sys.exit("Set N8N_BASE_URL, e.g. https://your-instance.app.n8n.cloud")

    results, failed_any = [], False
    for key in args.bot or list(BOTS):
        name, path = BOTS[key]
        started = time.time()
        try:
            summary = call_eval(base_url, path, args.timeout)
            total = int(summary.get("total", 0))
            passed = int(summary.get("passed", 0))
            rate = passed / total if total else 0.0
            row = {"bot": name, "total": total, "passed": passed, "pass_rate": round(rate, 3),
                   "failures": summary.get("failures", []), "seconds": round(time.time() - started, 1)}
        except (urllib.error.URLError, ValueError, TimeoutError) as exc:
            row = {"bot": name, "total": 0, "passed": 0, "pass_rate": 0.0,
                   "failures": [f"harness error: {exc}"], "seconds": round(time.time() - started, 1)}
        if row["pass_rate"] < args.threshold:
            failed_any = True
        results.append(row)

    print(f"{'Bot':<22}{'Passed':>8}{'Total':>7}{'Rate':>8}{'Time':>8}")
    for r in results:
        print(f"{r['bot']:<22}{r['passed']:>8}{r['total']:>7}{r['pass_rate']:>8.0%}{r['seconds']:>7}s")
        for f in r["failures"]:
            print(f"    FAIL {f}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"run_at": datetime.now(timezone.utc).isoformat(), "threshold": args.threshold,
                   "results": results}, fh, indent=2)
    sys.exit(1 if failed_any else 0)


if __name__ == "__main__":
    main()

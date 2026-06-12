"""
app.py -- Phase Z status dashboard (READ-ONLY, local Flask app)
================================================================
Local web view of the orchestrator's Blob status files. Shows what is (or
was) running, per-phase progress, durations, notes (incl. the runner's
facit-verification text), errors/hints, and output locations -- by reading
the SAME status contract the runners write. Nothing is invented client-side;
the page renders only what the status file contains.

STRICTLY READ-ONLY by construction: this app imports ONLY read_status and
list_runs from blob.py. It cannot write status, upload outputs, start or
deallocate the VM, or trigger runs. Controls come later (NEXT_SESSION);
this version is the safe first layer.

Pattern: ProvetDiscount (Flask + status polling) applied to Phase Z.
Reuses the proven Blob layer (blob.py, account-key mode) -- no duplicated
Azure code. Same sys.path bootstrap and auth default as the runners, so it
behaves identically to run_site_model.py regarding credentials.

Prerequisites (one-time):
    py -3.11 -m pip install flask          (azure libs already installed)
    az login --scope https://management.core.windows.net//.default
    (account-key mode reads the storage key via az -- LB.46 subscription
     handling is inside blob.py)

Run:
    py -3.11 orchestration\\webapp\\app.py            (serves http://127.0.0.1:5000)
    py -3.11 orchestration\\webapp\\app.py --check    (verify Blob reachable, list runs, exit)
    py -3.11 orchestration\\webapp\\app.py --port 5050

Notes:
- First request is slow (~3-5 s): blob.py lazily fetches the account key via
  az CLI on first client creation. Subsequent requests are fast, and the key
  lives only in process memory (documented ABAC debt -- see blob.py header).
- Binds 127.0.0.1 only: this is Jens's local view. Colleague-facing hosting
  is a later step (requires a reachable host -- see FUTURE_DEVELOPMENT).

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Author: Claude advisor, Phase Z session 2026-06-12.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Same bootstrap as the runners: webapp/ is an entry point; shared/ and
# infrastructure/ are sibling layers under orchestration/.
ORCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORCH / "shared"))
sys.path.insert(0, str(ORCH / "infrastructure"))

# Documented debt: AAD data role is ABAC-blocked -> account-key mode until
# the role exists. Must be set BEFORE importing blob (it reads env at import).
os.environ.setdefault("PRICINGMODEL_AUTH", "key")

from flask import Flask, jsonify, render_template  # noqa: E402
from azure.core.exceptions import ResourceNotFoundError  # noqa: E402
from blob import read_status, list_runs  # noqa: E402  (READ-ONLY imports, by design)
from story_config import STORY, BAGE_SV  # noqa: E402  (statisk facit-referens + texter)

log = logging.getLogger("webapp")
app = Flask(__name__)


@app.get("/")
def index():
    return render_template("dashboard.html")


@app.get("/api/story")
def api_story():
    """Statisk facit-referens + svenska berattartexter (story_config.py).
    Hamtas en gang av sidan; andras bara nar konfigfilen andras."""
    return jsonify({"story": STORY, "bage": BAGE_SV})


@app.get("/api/runs")
def api_runs():
    """All run_ids that have a status file, newest first (ISO dates sort)."""
    try:
        ids = sorted(list_runs(), reverse=True)
        return jsonify({"runs": ids})
    except Exception as e:  # surface a friendly, actionable error to the UI
        log.exception("list_runs failed")
        return jsonify({"error": _friendly(e)}), 502


@app.get("/api/status/<run_id>")
def api_status(run_id: str):
    """The status file verbatim -- the contract's own JSON, no reshaping."""
    try:
        rs = read_status(run_id)
        return app.response_class(rs.to_json(), mimetype="application/json")
    except ResourceNotFoundError:
        return jsonify({"error": f"No status file for run '{run_id}'."}), 404
    except Exception as e:
        log.exception("read_status failed")
        return jsonify({"error": _friendly(e)}), 502


def _friendly(e: Exception) -> str:
    msg = str(e)
    if "token" in msg.lower() or "401" in msg or "Kunde inte lasa kontonyckeln" in msg:
        return ("Could not authenticate to Blob. Run: az login --scope "
                "https://management.core.windows.net//.default and reload.")
    if "403" in msg or "AuthorizationPermissionMismatch" in msg:
        return ("403 from Blob: data-plane role missing (ABAC). The app runs in "
                "account-key mode by default -- check PRICINGMODEL_AUTH=key.")
    return msg[:300]


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase Z read-only status dashboard (local).")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--check", action="store_true",
                    help="Verify Blob is reachable and list runs, then exit.")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.check:
        print("Checking Blob access (first call fetches the account key, ~3-5 s) ...")
        ids = sorted(list_runs(), reverse=True)
        print(f"OK -- {len(ids)} run(s) with a status file:")
        for i in ids[:10]:
            print(f"  {i}")
        print("Run without --check to start the dashboard.")
        return 0

    print(f"Phase Z dashboard (read-only): http://127.0.0.1:{args.port}")
    print("First page load is slow (~3-5 s) while the account key is fetched.")
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

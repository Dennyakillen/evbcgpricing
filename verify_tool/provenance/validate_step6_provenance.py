"""
validate_step6_provenance.py
============================
Proves, per Step 6 (Fall_Back_Logic.py) input, whether it is LIVE GROWING data
or a FROZEN PLACEHOLDER (reused BCG facit / locked assumption), and which part of
the final blended elasticity each one drives.

This is the management-facing honesty check: when we take a documented shortcut
(reuse frozen bundle output, frozen revenue weights) to keep momentum, this script
shows -- on screen, live -- exactly what is fresh and what is frozen, with the FD
ticket for every frozen part. Frozen is REVIEW, not FAIL: it works, it is documented,
and the receipt names what must become growing later.

Against: the six inputs Constant.py declares (resolved absolute in the helper).
Method:  open each, read a freshness signal (max date / run timestamp / the
         hardcoded year-ending column name), classify, and report.

Run (PowerShell):
    cd "C:\\Projekt\\BCG\\verify_tool\\provenance"
    py -3.11 validate_step6_provenance.py

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Created:   2026-06-11
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from _provenance_helpers import (  # noqa: E402
    INPUT_REGISTRY, STEP6_EXPECTS, GROWING_CANDIDATES, FROZEN_FACIT,
    classify_input, section, subsection, now_iso, file_hash_short,
)


def _resolve_present(key):
    """Find the file Step 6 would actually consume for this input.

    Priority: a known growing candidate (freshest) -> Step 6's expected path ->
    frozen facit placeholder. Returns (path, label) or (None, None)."""
    for cand in GROWING_CANDIDATES.get(key, []):
        if cand.exists():
            return cand, "growing-candidate"
    expected = STEP6_EXPECTS.get(key)
    if expected and expected.exists():
        return expected, "step6-expected-path"
    frozen = FROZEN_FACIT.get(key)
    if frozen and frozen.exists():
        return frozen, "frozen-facit-placeholder"
    return None, None


def _read_max_date(path, date_col):
    """Best-effort max date from a column; falls back to file mtime.
    Returns (signal_value, source_str). signal_value is comparable as YYYY-MM..."""
    # File modification time is the robust freshness signal for model outputs
    # (their KEY column is Cluster-ItemCode, not a date).
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        mtime_str = None

    # If a real date column is requested AND present, prefer it.
    if date_col:
        try:
            df = pd.read_excel(path, usecols=lambda c: True, nrows=0)
            if date_col in df.columns and date_col != "KEY":
                full = pd.read_excel(path, usecols=[date_col])
                mx = pd.to_datetime(full[date_col], errors="coerce").max()
                if pd.notna(mx):
                    return mx.strftime("%Y-%m-%d"), f"max({date_col})"
        except Exception:
            pass

    return mtime_str, "file mtime"


def _yearending_col(path):
    """Return the name of any SalesTotal_YearEndingNN column (proves the lock year)."""
    try:
        df = pd.read_excel(path, nrows=0)
        for c in df.columns:
            cs = str(c)
            if "YearEnding" in cs or "ear ending" in cs:
                return cs
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description="Classify Step 6 inputs: live growing vs frozen.")
    ap.add_argument("--quiet", action="store_true", help="suppress per-input detail")
    args = ap.parse_args()

    section("STEP 6 DATA PROVENANCE  -  live growing vs frozen placeholder")
    print(f"Run timestamp: {now_iso()}")
    print("Question: which Step 6 inputs are fresh growing data, and which rest")
    print("on frozen locked assumptions? Frozen = REVIEW (documented), not FAIL.")
    print()

    rows = []
    for entry in INPUT_REGISTRY:
        key = entry["key"]
        present_path, present_label = _resolve_present(key)

        max_date = None
        yearending_col = None
        if present_path is not None:
            if entry["date_from"] == "yearending_colname":
                yearending_col = _yearending_col(present_path)
            else:
                max_date, _src = _read_max_date(present_path, entry.get("date_col"))

        verdict = classify_input(entry, present_path, present_label, max_date, yearending_col)

        rows.append({
            "label": entry["label"],
            "feeds": entry["feeds"],
            "kind": verdict["kind"],
            "reaches": verdict["reaches"],
            "status": verdict["status"],
            "fd": entry["fd"] or "-",
            "impact": entry["impact"],
            "path": str(present_path) if present_path else "(not found)",
            "hash": file_hash_short(present_path) if present_path else "n/a",
        })

        if not args.quiet:
            subsection(entry["label"])
            print(f"  Feeds        : {entry['feeds']}")
            print(f"  Classification: {verdict['kind']}")
            print(f"  Evidence     : {verdict['evidence']}")
            print(f"  FD ticket    : {entry['fd'] or '-'}")
            print(f"  File         : {present_path if present_path else '(not found)'}")
            print(f"  Hash         : {rows[-1]['hash']}")
            print(f"  Impact       : {entry['impact']}")
            print()

    # ---- management headline table ----
    section("PROVENANCE HEADLINE  (read top-down)")
    print(f"{'Step 6 input':<42} {'Source':<20} {'Reaches':<22} {'Feeds':<34} {'FD':<6}")
    print("-" * 124)
    for r in rows:
        print(f"{r['label'][:41]:<42} {r['kind'][:19]:<20} {r['reaches'][:21]:<22} "
              f"{r['feeds'][:33]:<34} {r['fd']:<6}")
    print("-" * 124)
    print()

    n_growing = sum(1 for r in rows if r["kind"] == "LIVE GROWING")
    n_frozen = sum(1 for r in rows if "FROZEN" in r["kind"])
    n_missing = sum(1 for r in rows if r["kind"] == "MISSING")
    total = len(rows)

    section("PROVENANCE SUMMARY")
    print(f"  LIVE GROWING : {n_growing}/{total}")
    print(f"  FROZEN       : {n_frozen}/{total}")
    print(f"  MISSING      : {n_missing}/{total}")
    print()

    if n_frozen:
        print("  Frozen inputs (what must become growing -- see FD tickets):")
        for r in rows:
            if "FROZEN" in r["kind"]:
                print(f"    - {r['label']} [{r['fd']}]: {r['impact']}")
        print()

    # Overall verdict for the master runner to pick up.
    if n_missing:
        overall = "REVIEW"   # missing growing source -> needs attention, but not a hard fail here
        note = "Some inputs not found; Step 6 cannot run until resolved (see MISSING above)."
    elif n_frozen:
        overall = "REVIEW"
        note = ("Model runs, but rests partly on frozen locks. This is the documented "
                "shortcut -- decision-makers must know which numbers are fresh.")
    else:
        overall = "PASS"
        note = "All Step 6 inputs are live growing data."

    print(f"  >> Result: {overall}")
    print(f"  {note}")
    print()
    print("  NOTE: 'frozen' is honesty, not failure. The blended elasticity is as fresh")
    print("  as its inputs; this receipt makes the mix explicit so nobody over-trusts it.")

    # exit 0 on PASS, 1 on REVIEW (so CI/run_all flags it without treating as crash)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

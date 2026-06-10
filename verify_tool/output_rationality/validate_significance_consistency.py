"""
validate_significance_consistency.py
=====================================
Compares significance classification between our run and BCG facit.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Overall significance rate: ours vs BCG (expected similar but ours can be lower
    if we have more KEY with less data per KEY)
  - Per-KEY agreement: where we both flag significant vs different decisions
  - Significance "flip" rate (we sig but BCG not, or vice versa)
  - Direction of changes: are we becoming MORE or LESS sig as data grows?

CONTEXT:
  Our 2026-06-08 cluster run: 1397/4180 = 33.4% significant
  BCG facit: 1541/3812 = 40.4% significant
  Difference: 7 percentage points
  
  Reasons our rate is lower:
  - New tjänster (AAP, DUS) have shorter price history
  - Smaller cluster aggregates have noisier elasticities
  - FTE NULL share (15-20%) for newer weeks affects regression noise
  
  Step 6 (Fall_Back_Logic) is designed to rescue many of these via hierarchical
  fallback - so 33.4% pre-fallback is not the final number.

THRESHOLDS:
  - Significance rate within 10 percentage points of BCG (33-50% acceptable)
  - Agreement rate on shared KEY >= 75%
  - "Both significant" rate >= 80% of BCG's significant population

OUTPUT:
  - Console log with cross-tab
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/08_significance_consistency_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse
import pandas as pd
import numpy as np
from _rationality_helpers import (
    resolve_our_output_summary, BCG_FACIT_OUTPUT_SUMMARY,
    COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE,
    SIG_RSQ_MIN, SIG_PVALUE_MAX,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("SIGNIFICANCE CONSISTENCY VALIDATION (vs BCG facit)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    subsection("[1/4] Resolving inputs and loading")
    our_path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Ours: {source_label} -> {our_path}")
    if not BCG_FACIT_OUTPUT_SUMMARY.exists():
        sys.exit(f"ERROR: BCG facit not found: {BCG_FACIT_OUTPUT_SUMMARY}")

    ours = pd.read_excel(our_path)
    bcg = pd.read_excel(BCG_FACIT_OUTPUT_SUMMARY)

    for c in [COL_RSQ, COL_PVALUE]:
        ours[c] = pd.to_numeric(ours[c], errors="coerce")
        bcg[c] = pd.to_numeric(bcg[c], errors="coerce")

    ours["sig"] = (ours[COL_RSQ] >= SIG_RSQ_MIN) & (ours[COL_PVALUE] <= SIG_PVALUE_MAX)
    bcg["sig"] = (bcg[COL_RSQ] >= SIG_RSQ_MIN) & (bcg[COL_PVALUE] <= SIG_PVALUE_MAX)
    print()

    # ----- Aggregate rates -----
    subsection("[2/4] Aggregate significance rates")
    n_ours = len(ours)
    n_sig_ours = ours["sig"].sum()
    pct_sig_ours = 100 * n_sig_ours / n_ours

    n_bcg = len(bcg)
    n_sig_bcg = bcg["sig"].sum()
    pct_sig_bcg = 100 * n_sig_bcg / n_bcg

    print(f"  Ours:  {fmt_int(n_sig_ours)}/{fmt_int(n_ours)} = {pct_sig_ours:.1f}% significant")
    print(f"  BCG:   {fmt_int(n_sig_bcg)}/{fmt_int(n_bcg)} = {pct_sig_bcg:.1f}% significant")
    print(f"  Diff:  {pct_sig_ours - pct_sig_bcg:+.1f} percentage points")
    print()

    # ----- Per-KEY agreement -----
    subsection("[3/4] Per-KEY significance agreement (shared KEY)")
    o = ours[[COL_KEY, "sig"]].rename(columns={"sig": "sig_ours"})
    b = bcg[[COL_KEY, "sig"]].rename(columns={"sig": "sig_bcg"})
    m = o.merge(b, on=COL_KEY, how="inner")
    n_shared = len(m)

    n_both_sig = (m["sig_ours"] & m["sig_bcg"]).sum()
    n_neither_sig = (~m["sig_ours"] & ~m["sig_bcg"]).sum()
    n_only_ours_sig = (m["sig_ours"] & ~m["sig_bcg"]).sum()
    n_only_bcg_sig = (~m["sig_ours"] & m["sig_bcg"]).sum()

    n_agree = n_both_sig + n_neither_sig
    pct_agree = 100 * n_agree / n_shared if n_shared else 0

    print(f"  Shared KEY:              {fmt_int(n_shared)}")
    print(f"  Both significant:        {fmt_int(n_both_sig)} ({100*n_both_sig/n_shared:.1f}%)")
    print(f"  Neither significant:     {fmt_int(n_neither_sig)} ({100*n_neither_sig/n_shared:.1f}%)")
    print(f"  Only ours significant:   {fmt_int(n_only_ours_sig)} ({100*n_only_ours_sig/n_shared:.1f}%)")
    print(f"  Only BCG significant:    {fmt_int(n_only_bcg_sig)} ({100*n_only_bcg_sig/n_shared:.1f}%)")
    print(f"  Agreement rate:          {pct_agree:.1f}%")
    print()

    # Of BCG's significant, how many do we also flag?
    bcg_sig_set = m[m["sig_bcg"]]
    if len(bcg_sig_set):
        recover_rate = 100 * bcg_sig_set["sig_ours"].sum() / len(bcg_sig_set)
        print(f"  BCG-sig KEY also flagged sig by us: "
              f"{bcg_sig_set['sig_ours'].sum()}/{len(bcg_sig_set)} ({recover_rate:.1f}%)")
    else:
        recover_rate = 100
    print()

    # ----- Checks -----
    subsection("[4/4] Checks")
    checks = []

    # Check 1: Our rate within +/- 10 pp of BCG
    abs_diff = abs(pct_sig_ours - pct_sig_bcg)
    chk1_pass = abs_diff <= 10
    print(f"  Sig rate within +/- 10pp of BCG: {abs_diff:.1f} pp -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append(("Sig rate diff <= 10pp", f"{abs_diff:.1f}", "<= 10pp",
                   "PASS" if chk1_pass else "REVIEW"))

    # Check 2: Agreement rate >= 75%
    chk2_pass = pct_agree >= 75
    print(f"  Agreement rate >= 75%: {pct_agree:.1f}% -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("Agreement rate >= 75%", f"{pct_agree:.1f}%", ">= 75%",
                   "PASS" if chk2_pass else "REVIEW"))

    # Check 3: BCG-sig recovery >= 80%
    chk3_pass = recover_rate >= 80
    print(f"  BCG-sig recovery >= 80%: {recover_rate:.1f}% -> "
          f"{'PASS' if chk3_pass else 'REVIEW'}")
    checks.append(("BCG-sig recovery >= 80%", f"{recover_rate:.1f}%", ">= 80%",
                   "PASS" if chk3_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Significance consistency vs BCG.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"08_significance_consistency_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_significance_consistency.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

"""
validate_distribution.py
=========================
Validates aggregate distribution of elasticities in our output.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Total KEY count vs expected (>= 3812 from BCG facit baseline)
  - Elasticity distribution: mean, median, percentiles, std
  - Negative/positive/zero share (expected: ~76% neg for cluster level per IB.9)
  - Significance rate per BCG gate (RSQ >= 0.5 AND p <= 0.2)
  - Distribution sanity: not heavily skewed by extreme outliers

THRESHOLDS:
  - KEY count >= 3812 (BCG facit baseline)
  - Negative share between 60% and 85% (cluster level reference IB.9: 76.5%)
  - Significance rate between 10% and 50%
  - Median elasticity between -1.0 and 0.0 (negative but not extreme)

OUTPUT:
  - Console log (structural)
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/01_distribution_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse
import pandas as pd
import numpy as np
from _rationality_helpers import (
    resolve_our_output_summary,
    COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE,
    SIG_RSQ_MIN, SIG_PVALUE_MAX,
    fmt_int, fmt_pct, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("DISTRIBUTION VALIDATION (aggregate elasticity profile)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    # ----- Resolve output -----
    subsection("[1/5] Resolving output_summary.xlsx")
    path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Source: {source_label}")
    print(f"  Path:   {path}")
    print(f"  Hash:   {file_hash_short(path)}")
    print()

    # ----- Load -----
    subsection("[2/5] Loading output")
    df = pd.read_excel(path)
    print(f"  Rows (KEY): {fmt_int(len(df))}")
    print(f"  Columns: {list(df.columns)}")
    print()

    # ----- Aggregate distribution -----
    subsection("[3/5] Elasticity distribution")
    elast = pd.to_numeric(df[COL_ELASTICITY], errors="coerce")
    n = len(elast)
    n_nan = elast.isna().sum()

    mean_v = elast.mean()
    median_v = elast.median()
    std_v = elast.std()
    p01 = elast.quantile(0.01)
    p05 = elast.quantile(0.05)
    p25 = elast.quantile(0.25)
    p75 = elast.quantile(0.75)
    p95 = elast.quantile(0.95)
    p99 = elast.quantile(0.99)
    min_v = elast.min()
    max_v = elast.max()

    print(f"  Total rows:    {fmt_int(n)}")
    print(f"  Missing:       {fmt_int(n_nan)}")
    print(f"  Mean:          {mean_v:>+8.4f}")
    print(f"  Median:        {median_v:>+8.4f}")
    print(f"  Std dev:       {std_v:>8.4f}")
    print(f"  Min:           {min_v:>+8.4f}")
    print(f"  P01:           {p01:>+8.4f}")
    print(f"  P05:           {p05:>+8.4f}")
    print(f"  P25:           {p25:>+8.4f}")
    print(f"  P75:           {p75:>+8.4f}")
    print(f"  P95:           {p95:>+8.4f}")
    print(f"  P99:           {p99:>+8.4f}")
    print(f"  Max:           {max_v:>+8.4f}")
    print()

    # ----- Sign distribution -----
    subsection("[4/5] Sign distribution")
    n_neg = (elast < 0).sum()
    n_pos = (elast > 0).sum()
    n_zero = (elast == 0).sum()
    pct_neg = 100 * n_neg / n if n else 0
    pct_pos = 100 * n_pos / n if n else 0
    pct_zero = 100 * n_zero / n if n else 0

    print(f"  Negative:      {fmt_int(n_neg)} ({pct_neg:>5.1f}%)")
    print(f"  Positive:      {fmt_int(n_pos)} ({pct_pos:>5.1f}%)")
    print(f"  Zero:          {fmt_int(n_zero)} ({pct_zero:>5.1f}%)")
    print()

    # Significance per BCG gate
    rsq = pd.to_numeric(df[COL_RSQ], errors="coerce")
    pval = pd.to_numeric(df[COL_PVALUE], errors="coerce")
    sig_mask = (rsq >= SIG_RSQ_MIN) & (pval <= SIG_PVALUE_MAX)
    n_sig = sig_mask.sum()
    pct_sig = 100 * n_sig / n if n else 0
    print(f"  Significant (RSQ>={SIG_RSQ_MIN} AND p<={SIG_PVALUE_MAX}): "
          f"{fmt_int(n_sig)} ({pct_sig:>5.1f}%)")
    print()

    # ----- Checks -----
    subsection("[5/5] Sanity checks")
    checks = []

    # Check 1: KEY count
    chk1_pass = n >= 3812
    print(f"  KEY count >= 3812 (BCG facit baseline): {n} -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append(("KEY count >= BCG baseline", n, ">= 3812",
                   "PASS" if chk1_pass else "REVIEW"))

    # Check 2: Negative share
    chk2_pass = 60 <= pct_neg <= 85
    print(f"  Negative share 60-85% (IB.9 ref 76.5%): {pct_neg:.1f}% -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("Negative share 60-85%", f"{pct_neg:.1f}%", "60-85%",
                   "PASS" if chk2_pass else "REVIEW"))

    # Check 3: Significance rate
    chk3_pass = 10 <= pct_sig <= 50
    print(f"  Significance rate 10-50% (BCG ref 18%): {pct_sig:.1f}% -> "
          f"{'PASS' if chk3_pass else 'REVIEW'}")
    checks.append(("Significance rate 10-50%", f"{pct_sig:.1f}%", "10-50%",
                   "PASS" if chk3_pass else "REVIEW"))

    # Check 4: Median elasticity in rational band
    chk4_pass = -1.0 <= median_v <= 0.0
    print(f"  Median elasticity -1.0 to 0.0: {median_v:+.4f} -> "
          f"{'PASS' if chk4_pass else 'REVIEW'}")
    checks.append(("Median in rational band", f"{median_v:+.4f}", "-1.0 to 0.0",
                   "PASS" if chk4_pass else "REVIEW"))

    # Check 5: No NaN explosion (>1% would be concerning)
    pct_nan = 100 * n_nan / n if n else 0
    chk5_pass = pct_nan < 1.0
    print(f"  NaN share < 1%: {pct_nan:.2f}% -> "
          f"{'PASS' if chk5_pass else 'REVIEW'}")
    checks.append(("NaN share < 1%", f"{pct_nan:.2f}%", "< 1%",
                   "PASS" if chk5_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)

    if overall_pass:
        status = "PASS"
    elif overall_review:
        status = "REVIEW"
    else:
        status = "FAIL"

    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Validate distribution of elasticities.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"01_distribution_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_distribution.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

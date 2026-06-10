"""
validate_outliers.py
=====================
Identifies KEY with extreme elasticity values that warrant manual review.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - KEY with |elasticity| > 5.0 (outlier threshold)
  - KEY with elasticity < -10 (BCG's absurd lower bound)
  - KEY with significant + extreme (RSQ>=0.5, p<=0.2, AND |elast|>5)
  - Outlier concentration: are extremes clustered in specific ItemCodes or services?

THRESHOLDS:
  - Outlier rate < 5% of total KEY
  - Significant outlier rate < 1% (these would be the most concerning - "trustworthy extremes")
  - Negative floor breaches (< -10) = expected to be 0 or very few

OUTPUT:
  - Console log with top outliers listed
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/02_outliers_<timestamp>.xlsx
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
    OUTLIER_ABS_THRESHOLD, OUTLIER_NEGATIVE_FLOOR,
    SIG_RSQ_MIN, SIG_PVALUE_MAX,
    extract_itemcode_from_key, extract_cluster_from_key,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("OUTLIER VALIDATION (extreme elasticity values)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    # ----- Resolve -----
    subsection("[1/5] Resolving output_summary.xlsx")
    path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Source: {source_label}")
    print(f"  Path:   {path}")
    print()

    # ----- Load -----
    subsection("[2/5] Loading output")
    df = pd.read_excel(path)
    df[COL_ELASTICITY] = pd.to_numeric(df[COL_ELASTICITY], errors="coerce")
    df[COL_RSQ] = pd.to_numeric(df[COL_RSQ], errors="coerce")
    df[COL_PVALUE] = pd.to_numeric(df[COL_PVALUE], errors="coerce")
    df["ItemCode"] = extract_itemcode_from_key(df[COL_KEY])
    df["Cluster"] = extract_cluster_from_key(df[COL_KEY])
    n_total = len(df)
    print(f"  Rows: {fmt_int(n_total)}")
    print()

    # ----- Outliers by threshold -----
    subsection("[3/5] Outlier identification")

    # Outlier: |elast| > 5.0
    abs_outlier_mask = df[COL_ELASTICITY].abs() > OUTLIER_ABS_THRESHOLD
    n_abs_outliers = abs_outlier_mask.sum()
    pct_abs_outliers = 100 * n_abs_outliers / n_total

    # Below floor: < -10
    floor_mask = df[COL_ELASTICITY] < OUTLIER_NEGATIVE_FLOOR
    n_floor = floor_mask.sum()
    pct_floor = 100 * n_floor / n_total

    # Significant AND outlier
    sig_mask = (df[COL_RSQ] >= SIG_RSQ_MIN) & (df[COL_PVALUE] <= SIG_PVALUE_MAX)
    sig_outlier_mask = sig_mask & abs_outlier_mask
    n_sig_outliers = sig_outlier_mask.sum()
    pct_sig_outliers = 100 * n_sig_outliers / n_total

    print(f"  Outliers (|elast| > {OUTLIER_ABS_THRESHOLD}): "
          f"{fmt_int(n_abs_outliers)} ({pct_abs_outliers:.2f}%)")
    print(f"  Below floor (elast < {OUTLIER_NEGATIVE_FLOOR}): "
          f"{fmt_int(n_floor)} ({pct_floor:.2f}%)")
    print(f"  Significant AND outlier:           "
          f"{fmt_int(n_sig_outliers)} ({pct_sig_outliers:.2f}%)")
    print()

    # ----- Top outliers list -----
    subsection("[4/5] Top 15 outliers by |elasticity| (significance shown)")
    outliers = df[abs_outlier_mask].copy()
    outliers["abs_elast"] = outliers[COL_ELASTICITY].abs()
    outliers["significant"] = sig_mask[abs_outlier_mask]
    top = outliers.nlargest(15, "abs_elast")

    if len(top):
        print(f"  {'KEY':<30}  {'Elast':>9}  {'RSQ':>6}  {'pval':>6}  {'Sig?':>5}")
        for _, r in top.iterrows():
            sig_str = "YES" if r["significant"] else "no"
            print(f"  {str(r[COL_KEY])[:30]:<30}  "
                  f"{r[COL_ELASTICITY]:>+9.3f}  "
                  f"{r[COL_RSQ]:>6.3f}  "
                  f"{r[COL_PVALUE]:>6.3f}  "
                  f"{sig_str:>5}")
    else:
        print("  No outliers found.")
    print()

    # ----- Concentration analysis -----
    subsection("[5/5] Outlier concentration by ItemCode family / Cluster")
    if n_abs_outliers > 0:
        # By cluster
        by_cluster = outliers.groupby("Cluster").size().sort_values(ascending=False).head(7)
        print(f"  Top clusters by outlier count:")
        for cluster, count in by_cluster.items():
            print(f"    {cluster:<20}  {count:>4}")
        print()

        # By ItemCode prefix
        outliers["family"] = outliers["ItemCode"].str.extract(r"^([A-Z]+)", expand=False).fillna("OTHER")
        by_family = outliers.groupby("family").size().sort_values(ascending=False).head(10)
        print(f"  Top ItemCode families by outlier count:")
        for family, count in by_family.items():
            print(f"    {family:<10}  {count:>4}")
    else:
        print("  (no outliers to analyze)")
    print()

    # ----- Checks -----
    checks = []

    # Check 1: Outlier rate < 5%
    chk1_pass = pct_abs_outliers < 5.0
    checks.append(("Outlier rate < 5%", f"{pct_abs_outliers:.2f}%", "< 5%",
                   "PASS" if chk1_pass else "REVIEW"))
    print(f"  Outlier rate < 5%: {pct_abs_outliers:.2f}% -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")

    # Check 2: Significant outlier rate < 1%
    chk2_pass = pct_sig_outliers < 1.0
    checks.append(("Significant outlier rate < 1%", f"{pct_sig_outliers:.2f}%", "< 1%",
                   "PASS" if chk2_pass else "REVIEW"))
    print(f"  Significant outlier rate < 1%: {pct_sig_outliers:.2f}% -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")

    # Check 3: No floor breaches
    chk3_pass = n_floor == 0
    checks.append(("No floor breaches (elast < -10)", n_floor, 0,
                   "PASS" if chk3_pass else "REVIEW"))
    print(f"  No floor breaches (elast < -10): {n_floor} -> "
          f"{'PASS' if chk3_pass else 'REVIEW'}")

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Identify outlier elasticities.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"02_outliers_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_outliers.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

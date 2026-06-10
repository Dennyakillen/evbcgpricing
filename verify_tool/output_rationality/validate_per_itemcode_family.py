"""
validate_per_itemcode_family.py
================================
Validates elasticity consistency per ItemCode family (prefix-based grouping).

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Median elasticity per ItemCode family (AAP, DUS, AEM, etc)
  - Sample size per family (small families = unreliable)
  - Sign consistency within family (all AAP-codes should behave similarly)
  - Significance rate per family

INTERPRETATION:
  ItemCode prefixes group products by category:
  - AAP = Allmän, Avgift, Provtagning (general services)
  - DUS = Dusch / hygien (hygiene services)
  - AEM, ALB, ALT, ANALYS = clinical lab analyses
  - Pharmaceutical and surgical codes
  
  Products within a family should show roughly similar price elasticity patterns.
  If AAP125 shows -0.5 but AAP130 shows +0.8 with similar p-values, that's worth
  examining - could be a real difference, could be noise.

THRESHOLDS:
  - Families with >= 10 KEY: median sign consistency
  - Families with at least 5 KEY: report stats but don't gate
  - No family has all-positive median (all sig + positive = warning)

OUTPUT:
  - Console log with per-family table
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/06_per_itemcode_family_<timestamp>.xlsx
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
    extract_itemcode_from_key, extract_itemcode_family,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)

MIN_FAMILY_SIZE = 10  # families smaller than this aren't gated, only reported


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("PER-ITEMCODE-FAMILY VALIDATION (prefix-based consistency)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    subsection("[1/4] Resolving and loading")
    path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Source: {source_label} -> {path}")

    df = pd.read_excel(path)
    df[COL_ELASTICITY] = pd.to_numeric(df[COL_ELASTICITY], errors="coerce")
    df[COL_RSQ] = pd.to_numeric(df[COL_RSQ], errors="coerce")
    df[COL_PVALUE] = pd.to_numeric(df[COL_PVALUE], errors="coerce")
    df["ItemCode"] = extract_itemcode_from_key(df[COL_KEY])
    df["family"] = extract_itemcode_family(df["ItemCode"])
    df["sig"] = (df[COL_RSQ] >= SIG_RSQ_MIN) & (df[COL_PVALUE] <= SIG_PVALUE_MAX)

    n_total = len(df)
    n_families = df["family"].nunique()
    print(f"  Total KEY: {fmt_int(n_total)}")
    print(f"  Distinct families: {n_families}")
    print()

    # ----- Per family stats -----
    subsection("[2/4] Per-family aggregates (sorted by size)")
    grp = df.groupby("family").agg(
        n_key=(COL_KEY, "count"),
        n_codes=("ItemCode", "nunique"),
        median_elast=(COL_ELASTICITY, "median"),
        mean_elast=(COL_ELASTICITY, "mean"),
        n_neg=(COL_ELASTICITY, lambda x: (x < 0).sum()),
        n_sig=("sig", "sum"),
    ).reset_index()
    grp["pct_neg"] = 100 * grp["n_neg"] / grp["n_key"]
    grp["pct_sig"] = 100 * grp["n_sig"] / grp["n_key"]
    grp = grp.sort_values("n_key", ascending=False)

    # Print top 20 by size (also flag small families)
    print(f"  {'Family':<8}  {'#KEY':>5}  {'#Code':>5}  {'Median':>7}  "
          f"{'Mean':>7}  {'%Neg':>5}  {'%Sig':>5}")
    for _, r in grp.head(25).iterrows():
        small_flag = " *" if r["n_key"] < MIN_FAMILY_SIZE else ""
        print(f"  {r['family']:<8}  "
              f"{r['n_key']:>5}  "
              f"{r['n_codes']:>5}  "
              f"{r['median_elast']:>+7.3f}  "
              f"{r['mean_elast']:>+7.3f}  "
              f"{r['pct_neg']:>4.1f}%  "
              f"{r['pct_sig']:>4.1f}%{small_flag}")
    if len(grp) > 25:
        print(f"  ... and {len(grp) - 25} more families")
    print(f"  (* = small family, n < {MIN_FAMILY_SIZE}, not gated)")
    print()

    # ----- Concerning families -----
    subsection("[3/4] Families with concerning patterns")

    # Concern 1: Median positive on a sizable family (price increase -> demand up?)
    pos_median = grp[(grp["n_key"] >= MIN_FAMILY_SIZE) & (grp["median_elast"] > 0)]
    if len(pos_median):
        print(f"  Families with positive median (anomalous - {len(pos_median)}):")
        for _, r in pos_median.iterrows():
            print(f"    {r['family']:<8}  n={r['n_key']:>4}  "
                  f"median={r['median_elast']:>+.3f}  pct_sig={r['pct_sig']:.1f}%")
    else:
        print(f"  No sizable families with positive median elasticity. (Good.)")
    print()

    # Concern 2: Family with low neg-share despite size
    low_neg_pct = grp[(grp["n_key"] >= MIN_FAMILY_SIZE) & (grp["pct_neg"] < 50)]
    if len(low_neg_pct):
        print(f"  Families with < 50% negative (concerning - {len(low_neg_pct)}):")
        for _, r in low_neg_pct.iterrows():
            print(f"    {r['family']:<8}  n={r['n_key']:>4}  pct_neg={r['pct_neg']:.1f}%")
    else:
        print(f"  All sizable families have >= 50% negative. (Good.)")
    print()

    # ----- Checks -----
    subsection("[4/4] Checks")
    checks = []

    # Check 1: No sizable family has positive median
    chk1_pass = len(pos_median) == 0
    print(f"  No sizable family with positive median: "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append(("No positive-median sizable family", len(pos_median), 0,
                   "PASS" if chk1_pass else "REVIEW"))

    # Check 2: All sizable families >= 50% neg
    chk2_pass = len(low_neg_pct) == 0
    print(f"  All sizable families >= 50% negative: "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("All sizable >= 50% neg", len(low_neg_pct), 0,
                   "PASS" if chk2_pass else "REVIEW"))

    # Check 3: At least 5 sizable families
    n_sizable = (grp["n_key"] >= MIN_FAMILY_SIZE).sum()
    chk3_pass = n_sizable >= 5
    print(f"  At least 5 sizable families: {n_sizable} -> "
          f"{'PASS' if chk3_pass else 'REVIEW'}")
    checks.append(("At least 5 sizable families", n_sizable, ">= 5",
                   "PASS" if chk3_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Per-ItemCode-family consistency.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"06_per_itemcode_family_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_per_itemcode_family.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

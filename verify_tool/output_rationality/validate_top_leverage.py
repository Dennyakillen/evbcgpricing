"""
validate_top_leverage.py
=========================
Identifies KEY with largest pricing leverage (revenue x |elasticity|).
These are the products where small price changes would have the biggest impact.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Computes leverage = TotalNet * |elasticity| for each KEY
  - Lists top 50 KEY by leverage (where price decisions would matter most)
  - Restricts to significant KEY (BCG gate) - decision-relevant only
  - Coverage check: what share of total revenue is in top 50?
  - Distribution: how concentrated is the leverage?

WHY THIS MATTERS:
  Price decisions on a low-revenue product with high elasticity have small impact.
  Price decisions on a high-revenue product with moderate elasticity have big impact.
  Leverage = the metric that tells you WHERE to focus pricing analysis first.

OUTPUT:
  - Console log with top 50 list
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/07_top_leverage_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse
import pandas as pd
import numpy as np
from _rationality_helpers import (
    resolve_our_output_summary,
    COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET,
    SIG_RSQ_MIN, SIG_PVALUE_MAX,
    extract_itemcode_from_key, extract_cluster_from_key,
    fmt_int, fmt_msek, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)

TOP_N = 50


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("TOP LEVERAGE VALIDATION (revenue x |elasticity|)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    subsection("[1/4] Resolving and loading")
    path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Source: {source_label} -> {path}")

    df = pd.read_excel(path)
    df[COL_ELASTICITY] = pd.to_numeric(df[COL_ELASTICITY], errors="coerce")
    df[COL_RSQ] = pd.to_numeric(df[COL_RSQ], errors="coerce")
    df[COL_PVALUE] = pd.to_numeric(df[COL_PVALUE], errors="coerce")
    df[COL_TOTALNET] = pd.to_numeric(df[COL_TOTALNET], errors="coerce")
    df["sig"] = (df[COL_RSQ] >= SIG_RSQ_MIN) & (df[COL_PVALUE] <= SIG_PVALUE_MAX)
    df["ItemCode"] = extract_itemcode_from_key(df[COL_KEY])
    df["Cluster"] = extract_cluster_from_key(df[COL_KEY])

    print(f"  Total KEY:        {fmt_int(len(df))}")
    print(f"  Significant KEY:  {fmt_int(df['sig'].sum())}")
    print()

    # ----- Compute leverage -----
    subsection("[2/4] Computing leverage")
    df["abs_elast"] = df[COL_ELASTICITY].abs()
    df["leverage"] = df[COL_TOTALNET] * df["abs_elast"]

    # Filter to significant + valid
    valid = df[df["sig"] & df["leverage"].notna()].copy()
    n_valid = len(valid)
    print(f"  Eligible (significant + valid): {fmt_int(n_valid)}")

    total_revenue_all = df[COL_TOTALNET].sum()
    total_revenue_sig = valid[COL_TOTALNET].sum()
    total_leverage = valid["leverage"].sum()
    print(f"  Total revenue (all KEY):    {fmt_msek(total_revenue_all)}")
    print(f"  Total revenue (significant): {fmt_msek(total_revenue_sig)}")
    print(f"  Total leverage:             {total_leverage:>16,.0f}")
    print()

    # ----- Top N by leverage -----
    subsection(f"[3/4] Top {TOP_N} KEY by leverage (revenue x |elast|)")
    top = valid.nlargest(TOP_N, "leverage").copy()
    top["pct_of_leverage"] = 100 * top["leverage"] / total_leverage
    top["cum_pct"] = top["pct_of_leverage"].cumsum()

    print(f"  {'#':>3}  {'KEY':<28}  {'Rev MSEK':>9}  {'Elast':>7}  "
          f"{'Leverage':>12}  {'%':>5}  {'Cum%':>5}")
    for i, (_, r) in enumerate(top.iterrows(), 1):
        print(f"  {i:>3}  {str(r[COL_KEY])[:28]:<28}  "
              f"{r[COL_TOTALNET]/1e6:>9.2f}  "
              f"{r[COL_ELASTICITY]:>+7.3f}  "
              f"{r['leverage']:>12,.0f}  "
              f"{r['pct_of_leverage']:>4.1f}%  "
              f"{r['cum_pct']:>4.1f}%")
    print()

    # ----- Coverage analysis -----
    subsection("[4/4] Leverage concentration analysis")
    cum_top_n = top["leverage"].sum()
    pct_top_n = 100 * cum_top_n / total_leverage if total_leverage else 0
    rev_in_top = top[COL_TOTALNET].sum()
    pct_rev_in_top = 100 * rev_in_top / total_revenue_sig if total_revenue_sig else 0

    print(f"  Top {TOP_N} leverage:           {cum_top_n:>16,.0f}")
    print(f"  Top {TOP_N} as % of total:     {pct_top_n:>5.1f}%")
    print(f"  Top {TOP_N} revenue:           {fmt_msek(rev_in_top)}")
    print(f"  Top {TOP_N} as % of sig rev:   {pct_rev_in_top:>5.1f}%")
    print()

    # Cluster/family distribution in top N
    print(f"  Top {TOP_N} by Cluster:")
    cluster_dist = top.groupby("Cluster").size().sort_values(ascending=False)
    for cluster, count in cluster_dist.items():
        print(f"    {cluster:<22}  {count:>3}")
    print()

    print(f"  Top {TOP_N} by ItemCode family:")
    top["family"] = top["ItemCode"].str.extract(r"^([A-Z]+)", expand=False).fillna("OTHER")
    family_dist = top.groupby("family").size().sort_values(ascending=False).head(10)
    for family, count in family_dist.items():
        print(f"    {family:<10}  {count:>3}")
    print()

    # ----- Checks -----
    checks = []

    # Check 1: At least 50 significant KEY available
    chk1_pass = n_valid >= TOP_N
    print(f"  At least {TOP_N} significant KEY: {n_valid} -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append((f"Eligible >= {TOP_N}", n_valid, f">= {TOP_N}",
                   "PASS" if chk1_pass else "REVIEW"))

    # Check 2: Top 50 captures meaningful share (>= 20%)
    chk2_pass = pct_top_n >= 20
    print(f"  Top {TOP_N} captures >= 20% of leverage: {pct_top_n:.1f}% -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append((f"Top {TOP_N} >= 20% leverage", f"{pct_top_n:.1f}%", ">= 20%",
                   "PASS" if chk2_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Top leverage KEY analysis.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"07_top_leverage_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_top_leverage.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

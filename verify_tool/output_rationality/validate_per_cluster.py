"""
validate_per_cluster.py
========================
Validates elasticity consistency per cluster.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Median elasticity per cluster (should be roughly comparable across clusters)
  - Significance rate per cluster (high variance = uneven model quality)
  - Negative share per cluster (clusters with < 50% neg = concerning)
  - Outlier concentration per cluster (one cluster shouldn't dominate)

INTERPRETATION:
  Different clusters serve different patient populations and pricing contexts.
  Some variation is expected, but extreme differences may indicate:
  - Data quality issues in one cluster
  - Pricing strategy differences (premium vs budget clinics)
  - Sample size effects in small clusters

THRESHOLDS:
  - Median elasticity per cluster within [-1.5, 0.0]
  - Negative share per cluster >= 50%
  - Significance rate per cluster >= 10%
  - No single cluster has > 40% of total outliers

OUTPUT:
  - Console log with per-cluster table
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/05_per_cluster_<timestamp>.xlsx
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
    SIG_RSQ_MIN, SIG_PVALUE_MAX, OUTLIER_ABS_THRESHOLD,
    extract_cluster_from_key,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("PER-CLUSTER VALIDATION (consistency across clusters)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    subsection("[1/4] Resolving and loading")
    path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Source: {source_label} -> {path}")

    df = pd.read_excel(path)
    df[COL_ELASTICITY] = pd.to_numeric(df[COL_ELASTICITY], errors="coerce")
    df[COL_RSQ] = pd.to_numeric(df[COL_RSQ], errors="coerce")
    df[COL_PVALUE] = pd.to_numeric(df[COL_PVALUE], errors="coerce")
    df["Cluster"] = extract_cluster_from_key(df[COL_KEY])
    df["sig"] = (df[COL_RSQ] >= SIG_RSQ_MIN) & (df[COL_PVALUE] <= SIG_PVALUE_MAX)
    df["is_outlier"] = df[COL_ELASTICITY].abs() > OUTLIER_ABS_THRESHOLD

    n_total = len(df)
    n_clusters = df["Cluster"].nunique()
    print(f"  Total KEY: {fmt_int(n_total)}")
    print(f"  Distinct clusters: {n_clusters}")
    print()

    # ----- Per cluster stats -----
    subsection("[2/4] Per-cluster aggregates")
    grp = df.groupby("Cluster").agg(
        n_key=(COL_KEY, "count"),
        median_elast=(COL_ELASTICITY, "median"),
        mean_elast=(COL_ELASTICITY, "mean"),
        n_neg=(COL_ELASTICITY, lambda x: (x < 0).sum()),
        n_sig=("sig", "sum"),
        n_outlier=("is_outlier", "sum"),
    ).reset_index()
    grp["pct_neg"] = 100 * grp["n_neg"] / grp["n_key"]
    grp["pct_sig"] = 100 * grp["n_sig"] / grp["n_key"]
    grp["pct_outlier"] = 100 * grp["n_outlier"] / grp["n_key"]
    grp = grp.sort_values("n_key", ascending=False)

    print(f"  {'Cluster':<22}  {'#KEY':>5}  {'Median':>7}  {'Mean':>7}  "
          f"{'%Neg':>5}  {'%Sig':>5}  {'%Out':>5}")
    for _, r in grp.iterrows():
        print(f"  {str(r['Cluster'])[:22]:<22}  "
              f"{r['n_key']:>5}  "
              f"{r['median_elast']:>+7.3f}  "
              f"{r['mean_elast']:>+7.3f}  "
              f"{r['pct_neg']:>4.1f}%  "
              f"{r['pct_sig']:>4.1f}%  "
              f"{r['pct_outlier']:>4.1f}%")
    print()

    # ----- Concentration -----
    subsection("[3/4] Outlier concentration analysis")
    total_outliers = grp["n_outlier"].sum()
    if total_outliers > 0:
        grp["pct_of_outliers"] = 100 * grp["n_outlier"] / total_outliers
        max_concentration_cluster = grp.loc[grp["pct_of_outliers"].idxmax(), "Cluster"]
        max_concentration_pct = grp["pct_of_outliers"].max()
        print(f"  Total outliers: {total_outliers}")
        print(f"  Most concentrated in: {max_concentration_cluster} ({max_concentration_pct:.1f}%)")
    else:
        max_concentration_pct = 0
        print(f"  No outliers in any cluster.")
    print()

    # ----- Checks -----
    subsection("[4/4] Checks")
    checks = []

    # Check 1: All median elasticities in rational band
    out_of_band = grp[~grp["median_elast"].between(-1.5, 0.0)]
    chk1_pass = len(out_of_band) == 0
    print(f"  All cluster medians in [-1.5, 0.0]: "
          f"{n_clusters - len(out_of_band)}/{n_clusters} -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    if len(out_of_band):
        for _, r in out_of_band.iterrows():
            print(f"    Out of band: {r['Cluster']} median={r['median_elast']:+.3f}")
    checks.append(("All cluster medians in band", f"{n_clusters - len(out_of_band)}/{n_clusters}",
                   "all", "PASS" if chk1_pass else "REVIEW"))

    # Check 2: All clusters have >= 50% negative
    low_neg = grp[grp["pct_neg"] < 50]
    chk2_pass = len(low_neg) == 0
    print(f"  All clusters >= 50% negative: "
          f"{n_clusters - len(low_neg)}/{n_clusters} -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("All clusters >= 50% negative", f"{n_clusters - len(low_neg)}/{n_clusters}",
                   "all", "PASS" if chk2_pass else "REVIEW"))

    # Check 3: All clusters have >= 10% significant
    low_sig = grp[grp["pct_sig"] < 10]
    chk3_pass = len(low_sig) == 0
    print(f"  All clusters >= 10% significant: "
          f"{n_clusters - len(low_sig)}/{n_clusters} -> "
          f"{'PASS' if chk3_pass else 'REVIEW'}")
    checks.append(("All clusters >= 10% sig", f"{n_clusters - len(low_sig)}/{n_clusters}",
                   "all", "PASS" if chk3_pass else "REVIEW"))

    # Check 4: No cluster has > 40% of outliers
    chk4_pass = max_concentration_pct <= 40
    print(f"  Max outlier concentration <= 40%: {max_concentration_pct:.1f}% -> "
          f"{'PASS' if chk4_pass else 'REVIEW'}")
    checks.append(("Outlier concentration <= 40%", f"{max_concentration_pct:.1f}%", "<= 40%",
                   "PASS" if chk4_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Per-cluster consistency check.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"05_per_cluster_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_per_cluster.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

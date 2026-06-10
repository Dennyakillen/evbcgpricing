"""
validate_drift_vs_bcg.py
=========================
Compares per-KEY elasticity drift between our output and BCG's frozen facit.
Answers: "What has changed since BCG's 2025-07 snapshot, and does it matter?"

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Per-KEY elasticity delta for KEY present in both
  - Distribution of |delta_elasticity|: median, P95, max
  - KEY with decision-relevant drift (|delta| > 0.5)
  - KEY where one or both is significant (the cases that matter for price decisions)
  - Correlation between elasticities (Spearman rank correlation - robust to outliers)

THRESHOLDS:
  - Median |delta| < 0.05 (typical KEY is bit-identical or near-identical)
  - P95 |delta| < 0.5 (95% of KEY within acceptable drift band)
  - KEY with |delta| > 1.0 + both significant < 5% of overlap

OUTPUT:
  - Console log with top drift cases listed
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/03_drift_vs_bcg_<timestamp>.xlsx
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
    DRIFT_ABS_TOLERANCE, DRIFT_HARD_THRESHOLD,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("DRIFT VS BCG VALIDATION (per-KEY delta on shared population)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    # ----- Resolve paths -----
    subsection("[1/5] Resolving inputs")
    our_path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Ours: {source_label} -> {our_path}")
    if not BCG_FACIT_OUTPUT_SUMMARY.exists():
        sys.exit(f"ERROR: BCG facit not found: {BCG_FACIT_OUTPUT_SUMMARY}")
    print(f"  BCG:  {BCG_FACIT_OUTPUT_SUMMARY}")
    print()

    # ----- Load both -----
    subsection("[2/5] Loading and merging")
    ours = pd.read_excel(our_path)
    bcg = pd.read_excel(BCG_FACIT_OUTPUT_SUMMARY)
    ours[COL_ELASTICITY] = pd.to_numeric(ours[COL_ELASTICITY], errors="coerce")
    bcg[COL_ELASTICITY] = pd.to_numeric(bcg[COL_ELASTICITY], errors="coerce")
    ours[COL_RSQ] = pd.to_numeric(ours[COL_RSQ], errors="coerce")
    bcg[COL_RSQ] = pd.to_numeric(bcg[COL_RSQ], errors="coerce")
    ours[COL_PVALUE] = pd.to_numeric(ours[COL_PVALUE], errors="coerce")
    bcg[COL_PVALUE] = pd.to_numeric(bcg[COL_PVALUE], errors="coerce")

    print(f"  Our rows: {fmt_int(len(ours))}")
    print(f"  BCG rows: {fmt_int(len(bcg))}")
    print()

    # Population overlap
    our_keys = set(ours[COL_KEY])
    bcg_keys = set(bcg[COL_KEY])
    both = our_keys & bcg_keys
    only_ours = our_keys - bcg_keys
    only_bcg = bcg_keys - our_keys
    print(f"  KEY in both:    {fmt_int(len(both))}")
    print(f"  Only in ours:   {fmt_int(len(only_ours))}  (new from growing window)")
    print(f"  Only in BCG:    {fmt_int(len(only_bcg))}  (lost in our run)")
    print()

    # ----- Merge and compute drift -----
    subsection("[3/5] Per-KEY drift analysis")
    o = ours[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE]].rename(
        columns={COL_ELASTICITY: "elast_ours", COL_RSQ: "rsq_ours", COL_PVALUE: "pval_ours"})
    b = bcg[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE]].rename(
        columns={COL_ELASTICITY: "elast_bcg", COL_RSQ: "rsq_bcg", COL_PVALUE: "pval_bcg"})
    m = o.merge(b, on=COL_KEY, how="inner").dropna(subset=["elast_ours", "elast_bcg"])
    n_compared = len(m)

    m["delta"] = m["elast_ours"] - m["elast_bcg"]
    m["abs_delta"] = m["delta"].abs()
    m["sig_ours"] = (m["rsq_ours"] >= SIG_RSQ_MIN) & (m["pval_ours"] <= SIG_PVALUE_MAX)
    m["sig_bcg"] = (m["rsq_bcg"] >= SIG_RSQ_MIN) & (m["pval_bcg"] <= SIG_PVALUE_MAX)
    m["both_sig"] = m["sig_ours"] & m["sig_bcg"]

    median_delta = m["abs_delta"].median()
    mean_delta = m["abs_delta"].mean()
    p95_delta = m["abs_delta"].quantile(0.95)
    p99_delta = m["abs_delta"].quantile(0.99)
    max_delta = m["abs_delta"].max()

    n_within_tol = (m["abs_delta"] < DRIFT_ABS_TOLERANCE).sum()
    n_hard_drift = (m["abs_delta"] > DRIFT_HARD_THRESHOLD).sum()
    n_decision_drift = ((m["abs_delta"] > DRIFT_ABS_TOLERANCE) & m["both_sig"]).sum()

    # Spearman rank correlation (no scipy - use rank().corr())
    rank_corr = m["elast_ours"].rank().corr(m["elast_bcg"].rank())
    pearson_corr = m["elast_ours"].corr(m["elast_bcg"])

    print(f"  Compared:         {fmt_int(n_compared)} KEY (both elasticities present)")
    print()
    print(f"  Median |delta|:   {median_delta:>+8.4f}")
    print(f"  Mean |delta|:     {mean_delta:>+8.4f}")
    print(f"  P95 |delta|:      {p95_delta:>+8.4f}")
    print(f"  P99 |delta|:      {p99_delta:>+8.4f}")
    print(f"  Max |delta|:      {max_delta:>+8.4f}")
    print()
    print(f"  Within tolerance (|delta| < {DRIFT_ABS_TOLERANCE}): "
          f"{fmt_int(n_within_tol)} ({100*n_within_tol/n_compared:.1f}%)")
    print(f"  Hard drift (|delta| > {DRIFT_HARD_THRESHOLD}):     "
          f"{fmt_int(n_hard_drift)} ({100*n_hard_drift/n_compared:.1f}%)")
    print(f"  Decision-relevant drift (|delta|>{DRIFT_ABS_TOLERANCE} AND both sig): "
          f"{fmt_int(n_decision_drift)} ({100*n_decision_drift/n_compared:.1f}%)")
    print()
    print(f"  Spearman rank correlation: {rank_corr:.6f}")
    print(f"  Pearson correlation:       {pearson_corr:.6f}")
    print()

    # ----- Top drift cases -----
    subsection("[4/5] Top 15 KEY by |delta_elasticity| (decision-relevant filter)")
    decision_drift = m[(m["abs_delta"] > DRIFT_ABS_TOLERANCE) & m["both_sig"]]
    if len(decision_drift):
        top = decision_drift.nlargest(15, "abs_delta")
        print(f"  {'KEY':<30}  {'Ours':>8}  {'BCG':>8}  {'Delta':>8}  "
              f"{'pOurs':>6}  {'pBCG':>6}")
        for _, r in top.iterrows():
            print(f"  {str(r[COL_KEY])[:30]:<30}  "
                  f"{r['elast_ours']:>+8.3f}  "
                  f"{r['elast_bcg']:>+8.3f}  "
                  f"{r['delta']:>+8.3f}  "
                  f"{r['pval_ours']:>6.3f}  "
                  f"{r['pval_bcg']:>6.3f}")
    else:
        print(f"  No decision-relevant drift cases (|delta| > {DRIFT_ABS_TOLERANCE} AND both significant).")
    print()

    # ----- Checks -----
    subsection("[5/5] Checks")
    checks = []

    chk1_pass = median_delta < 0.05
    print(f"  Median |delta| < 0.05: {median_delta:.4f} -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append(("Median |delta| < 0.05", f"{median_delta:.4f}", "< 0.05",
                   "PASS" if chk1_pass else "REVIEW"))

    chk2_pass = p95_delta < 0.5
    print(f"  P95 |delta| < 0.5: {p95_delta:.4f} -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("P95 |delta| < 0.5", f"{p95_delta:.4f}", "< 0.5",
                   "PASS" if chk2_pass else "REVIEW"))

    pct_decision_drift = 100 * n_decision_drift / n_compared if n_compared else 0
    chk3_pass = pct_decision_drift < 5.0
    print(f"  Decision-relevant drift < 5%: {pct_decision_drift:.2f}% -> "
          f"{'PASS' if chk3_pass else 'REVIEW'}")
    checks.append(("Decision-drift < 5%", f"{pct_decision_drift:.2f}%", "< 5%",
                   "PASS" if chk3_pass else "REVIEW"))

    chk4_pass = rank_corr >= 0.85
    print(f"  Spearman rank corr >= 0.85: {rank_corr:.4f} -> "
          f"{'PASS' if chk4_pass else 'REVIEW'}")
    checks.append(("Rank corr >= 0.85", f"{rank_corr:.4f}", ">= 0.85",
                   "PASS" if chk4_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Per-KEY drift vs BCG facit.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"03_drift_vs_bcg_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_drift_vs_bcg.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

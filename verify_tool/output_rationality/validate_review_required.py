"""
validate_review_required.py
============================
Aggregates KEY flagged across all previous rationality validations.
Produces the "manual review list" - the cases a chef would actually look at.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - Builds a unified list of "concerning" KEY from multiple criteria:
    * Extreme outliers (|elast| > 5)
    * Large drift vs BCG (|delta| > 1.0)
    * Sign flips with both significant
    * Top 50 leverage KEY (always include for context)
  
  - Categorizes each KEY by reason for review
  - Prioritizes by: (a) significance, (b) leverage (revenue x |elast|)
  - Produces a SINGLE concrete list of KEY needing human eyes

INTERPRETATION:
  This is the bottom-line answer to "given the pipeline ran, what do I actually
  need to look at before making price decisions?" If this list is short and
  the rest of the validations are green, the model is decision-ready.

OUTPUT:
  - Console log with categorized list
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/09_review_required_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse
import pandas as pd
import numpy as np
from _rationality_helpers import (
    resolve_our_output_summary, BCG_FACIT_OUTPUT_SUMMARY,
    COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET,
    SIG_RSQ_MIN, SIG_PVALUE_MAX,
    OUTLIER_ABS_THRESHOLD, DRIFT_HARD_THRESHOLD,
    extract_itemcode_from_key, extract_cluster_from_key,
    fmt_int, fmt_msek, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)

MAX_REVIEW_LIST = 100  # cap total flagged KEY at 100 to keep manageable


def _run_validation(output_summary_path=None):
    timestamp_iso = now_iso()

    section("REVIEW REQUIRED (aggregator - the manual review list)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    # ----- Load -----
    subsection("[1/5] Loading inputs")
    our_path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Ours: {source_label} -> {our_path}")
    ours = pd.read_excel(our_path)

    for c in [COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET]:
        ours[c] = pd.to_numeric(ours[c], errors="coerce")
    ours["sig"] = (ours[COL_RSQ] >= SIG_RSQ_MIN) & (ours[COL_PVALUE] <= SIG_PVALUE_MAX)
    ours["ItemCode"] = extract_itemcode_from_key(ours[COL_KEY])
    ours["Cluster"] = extract_cluster_from_key(ours[COL_KEY])

    bcg_available = BCG_FACIT_OUTPUT_SUMMARY.exists()
    if bcg_available:
        bcg = pd.read_excel(BCG_FACIT_OUTPUT_SUMMARY)
        for c in [COL_ELASTICITY, COL_RSQ, COL_PVALUE]:
            bcg[c] = pd.to_numeric(bcg[c], errors="coerce")
        bcg["sig"] = (bcg[COL_RSQ] >= SIG_RSQ_MIN) & (bcg[COL_PVALUE] <= SIG_PVALUE_MAX)
        b = bcg[[COL_KEY, COL_ELASTICITY, "sig"]].rename(
            columns={COL_ELASTICITY: "elast_bcg", "sig": "sig_bcg"})
        merged = ours.merge(b, on=COL_KEY, how="left")
        merged["delta"] = merged[COL_ELASTICITY] - merged["elast_bcg"]
        merged["abs_delta"] = merged["delta"].abs()
        merged["flipped"] = (
            (np.sign(merged[COL_ELASTICITY]) != np.sign(merged["elast_bcg"]))
            & (merged[COL_ELASTICITY] != 0) & (merged["elast_bcg"] != 0)
            & merged["elast_bcg"].notna()
        )
    else:
        merged = ours.copy()
        merged["sig_bcg"] = False
        merged["elast_bcg"] = np.nan
        merged["abs_delta"] = np.nan
        merged["flipped"] = False
        print(f"  WARN: BCG facit not available - drift/flip categories will be empty.")
    print()

    # ----- Categorize -----
    subsection("[2/5] Categorization")
    merged["abs_elast"] = merged[COL_ELASTICITY].abs()
    merged["leverage"] = merged[COL_TOTALNET] * merged["abs_elast"]

    # Reason 1: Extreme outlier
    merged["r1_outlier"] = merged["abs_elast"] > OUTLIER_ABS_THRESHOLD

    # Reason 2: Large drift vs BCG (only counts if both elasticities exist)
    merged["r2_drift"] = (merged["abs_delta"] > DRIFT_HARD_THRESHOLD) & merged["elast_bcg"].notna()

    # Reason 3: Sign flip with both significant
    merged["r3_flip"] = merged["flipped"] & merged["sig"] & merged["sig_bcg"]

    # Reason 4: Top 50 leverage (always include)
    merged_sig_with_lev = merged[merged["sig"] & merged["leverage"].notna()]
    top_lev_keys = set(merged_sig_with_lev.nlargest(50, "leverage")[COL_KEY])
    merged["r4_top_leverage"] = merged[COL_KEY].isin(top_lev_keys)

    n_r1 = merged["r1_outlier"].sum()
    n_r2 = merged["r2_drift"].sum()
    n_r3 = merged["r3_flip"].sum()
    n_r4 = merged["r4_top_leverage"].sum()

    print(f"  R1 - Extreme outlier (|elast| > {OUTLIER_ABS_THRESHOLD}):     {n_r1}")
    print(f"  R2 - Large drift vs BCG (|delta| > {DRIFT_HARD_THRESHOLD}):       {n_r2}")
    print(f"  R3 - Sign flip with both sig:               {n_r3}")
    print(f"  R4 - Top 50 leverage (always reviewed):     {n_r4}")
    print()

    # Combine reasons
    flagged_mask = (merged["r1_outlier"] | merged["r2_drift"] |
                    merged["r3_flip"] | merged["r4_top_leverage"])
    flagged = merged[flagged_mask].copy()

    # Build reason label
    def reason_label(row):
        reasons = []
        if row["r1_outlier"]:
            reasons.append("OUTLIER")
        if row["r2_drift"]:
            reasons.append("DRIFT")
        if row["r3_flip"]:
            reasons.append("FLIP")
        if row["r4_top_leverage"]:
            reasons.append("TOP-LEV")
        return ",".join(reasons)
    flagged["reasons"] = flagged.apply(reason_label, axis=1)

    n_flagged_unique = len(flagged)
    print(f"  Total unique KEY flagged: {n_flagged_unique}")

    # Cap at MAX_REVIEW_LIST
    if n_flagged_unique > MAX_REVIEW_LIST:
        # Prioritize: significance first, then leverage
        flagged = flagged.sort_values(
            ["sig", "leverage"], ascending=[False, False]
        ).head(MAX_REVIEW_LIST)
        print(f"  Capped at top {MAX_REVIEW_LIST} by significance + leverage.")
    print()

    # ----- Print review list -----
    subsection("[3/5] Review list (sorted by significance, then leverage)")
    flagged = flagged.sort_values(["sig", "leverage"], ascending=[False, False])
    print(f"  {'KEY':<30}  {'Rev MSEK':>9}  {'Elast':>7}  {'Sig':>4}  "
          f"{'Reasons':<25}")
    for _, r in flagged.head(30).iterrows():
        sig_str = "YES" if r["sig"] else "no"
        print(f"  {str(r[COL_KEY])[:30]:<30}  "
              f"{r[COL_TOTALNET]/1e6:>9.2f}  "
              f"{r[COL_ELASTICITY]:>+7.3f}  "
              f"{sig_str:>4}  "
              f"{str(r['reasons'])[:25]:<25}")
    if len(flagged) > 30:
        print(f"  ... and {len(flagged) - 30} more in receipt")
    print()

    # ----- Concentration -----
    subsection("[4/5] Concentration analysis")
    print(f"  By cluster:")
    cluster_dist = flagged.groupby("Cluster").size().sort_values(ascending=False)
    for cluster, count in cluster_dist.items():
        print(f"    {cluster:<22}  {count:>3}")
    print()

    # ----- Status -----
    subsection("[5/5] Verdict")
    pct_flagged = 100 * n_flagged_unique / len(merged) if len(merged) else 0

    # Status logic:
    # - n_r1 + n_r2 + n_r3 = real concerns. If < 1% of total = small enough to review.
    # - r4 (top leverage) is always included but isn't "concerning" by itself.
    real_concerns = (merged["r1_outlier"] | merged["r2_drift"] | merged["r3_flip"]).sum()
    pct_real_concerns = 100 * real_concerns / len(merged) if len(merged) else 0

    print(f"  Total flagged:        {n_flagged_unique} ({pct_flagged:.1f}% of all KEY)")
    print(f"  Real concerns (R1-3): {real_concerns} ({pct_real_concerns:.2f}% of all KEY)")
    print()

    checks = []
    chk1_pass = pct_real_concerns < 5
    print(f"  Real concerns < 5% of KEY: {pct_real_concerns:.2f}% -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append(("Real concerns < 5%", f"{pct_real_concerns:.2f}%", "< 5%",
                   "PASS" if chk1_pass else "REVIEW"))

    chk2_pass = real_concerns <= 200
    print(f"  Real concerns <= 200 absolute: {real_concerns} -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("Real concerns <= 200", real_concerns, "<= 200",
                   "PASS" if chk2_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    print()
    print(f"  Decision rule: Model is ready for chef-level review when:")
    print(f"    - real concerns < 5% AND <= 200 KEY")
    print(f"    - significant individual cases get manual sanity check")
    print(f"    - Top-50 leverage KEY are sanity-checked even if not concerning")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Aggregate review-required KEY.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"09_review_required_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_review_required.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

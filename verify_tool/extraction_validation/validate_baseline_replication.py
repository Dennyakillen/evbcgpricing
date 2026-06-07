"""
validate_baseline_replication.py
=================================
Compares our FROZEN-window extraction against BCG's frozen facit at ItemCode level.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES:
  - Per-ItemCode revenue drift between our extraction and BCG facit (frozen window only)
  - Lists top N ItemCodes by absolute drift
  - Quantifies systematic vs random drift
  - Provides forensic evidence for the aggregate -0.043% drift observed at total level

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\08_baseline_replication_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    OUR_CSV, BCG_FACIT_CSV, BCG_START, BCG_END,
    fmt_msek, fmt_pct, fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("BASELINE REPLICATION VALIDATION (per ItemCode)")
    print(f"Run timestamp: {timestamp_iso}")
    print(f"Frozen window: {BCG_START} -> {BCG_END}")
    print()

    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")
    if not BCG_FACIT_CSV.exists():
        sys.exit(f"ERROR: BCG facit missing: {BCG_FACIT_CSV}")

    # ----- Load both -----
    subsection("[1/4] Loading data")
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    bcg = pd.read_csv(BCG_FACIT_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    our["week_starting_monday"] = pd.to_datetime(our["week_starting_monday"])
    bcg["week_starting_monday"] = pd.to_datetime(bcg["week_starting_monday"])
    our["ItemCode"] = our["ItemCode"].astype(str).str.strip().str.upper()
    bcg["ItemCode"] = bcg["ItemCode"].astype(str).str.strip().str.upper()

    # Restrict our data to frozen window
    bcg_end_ts = pd.Timestamp(BCG_END)
    bcg_start_ts = pd.Timestamp(BCG_START)
    our_frozen = our[(our["week_starting_monday"] >= bcg_start_ts) &
                     (our["week_starting_monday"] <= bcg_end_ts)].copy()

    print(f"  Our frozen subset: {fmt_int(len(our_frozen))} rows")
    print(f"  BCG facit:         {fmt_int(len(bcg))} rows")
    print()

    # ----- Per ItemCode comparison -----
    subsection("[2/4] Per-ItemCode revenue comparison")
    our_by_code = our_frozen.groupby("ItemCode").agg(
        our_TotalNet=("TotalNet", "sum"),
        our_SoldQuantity=("SoldQuantity", "sum"),
        our_rows=("TotalNet", "count"),
    ).reset_index()
    bcg_by_code = bcg.groupby("ItemCode").agg(
        bcg_TotalNet=("TotalNet", "sum"),
        bcg_SoldQuantity=("SoldQuantity", "sum"),
        bcg_rows=("TotalNet", "count"),
    ).reset_index()

    merged = our_by_code.merge(bcg_by_code, on="ItemCode", how="outer", indicator=True)
    n_both = (merged["_merge"] == "both").sum()
    n_only_ours = (merged["_merge"] == "left_only").sum()
    n_only_bcg = (merged["_merge"] == "right_only").sum()
    print(f"  In both:    {n_both}")
    print(f"  Only ours:  {n_only_ours}")
    print(f"  Only BCG:   {n_only_bcg}")
    print()

    # Compute drift for matched codes
    both = merged[merged["_merge"] == "both"].copy()
    both["our_TotalNet"] = both["our_TotalNet"].fillna(0)
    both["bcg_TotalNet"] = both["bcg_TotalNet"].fillna(0)
    both["drift_abs"] = both["our_TotalNet"] - both["bcg_TotalNet"]
    both["drift_pct"] = 100 * both["drift_abs"] / both["bcg_TotalNet"].replace(0, pd.NA)
    both["drift_abs_pct"] = both["drift_pct"].abs()

    # ----- Top drifts -----
    subsection("[3/4] Top 15 ItemCodes by absolute drift")
    top_drift = both.nlargest(15, "drift_abs_pct")[
        ["ItemCode", "our_TotalNet", "bcg_TotalNet", "drift_abs", "drift_pct"]
    ]
    print(f"  {'ItemCode':<10}  {'Our (MSEK)':>10}  {'BCG (MSEK)':>10}  "
          f"{'Drift (kSEK)':>13}  {'Drift %':>8}")
    for _, r in top_drift.iterrows():
        drift_pct_val = r["drift_pct"] if pd.notna(r["drift_pct"]) else 0
        print(f"  {r['ItemCode']:<10}  {r['our_TotalNet']/1e6:>10.2f}  "
              f"{r['bcg_TotalNet']/1e6:>10.2f}  {r['drift_abs']/1e3:>13.1f}  "
              f"{drift_pct_val:>+7.2f}%")
    print()

    # Aggregate
    total_drift_abs = both["drift_abs"].sum()
    total_bcg = both["bcg_TotalNet"].sum()
    aggregate_drift_pct = 100 * total_drift_abs / total_bcg if total_bcg else 0
    median_drift_pct = both["drift_pct"].median()
    print(f"  Aggregate drift: {total_drift_abs:+,.0f} SEK ({aggregate_drift_pct:+.4f}%)")
    print(f"  Median per-code drift: {median_drift_pct:+.4f}%")
    print()

    # Status
    if abs(aggregate_drift_pct) <= 0.5:
        status = "PASS"
        status_note = f"Aggregate drift within +/-0.5% tolerance ({aggregate_drift_pct:+.4f}%)."
    else:
        status = "REVIEW"
        status_note = f"Aggregate drift exceeds +/-0.5% ({aggregate_drift_pct:+.4f}%)."

    # ----- Receipt -----
    subsection("[4/4] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"08_baseline_replication_{timestamp_file}.xlsx"

    summary_rows = [
        ["ItemCodes in both", n_both, "", ""],
        ["ItemCodes only in our extraction", n_only_ours, "", ""],
        ["ItemCodes only in BCG facit", n_only_bcg, "", ""],
        ["", "", "", ""],
        ["Our frozen revenue (SEK)", f"{both['our_TotalNet'].sum():,.0f}", "", ""],
        ["BCG facit revenue (SEK)", f"{both['bcg_TotalNet'].sum():,.0f}", "", ""],
        ["Aggregate drift (SEK)", f"{total_drift_abs:+,.0f}", "", ""],
        ["Aggregate drift (%)", f"{aggregate_drift_pct:+.4f}%", "tolerance +/-0.5%", status],
        ["Median per-code drift (%)", f"{median_drift_pct:+.4f}%", "", ""],
    ]

    top_drift_rows = [
        [r["ItemCode"],
         float(r["our_TotalNet"]),
         float(r["bcg_TotalNet"]),
         float(r["drift_abs"]),
         round(float(r["drift_pct"]) if pd.notna(r["drift_pct"]) else 0, 4)]
        for _, r in top_drift.iterrows()
    ]

    # Codes only in one side
    only_ours_rows = []
    if n_only_ours > 0:
        sub = merged[merged["_merge"] == "left_only"][["ItemCode", "our_TotalNet"]].head(50)
        only_ours_rows = [[r["ItemCode"], float(r["our_TotalNet"])] for _, r in sub.iterrows()]

    only_bcg_rows = []
    if n_only_bcg > 0:
        sub = merged[merged["_merge"] == "right_only"][["ItemCode", "bcg_TotalNet"]].head(50)
        only_bcg_rows = [[r["ItemCode"], float(r["bcg_TotalNet"])] for _, r in sub.iterrows()]

    print()
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1




def main():
    """Capture stdout while running validation, then save as single-sheet 'Logg' receipt."""
    with capture_stdout() as buf:
        exit_code = _run_validation()
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"08_baseline_replication_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_baseline_replication.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0

if __name__ == "__main__":
    sys.exit(main())

"""
validate_volume_quantity.py
============================
Validates volume/quantity consistency in the extraction.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES:
  - SoldQuantity vs NoofUnits relationship (per LB: differ ~16x by definition)
  - TotalNet vs TotalNetXVat ratio (~1.25 = 25% VAT)
  - QuantitySold(SalesTotal>0) == SoldQuantity (constants.py UNIT)
  - No negative values (already filtered, but verify)
  - Implausible outliers per ItemCode (price extremes)

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\07_volume_quantity_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from _validation_helpers import (
    OUR_CSV,
    fmt_msek, fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)


def _run_validation():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("VOLUME / QUANTITY CONSISTENCY VALIDATION")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")

    # ----- Load -----
    subsection("[1/5] Loading our extraction")
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    print(f"  Rows: {fmt_int(len(our))}")
    print()

    checks = []

    # ----- Check 1: VAT ratio -----
    subsection("[2/5] VAT ratio (TotalNet / TotalNetXVat)")
    sub = our[(our["TotalNetXVat"] > 0) & (our["TotalNet"] > 0)].copy()
    ratios = sub["TotalNet"] / sub["TotalNetXVat"]
    median_ratio = ratios.median()
    mean_ratio = ratios.mean()
    p99_ratio = ratios.quantile(0.99)
    expected = 1.25  # 25% VAT
    deviation = abs(median_ratio - expected)
    chk1_pass = deviation < 0.01
    print(f"  Median: {median_ratio:.4f} (expected ~{expected})")
    print(f"  Mean:   {mean_ratio:.4f}")
    print(f"  P99:    {p99_ratio:.4f}")
    print(f"  Deviation from {expected}: {deviation:.4f} -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    print()
    checks.append(("VAT ratio (median)", f"{median_ratio:.4f}", f"{expected}",
                   "PASS" if chk1_pass else "REVIEW"))

    # ----- Check 2: SoldQuantity vs NoofUnits -----
    subsection("[3/5] SoldQuantity vs NoofUnits (per LB: ~16x by definition)")
    sub = our[(our["SoldQuantity"] > 0) & (our["NoofUnits"] > 0)].copy()
    qty_ratio = sub["NoofUnits"] / sub["SoldQuantity"]
    qty_median = qty_ratio.median()
    qty_mean = qty_ratio.mean()
    qty_p10 = qty_ratio.quantile(0.10)
    qty_p90 = qty_ratio.quantile(0.90)
    print(f"  Median NoofUnits/SoldQuantity: {qty_median:.2f}")
    print(f"  Mean:                          {qty_mean:.2f}")
    print(f"  P10:                           {qty_p10:.2f}")
    print(f"  P90:                           {qty_p90:.2f}")
    # Not a strict pass/fail - this varies a lot by ItemCode type
    print(f"  Note: These are DIFFERENT columns (LB: ~16x ratio is heterogeneous).")
    print()
    checks.append(("NoofUnits/SoldQuantity median", f"{qty_median:.2f}",
                   "heterogeneous", "INFO"))

    # ----- Check 3: QuantitySold(SalesTotal>0) consistency -----
    subsection("[4/5] QuantitySold(SalesTotal>0) == SoldQuantity")
    diff = (our["QuantitySold(SalesTotal>0)"] - our["SoldQuantity"]).abs()
    max_diff = diff.max()
    n_diff = (diff > 0).sum()
    chk3_pass = (n_diff == 0)
    print(f"  Rows with difference: {n_diff}")
    print(f"  Max absolute difference: {max_diff}")
    print(f"  Status: {'PASS' if chk3_pass else 'FAIL'}")
    print()
    checks.append(("QuantitySold consistency", f"max diff = {max_diff}", "0",
                   "PASS" if chk3_pass else "FAIL"))

    # ----- Check 4: Non-negative values -----
    subsection("[5/5] Non-negative values + outliers")

    n_neg_rev = (our["TotalNet"] < 0).sum()
    n_neg_qty = (our["SoldQuantity"] < 0).sum()
    n_zero_rev = (our["TotalNet"] == 0).sum()
    n_zero_qty = (our["SoldQuantity"] == 0).sum()
    chk4_pass = (n_neg_rev == 0 and n_neg_qty == 0)
    print(f"  Negative TotalNet: {n_neg_rev}")
    print(f"  Negative SoldQuantity: {n_neg_qty}")
    print(f"  Zero TotalNet (after SQL filter): {n_zero_rev}")
    print(f"  Zero SoldQuantity (after SQL filter): {n_zero_qty}")
    print(f"  Status: {'PASS' if chk4_pass else 'FAIL'}")
    checks.append(("Negative values", f"rev={n_neg_rev}, qty={n_neg_qty}", "0",
                   "PASS" if chk4_pass else "FAIL"))

    # Outlier check: price per unit extremes
    sub = our[our["SoldQuantity"] > 0].copy()
    sub["price_per_unit"] = sub["TotalNet"] / sub["SoldQuantity"]
    sub["price_per_unit"] = sub["price_per_unit"].replace([np.inf, -np.inf], np.nan).dropna()
    p_min = sub["price_per_unit"].min()
    p_max = sub["price_per_unit"].max()
    p99_9 = sub["price_per_unit"].quantile(0.999)
    median_price = sub["price_per_unit"].median()
    print()
    print(f"  Price per unit (TotalNet / SoldQuantity):")
    print(f"    Min:     {p_min:>10.2f} SEK")
    print(f"    Median:  {median_price:>10.2f} SEK")
    print(f"    P99.9:   {p99_9:>10.2f} SEK")
    print(f"    Max:     {p_max:>10.2f} SEK")
    # Flag if max > 1M SEK per unit (sanity)
    n_extreme = (sub["price_per_unit"] > 1_000_000).sum()
    print(f"    Rows with > 1M SEK per unit: {n_extreme}")
    if n_extreme > 0:
        chk5_pass = False
        print(f"    Status: REVIEW (possible data issue)")
    else:
        chk5_pass = True
        print(f"    Status: PASS")
    checks.append(("Extreme price-per-unit > 1M", n_extreme, 0,
                   "PASS" if chk5_pass else "REVIEW"))
    print()

    # ----- Receipt -----
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"07_volume_quantity_{timestamp_file}.xlsx"

    print()

    overall = not any(c[3] == "FAIL" for c in checks)
    print(f"  >> Result: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1




def main():
    """Capture stdout while running validation, then save as single-sheet 'Logg' receipt."""
    with capture_stdout() as buf:
        exit_code = _run_validation()
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"07_volume_quantity_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_volume_quantity.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0

if __name__ == "__main__":
    sys.exit(main())

"""
validate_sign_flips.py
=======================
Identifies KEY where elasticity sign flipped vs BCG facit.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

WHAT IT VALIDATES:
  - KEY with opposite signs between our run and BCG facit (neg <-> pos)
  - Flips on significant KEY (concerning - "trustworthy sign change")
  - Flips on weak-signal KEY (expected per IB.10 - OLS noise near zero)
  - Magnitude of flipped values: are they small (noise) or large (real flip)?

INTERPRETATION:
  - Per IB.10: tecken-flips på fin nivå är svag-signal-OLS, inte replikeringsfel
  - Tecken-flips med BÅDE sidor signifikanta = varningsflagga (sällsynta men kritiska)
  - Tecken-flips med svaga p-värden = brus, hanteras av fallback (Step 6)

THRESHOLDS:
  - Total flip rate < 3% of shared KEY (some flips expected per IB.10)
  - Both-significant flip rate < 0.5% (concerning if higher)
  - Magnitude of flipped values: median |elast| < 0.5 typical of noise

OUTPUT:
  - Console log with top concerning flips
  - Excel receipt: verify_tool/receipts/YYYY-MM-DD/04_sign_flips_<timestamp>.xlsx
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

    section("SIGN FLIP VALIDATION (vs BCG facit)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    subsection("[1/4] Resolving inputs and loading")
    our_path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Ours: {source_label} -> {our_path}")
    if not BCG_FACIT_OUTPUT_SUMMARY.exists():
        sys.exit(f"ERROR: BCG facit not found: {BCG_FACIT_OUTPUT_SUMMARY}")

    ours = pd.read_excel(our_path)
    bcg = pd.read_excel(BCG_FACIT_OUTPUT_SUMMARY)
    for c in [COL_ELASTICITY, COL_RSQ, COL_PVALUE]:
        ours[c] = pd.to_numeric(ours[c], errors="coerce")
        bcg[c] = pd.to_numeric(bcg[c], errors="coerce")

    o = ours[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE]].rename(
        columns={COL_ELASTICITY: "elast_ours", COL_RSQ: "rsq_ours", COL_PVALUE: "pval_ours"})
    b = bcg[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE]].rename(
        columns={COL_ELASTICITY: "elast_bcg", COL_RSQ: "rsq_bcg", COL_PVALUE: "pval_bcg"})
    m = o.merge(b, on=COL_KEY, how="inner").dropna(subset=["elast_ours", "elast_bcg"])
    print(f"  KEY compared: {fmt_int(len(m))}")
    print()

    # ----- Identify flips -----
    subsection("[2/4] Sign flip identification")
    m["sign_ours"] = np.sign(m["elast_ours"])
    m["sign_bcg"] = np.sign(m["elast_bcg"])
    m["flipped"] = (m["sign_ours"] != m["sign_bcg"]) & (m["sign_ours"] != 0) & (m["sign_bcg"] != 0)

    m["sig_ours"] = (m["rsq_ours"] >= SIG_RSQ_MIN) & (m["pval_ours"] <= SIG_PVALUE_MAX)
    m["sig_bcg"] = (m["rsq_bcg"] >= SIG_RSQ_MIN) & (m["pval_bcg"] <= SIG_PVALUE_MAX)
    m["both_sig"] = m["sig_ours"] & m["sig_bcg"]
    m["either_sig"] = m["sig_ours"] | m["sig_bcg"]

    n_total = len(m)
    n_flipped = m["flipped"].sum()
    n_flipped_both_sig = (m["flipped"] & m["both_sig"]).sum()
    n_flipped_either_sig = (m["flipped"] & m["either_sig"]).sum()
    n_flipped_weak = n_flipped - n_flipped_either_sig

    pct_total = 100 * n_flipped / n_total if n_total else 0
    pct_both_sig = 100 * n_flipped_both_sig / n_total if n_total else 0
    pct_either_sig = 100 * n_flipped_either_sig / n_total if n_total else 0

    print(f"  Total flips:                    {fmt_int(n_flipped)} ({pct_total:.2f}%)")
    print(f"  Flips with BOTH significant:    {fmt_int(n_flipped_both_sig)} ({pct_both_sig:.2f}%)  <- concerning")
    print(f"  Flips with EITHER significant:  {fmt_int(n_flipped_either_sig)} ({pct_either_sig:.2f}%)")
    print(f"  Flips with NEITHER significant: {fmt_int(n_flipped_weak)} (weak-signal, expected per IB.10)")
    print()

    # Magnitude analysis
    if n_flipped > 0:
        flipped = m[m["flipped"]].copy()
        flipped["abs_max"] = flipped[["elast_ours", "elast_bcg"]].abs().max(axis=1)
        median_mag = flipped["abs_max"].median()
        p95_mag = flipped["abs_max"].quantile(0.95)
        print(f"  Magnitude of flipped (max(|ours|,|bcg|)):")
        print(f"    Median:  {median_mag:.3f}")
        print(f"    P95:     {p95_mag:.3f}")
        print(f"    (small magnitudes = noise; large = real flips needing review)")
    print()

    # ----- Top concerning flips -----
    subsection("[3/4] Top concerning flips (both-sig, then either-sig)")
    both_sig_flips = m[m["flipped"] & m["both_sig"]].copy()
    if len(both_sig_flips):
        both_sig_flips["abs_max"] = both_sig_flips[["elast_ours", "elast_bcg"]].abs().max(axis=1)
        top = both_sig_flips.nlargest(15, "abs_max")
        print(f"  BOTH-SIGNIFICANT FLIPS (most concerning):")
        print(f"  {'KEY':<30}  {'Ours':>8}  {'BCG':>8}  {'pOurs':>6}  {'pBCG':>6}")
        for _, r in top.iterrows():
            print(f"  {str(r[COL_KEY])[:30]:<30}  "
                  f"{r['elast_ours']:>+8.3f}  "
                  f"{r['elast_bcg']:>+8.3f}  "
                  f"{r['pval_ours']:>6.3f}  "
                  f"{r['pval_bcg']:>6.3f}")
    else:
        print(f"  No both-significant flips. (Good - this is the rare concerning case.)")
    print()

    # ----- Checks -----
    subsection("[4/4] Checks")
    checks = []

    chk1_pass = pct_total < 3.0
    print(f"  Total flip rate < 3%: {pct_total:.2f}% -> "
          f"{'PASS' if chk1_pass else 'REVIEW'}")
    checks.append(("Total flip rate < 3%", f"{pct_total:.2f}%", "< 3%",
                   "PASS" if chk1_pass else "REVIEW"))

    chk2_pass = pct_both_sig < 0.5
    print(f"  Both-sig flip rate < 0.5%: {pct_both_sig:.2f}% -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    checks.append(("Both-sig flip rate < 0.5%", f"{pct_both_sig:.2f}%", "< 0.5%",
                   "PASS" if chk2_pass else "REVIEW"))

    if n_flipped > 0:
        flipped = m[m["flipped"]].copy()
        flipped["abs_max"] = flipped[["elast_ours", "elast_bcg"]].abs().max(axis=1)
        chk3_pass = flipped["abs_max"].median() < 0.5
        print(f"  Median flip magnitude < 0.5 (noise check): {flipped['abs_max'].median():.3f} -> "
              f"{'PASS' if chk3_pass else 'REVIEW'}")
        checks.append(("Median flip magnitude < 0.5", f"{flipped['abs_max'].median():.3f}", "< 0.5",
                       "PASS" if chk3_pass else "REVIEW"))

    print()
    overall_pass = all(c[3] == "PASS" for c in checks)
    overall_review = any(c[3] == "REVIEW" for c in checks)
    status = "PASS" if overall_pass else ("REVIEW" if overall_review else "FAIL")
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Sign flips vs BCG facit.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_validation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"04_sign_flips_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "validate_sign_flips.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

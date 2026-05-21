"""
compare_to_facit.py
-------------------
Phase 7: validate our Azure model run against BCG's frozen facit.

Compares two output_summary.xlsx files on three layers, coarse to fine:
    1. Population  - which KEY groups exist in each, overlap, and uniques.
    2. Columns     - which columns match, which differ.
    3. KPI         - the regular-price elasticity per group, compared on the
                     groups present in BOTH files: strict match, tolerant match,
                     diff distribution, and correlation.

Design:
    - Read-only on both files. Writes nothing, changes nothing.
    - No raw-data dumps; prints a structured, token-light report.
    - STRICT and TOLERANT thresholds are constants at the top.
    - Guards against the elasticity column being read as text (Swedish decimal
      comma) instead of a number, and flags it if so.

Run locally on Windows (no VM needed):
    python compare_to_facit.py

Developer: Jens Palmo, with AI advisor.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# --- Configuration -------------------------------------------------------
# Adjust these two paths only if the files move.
OURS_PATH = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models"
    r"\output\azure_run_model\output_summary.xlsx"
)
FACIT_PATH = Path(
    r"C:\Projekt\BCG\Elasticity\Product_Cluster\output\model\output_summary.xlsx"
)

KEY_COL = "KEY"
KPI_COL = "ELASTICITY_Regular_Price_fwbw_max_6"

# A group "matches" strictly if |ours - facit| <= STRICT_TOL.
STRICT_TOL = 0.001
# A group "matches" tolerantly if the relative difference <= TOLERANT_REL (1%).
TOLERANT_REL = 0.01
# -------------------------------------------------------------------------


def load(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        print(f"ERROR: {label} file not found:\n  {path}")
        sys.exit(1)
    df = pd.read_excel(path)
    print(f"Loaded {label}: {path.name}  ->  {df.shape[0]} rows, {df.shape[1]} cols")
    return df


def check_kpi_numeric(df: pd.DataFrame, label: str) -> None:
    """Warn if the KPI column came in as text (e.g. Swedish decimal comma)."""
    if KPI_COL not in df.columns:
        print(f"  WARNING: {label} has no column '{KPI_COL}'")
        return
    if not pd.api.types.is_numeric_dtype(df[KPI_COL]):
        sample = df[KPI_COL].dropna().astype(str).head(3).tolist()
        print(f"  WARNING: {label} '{KPI_COL}' is not numeric (sample: {sample}).")
        print("           Likely text with comma decimals. Attempting conversion.")
        df[KPI_COL] = (
            df[KPI_COL].astype(str).str.replace(",", ".", regex=False)
        )
        df[KPI_COL] = pd.to_numeric(df[KPI_COL], errors="coerce")


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    section("LOADING")
    ours = load(OURS_PATH, "OURS (Azure)")
    facit = load(FACIT_PATH, "FACIT (BCG)")

    check_kpi_numeric(ours, "OURS")
    check_kpi_numeric(facit, "FACIT")

    # --- Layer 1: population ---------------------------------------------
    section("1. POPULATION (KEY groups)")
    if KEY_COL not in ours.columns or KEY_COL not in facit.columns:
        print(f"ERROR: '{KEY_COL}' missing in one of the files.")
        print(f"  OURS cols : {ours.columns.to_list()}")
        print(f"  FACIT cols: {facit.columns.to_list()}")
        return 1

    ours_keys = set(ours[KEY_COL])
    facit_keys = set(facit[KEY_COL])
    common = ours_keys & facit_keys
    only_ours = ours_keys - facit_keys
    only_facit = facit_keys - ours_keys

    print(f"  OURS groups : {len(ours_keys)}")
    print(f"  FACIT groups: {len(facit_keys)}")
    print(f"  in BOTH     : {len(common)}")
    print(f"  only OURS   : {len(only_ours)}")
    print(f"  only FACIT  : {len(only_facit)}")
    if only_ours:
        print(f"    e.g. only ours : {sorted(only_ours)[:5]}")
    if only_facit:
        print(f"    e.g. only facit: {sorted(only_facit)[:5]}")

    # --- Layer 2: columns -------------------------------------------------
    section("2. COLUMNS")
    ours_cols = set(ours.columns)
    facit_cols = set(facit.columns)
    print(f"  shared columns   : {sorted(ours_cols & facit_cols)}")
    if ours_cols - facit_cols:
        print(f"  only in OURS     : {sorted(ours_cols - facit_cols)}")
    if facit_cols - ours_cols:
        print(f"  only in FACIT    : {sorted(facit_cols - ours_cols)}")

    # --- Layer 3: KPI on common groups -----------------------------------
    section(f"3. KPI: {KPI_COL} (groups in BOTH)")
    if not common:
        print("  No overlapping groups; cannot compare KPI.")
        return 0

    o = ours[[KEY_COL, KPI_COL]].rename(columns={KPI_COL: "ours"})
    f = facit[[KEY_COL, KPI_COL]].rename(columns={KPI_COL: "facit"})
    m = o.merge(f, on=KEY_COL, how="inner").dropna(subset=["ours", "facit"])
    n = len(m)
    print(f"  comparable groups (both non-null): {n}")
    if n == 0:
        return 0

    m["abs_diff"] = (m["ours"] - m["facit"]).abs()
    # Relative diff guarded against divide-by-zero.
    denom = m["facit"].abs().replace(0, np.nan)
    m["rel_diff"] = (m["abs_diff"] / denom)

    strict_ok = (m["abs_diff"] <= STRICT_TOL).sum()
    tolerant_ok = (m["rel_diff"] <= TOLERANT_REL).sum()

    print(f"\n  STRICT  match (|diff| <= {STRICT_TOL}):        "
          f"{strict_ok}/{n}  ({100*strict_ok/n:.1f}%)")
    print(f"  TOLERANT match (rel diff <= {TOLERANT_REL:.0%}):     "
          f"{tolerant_ok}/{n}  ({100*tolerant_ok/n:.1f}%)")

    print("\n  Absolute diff distribution:")
    for q in [0.50, 0.90, 0.99, 1.00]:
        print(f"    p{int(q*100):>3}: {m['abs_diff'].quantile(q):.6f}")
    print(f"    mean: {m['abs_diff'].mean():.6f}   max: {m['abs_diff'].max():.6f}")

    corr = m["ours"].corr(m["facit"])
    print(f"\n  Pearson correlation ours vs facit: {corr:.6f}")

    worst = m.nlargest(5, "abs_diff")[[KEY_COL, "ours", "facit", "abs_diff"]]
    print("\n  5 largest absolute deviations:")
    for _, r in worst.iterrows():
        print(f"    {r[KEY_COL]:<24} ours={r['ours']:>10.4f} "
              f"facit={r['facit']:>10.4f}  diff={r['abs_diff']:.4f}")

    # --- Verdict ----------------------------------------------------------
    section("VERDICT")
    if strict_ok == n:
        print("  Bit-for-bit replication: all groups match strictly.")
    elif tolerant_ok / n >= 0.95 and corr >= 0.99:
        print("  Faithful replication: tolerant match high and correlation ~1.")
        print("  Small diffs likely numeric/version noise, not logic differences.")
    else:
        print("  Material differences present. Inspect the largest deviations and")
        print("  population gaps above before trusting the replication.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

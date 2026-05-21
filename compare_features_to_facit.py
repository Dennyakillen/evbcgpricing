"""
compare_features_to_facit.py
----------------------------
Validate our feature_selection output against BCG's frozen facit, on three
layers (most to least meaningful):
    1. Feature choice  - did we select the same features per group? This is
                         feature_selection's real output (the 'Variables' column).
    2. Elasticity      - does ELASTICITY_Regular_Price_fwbw_max_6 match facit?
    3. Adj R2          - numeric supporting check.

We deliberately do NOT diff the per-combination all_x_for_models.csv bit-for-bit;
small numeric noise in non-selected combinations does not change the outcome and
chasing it would be over-engineering. The selected features (+ elasticity) are
what feed the model step, so they are what we validate.

Read-only on both files. No raw-data dumps; structured, token-light report.

Run locally on Windows (no VM needed):
    python compare_features_to_facit.py

Developer: Jens Palmo, with AI advisor.
"""

import sys
import ast
from pathlib import Path
import pandas as pd
import numpy as np

# --- Configuration -------------------------------------------------------
OURS_PATH = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models"
    r"\output\azure_run_automl\results\finalized_x_for_models.csv"
)
FACIT_PATH = Path(
    r"C:\Projekt\BCG\Elasticity\Product_Cluster\output\model\automl\results"
    r"\finalized_x_for_models.csv"
)

KEY_COL = "KEY"
VARS_COL = "Variables"
KPI_COL = "ELASTICITY_Regular_Price_fwbw_max_6"
R2_COL = "Adj R2"

STRICT_TOL = 0.001        # |diff| for a strict elasticity match
TOLERANT_REL = 0.01       # relative diff for a tolerant elasticity match
# -------------------------------------------------------------------------


def load(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        print(f"ERROR: {label} file not found:\n  {path}")
        sys.exit(1)
    df = pd.read_csv(path)
    print(f"Loaded {label}: {df.shape[0]} rows, {df.shape[1]} cols")
    return df


def parse_varset(val):
    """The Variables column is a string like "['a', 'b', 'CONST']". Parse to a set."""
    if pd.isna(val):
        return frozenset()
    try:
        return frozenset(ast.literal_eval(val))
    except (ValueError, SyntaxError):
        # Fallback: split on commas if it isn't a clean literal list.
        return frozenset(s.strip(" []'\"") for s in str(val).split(","))


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    section("LOADING")
    ours = load(OURS_PATH, "OURS (Azure)")
    facit = load(FACIT_PATH, "FACIT (BCG)")

    for col in (KEY_COL, VARS_COL):
        if col not in ours.columns or col not in facit.columns:
            print(f"ERROR: column '{col}' missing in one file.")
            return 1

    # --- Layer 0: population ---------------------------------------------
    section("0. POPULATION (KEY groups)")
    ok, fk = set(ours[KEY_COL]), set(facit[KEY_COL])
    common = ok & fk
    print(f"  OURS groups : {len(ok)}")
    print(f"  FACIT groups: {len(fk)}")
    print(f"  in BOTH     : {len(common)}")
    if ok - fk:
        print(f"  only OURS   : {len(ok - fk)}  e.g. {sorted(ok - fk)[:5]}")
    if fk - ok:
        print(f"  only FACIT  : {len(fk - ok)}  e.g. {sorted(fk - ok)[:5]}")
    if not common:
        print("  No overlap; cannot compare.")
        return 0

    o = ours.set_index(KEY_COL)
    f = facit.set_index(KEY_COL)
    keys = sorted(common)

    # --- Layer 1: feature choice -----------------------------------------
    section("1. FEATURE CHOICE (Variables set per group)")
    identical = 0
    diffs = []
    for k in keys:
        os_ = parse_varset(o.loc[k, VARS_COL])
        fs_ = parse_varset(f.loc[k, VARS_COL])
        if os_ == fs_:
            identical += 1
        else:
            diffs.append((k, fs_ - os_, os_ - fs_))
    n = len(keys)
    print(f"  identical feature set: {identical}/{n}  ({100*identical/n:.1f}%)")
    if diffs:
        print(f"  groups with differing feature set: {len(diffs)}")
        print("  first 5 differences (facit_only | ours_only):")
        for k, fonly, oonly in diffs[:5]:
            print(f"    {k:<24} facit_only={sorted(fonly)}  ours_only={sorted(oonly)}")

    # --- Layer 2: elasticity ---------------------------------------------
    section(f"2. ELASTICITY: {KPI_COL}")
    if KPI_COL in o.columns and KPI_COL in f.columns:
        m = pd.DataFrame({
            "ours": pd.to_numeric(o.loc[keys, KPI_COL], errors="coerce"),
            "facit": pd.to_numeric(f.loc[keys, KPI_COL], errors="coerce"),
        }).dropna()
        if len(m):
            d = (m["ours"] - m["facit"]).abs()
            rel = d / m["facit"].abs().replace(0, np.nan)
            strict = (d <= STRICT_TOL).sum()
            tol = (rel <= TOLERANT_REL).sum()
            print(f"  comparable groups: {len(m)}")
            print(f"  STRICT  (|diff|<={STRICT_TOL}):   {strict}/{len(m)}  ({100*strict/len(m):.1f}%)")
            print(f"  TOLERANT (rel<={TOLERANT_REL:.0%}):    {tol}/{len(m)}  ({100*tol/len(m):.1f}%)")
            print(f"  max abs diff: {d.max():.6f}   corr: {m['ours'].corr(m['facit']):.6f}")
    else:
        print("  KPI column not present in both; skipping.")

    # --- Layer 3: Adj R2 -------------------------------------------------
    section(f"3. {R2_COL} (supporting)")
    if R2_COL in o.columns and R2_COL in f.columns:
        m = pd.DataFrame({
            "ours": pd.to_numeric(o.loc[keys, R2_COL], errors="coerce"),
            "facit": pd.to_numeric(f.loc[keys, R2_COL], errors="coerce"),
        }).dropna()
        if len(m):
            d = (m["ours"] - m["facit"]).abs()
            print(f"  comparable groups: {len(m)}   max abs diff: {d.max():.6f}   "
                  f"corr: {m['ours'].corr(m['facit']):.6f}")
    else:
        print("  Adj R2 not present in both; skipping.")

    # --- Verdict ----------------------------------------------------------
    section("VERDICT")
    if identical == n:
        print("  Feature selection fully replicated: identical feature sets on all groups.")
    elif identical / n >= 0.95:
        print(f"  Feature selection faithfully replicated: {100*identical/n:.1f}% identical sets.")
        print("  Inspect the listed differences to judge if they are material.")
    else:
        print("  Material feature-selection differences. Inspect before trusting replication.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

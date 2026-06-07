"""
verify_fallback.py
=====================================================================
Validates that OUR step-6 run reproduces BCG's facit, proving we own
the F1-F7 weave end-to-end. Compares in layers (KARNPRINCIPER 8.3:
population -> columns -> KPI; strict + tolerant + correlation), and
REPORTS deviations rather than returning a binary PASS/FAIL
(KARNPRINCIPER: "fail-fast-grindar som RAPPORTERAR slar binar
PASS/FAIL").

What it compares (per ProductKey, the dv8 key):
  Layer 1  Population  : row count, ProductKey overlap (only_ours / only_facit)
  Layer 2  Level mix   : elasticity_level distribution (F1-F7 counts) ours vs facit
  Layer 3  Elasticity  : final_elasticity correlation + median abs diff on shared keys
  Layer 4  Level agree : per-key elasticity_level agreement rate

dv8 columns (from Fall_Back_Logic.py creating_one_df, verbatim):
  ProductKey, ProductDescription, service, Clusters, SiteCode,
  TotalNet, year ending 2025 revenue, PVALUE_PRICE, RSQ,
  final_elasticity, elasticity_level, Product Granularity,
  site Granularity, Weighted Elasticity

Note (verified in source): PVALUE_PRICE / RSQ are populated ONLY for
F1/F2 rows; None elsewhere by design - so blanks there are correct,
not a defect. We therefore do not validate p-value/RSQ population.

Developer: Jens Palmo
Run in: the project venv (.venv) on Windows, via:
    python -m  ... see delivery notes  (AppLocker-clean: python -m)
Usage:
    python verify_fallback.py --ours  "<path to OUR Final_Fallback_Data_*.xlsx>" \
                              --facit "<path to BCG Final_Fallback_Data_20250930_091648.xlsx>"
If run with no args, it uses the DEFAULTS below (edit to taste).
=====================================================================
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --- Defaults (override with --ours / --facit) -----------------------
DEFAULT_OURS = r"C:\Projekt\BCG\_step6_run\02. Elasticity\6. Fall Back Logic\output_data"
DEFAULT_FACIT = (
    r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG"
    r"\BCG_orginal_V2_New\02. Elasticity\6. Fall Back Logic\output_data"
    r"\Final_Fallback_Data_20250930_091648.xlsx"
)

# A dv8 row is made unique by ProductKey + SiteCode + Clusters (the grain that
# dv1/dv2 in creating_one_df merge on). Joining on ProductKey alone explodes into
# a cartesian self-join (same key on many site/cluster rows), which falsely
# cross-pairs distinct elasticities and deflates correlation / level agreement.
KEY = ["ProductKey", "SiteCode", "Clusters"]
PKEY = "ProductKey"  # kept for population reporting
ELAS = "final_elasticity"
LEVEL = "elasticity_level"

LEVEL_LABELS = [
    "F1 site level",
    "F2 bundle level",
    "F3 cluster level",
    "F4 bundle across clusters",
    "F5 product across clusters",
    "F6 service within cluster",
    "F7 service across clusters",
]


def _resolve_ours(ours_arg: str) -> Path:
    """Accept either a file or a folder; if folder, pick newest Final_Fallback_Data_*.xlsx."""
    p = Path(ours_arg)
    if p.is_dir():
        candidates = sorted(
            p.glob("Final_Fallback_Data_*.xlsx"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            sys.exit(f"[FATAL] No Final_Fallback_Data_*.xlsx found in folder: {p}")
        chosen = candidates[0]
        print(f"[info] Folder given for --ours; using newest: {chosen.name}")
        return chosen
    if not p.exists():
        sys.exit(f"[FATAL] --ours file not found: {p}")
    return p


def _load(path: Path, label: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    missing = [c for c in KEY if c not in df.columns]
    if missing:
        sys.exit(f"[FATAL] {label}: key column(s) {missing} missing. Columns: {list(df.columns)}")
    for c in KEY:
        df[c] = df[c].astype(str)
    print(f"[info] {label}: {len(df):,} rows, {df.columns.size} cols  <- {path.name}")
    return df


def _section(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify step-6 fallback output against BCG facit.")
    ap.add_argument("--ours", default=DEFAULT_OURS, help="Our Final_Fallback_Data_*.xlsx (file or folder).")
    ap.add_argument("--facit", default=DEFAULT_FACIT, help="BCG facit Final_Fallback_Data_*.xlsx (file).")
    args = ap.parse_args()

    ours_path = _resolve_ours(args.ours)
    facit_path = Path(args.facit)
    if not facit_path.exists():
        sys.exit(f"[FATAL] --facit file not found: {facit_path}")

    ours = _load(ours_path, "OURS ")
    facit = _load(facit_path, "FACIT")

    # ---------------------------------------------------------------
    # Layer 1 - Population
    # ---------------------------------------------------------------
    _section("LAYER 1 - POPULATION")
    ours_rowkeys = set(map(tuple, ours[KEY].itertuples(index=False, name=None)))
    facit_rowkeys = set(map(tuple, facit[KEY].itertuples(index=False, name=None)))
    only_ours = ours_rowkeys - facit_rowkeys
    only_facit = facit_rowkeys - ours_rowkeys
    shared = ours_rowkeys & facit_rowkeys
    print(f"row grain = {KEY}")
    print(f"rows ours / facit            : {len(ours):,} / {len(facit):,}")
    print(f"distinct row-keys ours/facit : {len(ours_rowkeys):,} / {len(facit_rowkeys):,}")
    print(f"distinct ProductKey ours/fac : {ours[PKEY].nunique():,} / {facit[PKEY].nunique():,}")
    print(f"shared row-keys              : {len(shared):,}")
    print(f"only in ours                 : {len(only_ours):,}")
    print(f"only in facit                : {len(only_facit):,}")
    if only_ours:
        print(f"  sample only_ours           : {sorted(list(only_ours))[:5]}")
    if only_facit:
        print(f"  sample only_facit          : {sorted(list(only_facit))[:5]}")

    # ---------------------------------------------------------------
    # Layer 2 - elasticity_level distribution (F1-F7)
    # ---------------------------------------------------------------
    _section("LAYER 2 - ELASTICITY_LEVEL DISTRIBUTION (F1-F7)")
    if LEVEL not in ours.columns or LEVEL not in facit.columns:
        print(f"[warn] '{LEVEL}' missing in one frame - skipping level distribution.")
    else:
        o = ours[LEVEL].value_counts(dropna=False)
        f = facit[LEVEL].value_counts(dropna=False)
        dist = pd.DataFrame({"ours": o, "facit": f}).fillna(0).astype(int)
        dist["diff"] = dist["ours"] - dist["facit"]
        # order by known labels first, then any extras (NaN etc.)
        ordered = [l for l in LEVEL_LABELS if l in dist.index] + \
                  [i for i in dist.index if i not in LEVEL_LABELS]
        print(dist.loc[ordered].to_string())
        total_diff = int(dist["diff"].abs().sum())
        print(f"\nsum |diff| across levels: {total_diff}")

    # ---------------------------------------------------------------
    # Layer 3 - final_elasticity on shared keys
    # ---------------------------------------------------------------
    _section("LAYER 3 - FINAL_ELASTICITY (shared keys)")
    if ELAS not in ours.columns or ELAS not in facit.columns:
        print(f"[warn] '{ELAS}' missing in one frame - skipping.")
        merged = None
    else:
        cols = KEY + [ELAS, LEVEL]
        o = ours[cols].drop_duplicates(subset=KEY)
        f = facit[cols].drop_duplicates(subset=KEY)
        n_dup_ours = len(ours) - len(o)
        n_dup_facit = len(facit) - len(f)
        if n_dup_ours or n_dup_facit:
            print(f"[note] dropped duplicate row-keys before merge: ours {n_dup_ours}, facit {n_dup_facit}")
        m = o.merge(f, on=KEY, how="inner", suffixes=("_ours", "_facit"))
        m["abs_diff"] = (m[f"{ELAS}_ours"] - m[f"{ELAS}_facit"]).abs()
        both = m.dropna(subset=[f"{ELAS}_ours", f"{ELAS}_facit"])
        if len(both) >= 2:
            corr = both[f"{ELAS}_ours"].corr(both[f"{ELAS}_facit"])
        else:
            corr = float("nan")
        print(f"rows compared (row grain): {len(m):,}")
        print(f"both elasticities present: {len(both):,}")
        print(f"correlation (ours,facit) : {corr:.6f}")
        print(f"median |diff|            : {both['abs_diff'].median():.6f}")
        print(f"mean   |diff|            : {both['abs_diff'].mean():.6f}")
        print(f"max    |diff|            : {both['abs_diff'].max():.6f}")
        print(f"rows with |diff| > 0.01  : {(both['abs_diff'] > 0.01).sum():,}")
        worst = both.sort_values("abs_diff", ascending=False).head(10)
        print("\nworst 10 by |diff|:")
        print(worst[KEY + [f"{ELAS}_ours", f"{ELAS}_facit", "abs_diff"]].to_string(index=False))
        merged = m

    # ---------------------------------------------------------------
    # Layer 4 - per-key elasticity_level agreement
    # ---------------------------------------------------------------
    _section("LAYER 4 - PER-ROW LEVEL AGREEMENT")
    if merged is not None and f"{LEVEL}_ours" in merged.columns:
        lo = merged[f"{LEVEL}_ours"].astype(str)
        lf = merged[f"{LEVEL}_facit"].astype(str)
        agree = (lo == lf)
        rate = agree.mean() if len(agree) else float("nan")
        print(f"rows with matching level : {agree.sum():,} / {len(agree):,}  ({rate:.2%})")
        disagree = merged[~agree]
        if len(disagree):
            mix = (
                disagree.groupby([f"{LEVEL}_facit", f"{LEVEL}_ours"])
                .size()
                .reset_index(name="n")
                .sort_values("n", ascending=False)
                .head(15)
            )
            print("\ntop level disagreements (facit -> ours):")
            print(mix.to_string(index=False))
    else:
        print("[warn] level columns unavailable after merge - skipping.")

    # ---------------------------------------------------------------
    # Verdict (reporting, not gatekeeping)
    # ---------------------------------------------------------------
    _section("VERDICT (reporting gate - judge the deltas, not a threshold)")
    print("Replication is faithful when, on shared keys:")
    print("  - population overlap is ~complete (only_ours / only_facit ~ 0)")
    print("  - elasticity_level distribution matches (sum |diff| small)")
    print("  - final_elasticity correlation ~ 1.0, median |diff| ~ 0")
    print("  - per-key level agreement ~ 100%")
    print("\nResidual variance with no top-line price impact is expected and")
    print("uncontroversial (KARNPRINCIPER). A diff that would flip a price")
    print("decision is the only kind that matters - inspect Layer 3 worst-10.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

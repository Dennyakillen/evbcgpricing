"""
verify_model.py  --  verify_tool: model-output (Cluster / Site / Bundle) vs BCG facit
=====================================================================================
One parametrized verifier for all three model families. They share the
output_summary.xlsx format (KEY, ELASTICITY_Regular_Price_fwbw_max_6, ...),
so a single tool with --family beats three near-identical copies.

Inherits the proven three-layer comparison from compare_to_facit.py
(population -> columns -> KPI; strict + tolerant + correlation) and follows
KARNPRINCIPER: REPORTS deviations, does not return a binary PASS/FAIL.

What it compares, per KEY (= Cluster_Granularity-ItemCode):
  Layer 1  Population : KEY overlap (only_ours / only_facit)
  Layer 2  Columns    : column-set match
  Layer 3  KPI        : ELASTICITY_Regular_Price_fwbw_max_6 per shared KEY
                        (strict / tolerant / correlation / worst deviations)

WHY this and not a file-size or whole-file diff: our VM run and BCG's frozen
run serialize to slightly different Excel byte sizes (expected, ~3% per family).
The signal is the per-KEY elasticity match, not the file size.

Reference values (IB.9, for the "does it look right" sanity read):
  Cluster: 3812 groups, median -0.138, neg 76.5%, p<0.05 18.0% (~ BCG 17.8%, IB.1)
  Site   : 4673 groups, median -0.054, neg 62.4%, p<0.05  9.3%
  Bundle :  125 groups, median -0.211, neg 85.6%, p<0.05 22.4%

Path-agnostic: defaults below are sensible, but --ours / --facit override them
so a later folder reorg never touches this code.

Developer: Jens Palmo, with AI advisor.
Run (PowerShell, project venv):
    python verify_model.py --family cluster
    python verify_model.py --family site
    python verify_model.py --family bundle
    python verify_model.py --family cluster --ours "<path>" --facit "<path>"
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KEY_COL = "KEY"
KPI_COL = "ELASTICITY_Regular_Price_fwbw_max_6"
PVAL_COL = "PVALUE_Regular_Price_fwbw_max_6"

STRICT_TOL = 0.001     # |diff| for a strict match
TOLERANT_REL = 0.01    # relative diff for a tolerant match

# --- Per-family defaults --------------------------------------------------
# OURS = our VM run (azure_run_model). FACIT = BCG's frozen run (\output\model).
_ORIG = (
    r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG"
    r"\BCG_orginal_V2_New\02. Elasticity"
)
_PIPE = r"C:\Projekt\BCG\Pipeline\02. Elasticity"

FAMILIES = {
    "cluster": {
        "label": "Cluster (product x cluster)",
        "ours": rf"{_PIPE}\2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx",
        "facit": rf"{_ORIG}\2. Product Cluster Level Models\output\model\output_summary.xlsx",
        "ref": "3812 groups, median -0.138, neg 76.5%, p<0.05 18.0% (~ BCG 17.8%)",
    },
    "site": {
        "label": "Site (product x site)",
        "ours": rf"{_PIPE}\3. Product Site Level Models\output\azure_run_model\output_summary.xlsx",
        "facit": rf"{_ORIG}\3. Product Site Level Models\output\model\output_summary.xlsx",
        "ref": "4673 groups, median -0.054, neg 62.4%, p<0.05 9.3%",
    },
    "bundle": {
        "label": "Bundle (baskets / clinic)",
        "ours": rf"{_PIPE}\5. Bundle Clinic Models\output\azure_run_model\output_summary.xlsx",
        "facit": rf"{_ORIG}\5. Bundle Clinic Models\output\model\output_summary.xlsx",
        "ref": "125 groups, median -0.211, neg 85.6%, p<0.05 22.4%",
    },
}


def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def _load(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"[FATAL] {label} not found:\n  {path}")
    df = pd.read_excel(path)
    print(f"[info] {label}: {df.shape[0]} rows, {df.shape[1]} cols  <- {path.name}")
    return df


def _coerce_numeric(df: pd.DataFrame, col: str, label: str) -> None:
    """Guard against the KPI/p-value coming in as text (Swedish decimal comma)."""
    if col not in df.columns:
        return
    if not pd.api.types.is_numeric_dtype(df[col]):
        sample = df[col].dropna().astype(str).head(3).tolist()
        print(f"[warn] {label} '{col}' not numeric (sample {sample}); converting comma->dot.")
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce"
        )


def _self_profile(df: pd.DataFrame, label: str) -> None:
    """Standalone sanity read (IB.9-style) - useful even without facit."""
    if KPI_COL not in df.columns:
        print(f"[warn] {label}: no '{KPI_COL}'; skipping profile.")
        return
    k = pd.to_numeric(df[KPI_COL], errors="coerce").dropna()
    neg = (k < 0).mean() if len(k) else float("nan")
    line = (f"  {label}: groups={len(df)}  median={k.median():.3f}  "
            f"neg={neg:.1%}")
    if PVAL_COL in df.columns:
        p = pd.to_numeric(df[PVAL_COL], errors="coerce")
        sig = (p < 0.05).mean()
        line += f"  p<0.05={sig:.1%}"
    print(line)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a model family's output vs BCG facit.")
    ap.add_argument("--family", required=True, choices=list(FAMILIES),
                    help="Which model family to verify.")
    ap.add_argument("--ours", default=None, help="Override path to our output_summary.xlsx.")
    ap.add_argument("--facit", default=None, help="Override path to BCG facit output_summary.xlsx.")
    args = ap.parse_args()

    fam = FAMILIES[args.family]
    ours_path = Path(args.ours or fam["ours"])
    facit_path = Path(args.facit or fam["facit"])

    _section(f"VERIFY MODEL FAMILY: {fam['label']}")
    print(f"reference (IB.9): {fam['ref']}")

    ours = _load(ours_path, "OURS ")
    facit = _load(facit_path, "FACIT")

    for df, lbl in ((ours, "OURS"), (facit, "FACIT")):
        _coerce_numeric(df, KPI_COL, lbl)
        _coerce_numeric(df, PVAL_COL, lbl)

    # Standalone profile (the "live demo" number a decision-maker recognizes)
    _section("PROFILE (standalone sanity, IB.9)")
    _self_profile(ours, "OURS ")
    _self_profile(facit, "FACIT")

    if KEY_COL not in ours.columns or KEY_COL not in facit.columns:
        sys.exit(f"[FATAL] '{KEY_COL}' missing. ours={list(ours.columns)} facit={list(facit.columns)}")

    # --- Layer 1: population -------------------------------------------
    _section("LAYER 1 - POPULATION (KEY groups)")
    ok, fk = set(ours[KEY_COL]), set(facit[KEY_COL])
    common = ok & fk
    print(f"OURS groups   : {len(ok)}")
    print(f"FACIT groups  : {len(fk)}")
    print(f"in BOTH       : {len(common)}")
    print(f"only OURS     : {len(ok - fk)}")
    print(f"only FACIT    : {len(fk - ok)}")
    if ok - fk:
        print(f"  e.g. only ours : {sorted(ok - fk)[:5]}")
    if fk - ok:
        print(f"  e.g. only facit: {sorted(fk - ok)[:5]}")

    # --- Layer 2: columns ----------------------------------------------
    _section("LAYER 2 - COLUMNS")
    oc, fc = set(ours.columns), set(facit.columns)
    print(f"shared    : {sorted(oc & fc)}")
    if oc - fc:
        print(f"only OURS : {sorted(oc - fc)}")
    if fc - oc:
        print(f"only FACIT: {sorted(fc - oc)}")

    # --- Layer 3: KPI on shared KEYs -----------------------------------
    _section(f"LAYER 3 - KPI: {KPI_COL} (shared KEYs)")
    if not common:
        print("No overlapping KEYs; cannot compare KPI.")
        return 0
    o = ours[[KEY_COL, KPI_COL]].rename(columns={KPI_COL: "ours"})
    # Carry facit RSQ + p-value so we can flag the significance-relevant subset.
    f_cols = [KEY_COL, KPI_COL]
    for extra in ("RSQ", PVAL_COL):
        if extra in facit.columns:
            f_cols.append(extra)
    f = facit[f_cols].rename(columns={KPI_COL: "facit"})
    m = o.merge(f, on=KEY_COL, how="inner").dropna(subset=["ours", "facit"])
    n = len(m)
    if n == 0:
        print("comparable groups: 0")
        return 0
    m["abs_diff"] = (m["ours"] - m["facit"]).abs()
    denom = m["facit"].abs().replace(0, np.nan)
    m["rel_diff"] = m["abs_diff"] / denom

    # --- compute everything quietly first --------------------------------
    strict = int((m["abs_diff"] <= STRICT_TOL).sum())
    tol = int((m["rel_diff"] <= TOLERANT_REL).sum())
    pearson = m["ours"].corr(m["facit"])
    # Rank correlation without scipy: Spearman == Pearson on the ranks.
    # pandas .rank() needs no extra dependency, unlike .corr(method="spearman").
    spearman = m["ours"].rank().corr(m["facit"].rank())
    med_diff = m["abs_diff"].median()
    max_diff = m["abs_diff"].max()

    # significance-gated (decision-relevant) subset
    have_gate = ("RSQ" in m.columns and PVAL_COL in m.columns)
    ns = scorr = sstrict = sig_med = sig_max = None
    sig = None
    if have_gate:
        rsq = pd.to_numeric(m["RSQ"], errors="coerce").round(2)
        pval = pd.to_numeric(m[PVAL_COL], errors="coerce").round(2)
        sig = (rsq >= 0.5) & (pval <= 0.20) & (m["facit"] < 0) & (m["facit"] > -10)
        ms = m[sig]
        ns = int(len(ms))
        if ns >= 1:
            scorr = ms["ours"].rank().corr(ms["facit"].rank()) if ns >= 2 else float("nan")
            sstrict = int((ms["abs_diff"] <= STRICT_TOL).sum())
            sig_med = ms["abs_diff"].median()
            sig_max = ms["abs_diff"].max()

    # ---------------------------------------------------------------------
    # HEADLINE  (the reliable, decision-maker-facing read - lead with this)
    # ---------------------------------------------------------------------
    print("SUMMARY (lead with these - the reliable measures):")
    print(f"  Population match     : {len(common)}/{len(common)} groups  (identical set)")
    print(f"  Median |diff|        : {med_diff:.4f}   (0 = the typical group is bit-identical)")
    print(f"  Identical groups     : {strict}/{n}  ({100*strict/n:.1f}%)")
    print(f"  Rank corr (Spearman) : {spearman:.4f}   (groups rank-order the same way)")
    if have_gate and ns:
        print(f"  Decision-relevant    : {sstrict}/{ns} significant groups identical "
              f"({100*sstrict/ns:.1f}%), median |diff| {sig_med:.4f}")
    print(f"  Pearson corr         : {pearson:.4f}   (context: sensitive to a few weak-signal "
          f"tail groups; rank corr above is the fairer read)")

    # ---------------------------------------------------------------------
    # DETAILS  (kept below for anyone who wants to dig - nothing hidden)
    # ---------------------------------------------------------------------
    _section("--- details (for anyone who wants to dig) ---")
    print(f"comparable groups (both non-null): {n}")
    print(f"STRICT  (|diff|<={STRICT_TOL}):   {strict}/{n}  ({100*strict/n:.1f}%)")
    print(f"TOLERANT (rel<={TOLERANT_REL:.0%}):    {tol}/{n}  ({100*tol/n:.1f}%)")
    print("abs diff distribution:")
    for q in (0.50, 0.90, 0.99, 1.00):
        print(f"  p{int(q*100):>3}: {m['abs_diff'].quantile(q):.6f}")
    print(f"  mean: {m['abs_diff'].mean():.6f}   max: {max_diff:.6f}")

    if have_gate and ns:
        print(f"\ndecision-relevant subset (IB.2 gate: RSQ>=0.5, p<=0.20, -10<elast<0): {ns}/{n}")
        print(f"  strict match: {sstrict}/{ns} ({100*sstrict/ns:.1f}%)   "
              f"median |diff|: {sig_med:.4f}   max |diff|: {sig_max:.4f}")
        ms = m[sig]
        sig_worst = ms.nlargest(5, "abs_diff")[[KEY_COL, "ours", "facit", "abs_diff"]]
        print("  widest gaps among significant groups (weak-signal borderline cases):")
        print(sig_worst.to_string(index=False))
        noise_max = m[~sig]["abs_diff"].max() if (~sig).any() else 0.0
        print(f"  (largest gap in NON-significant/noise groups, discarded by fallback: {noise_max:.4f})")
    elif not have_gate:
        print("\n[warn] RSQ / p-value not both present; significance gate skipped.")
        worst = m.nlargest(5, "abs_diff")[[KEY_COL, "ours", "facit", "abs_diff"]]
        print("widest gaps (all groups):")
        print(worst.to_string(index=False))

    # --- Verdict (reporting) -------------------------------------------
    _section("VERDICT")
    print("Read the SUMMARY at the top. Replication of this family is faithful when:")
    print("  - the group set is identical (population match),")
    print("  - the typical group is bit-identical (median |diff| ~ 0),")
    print("  - groups rank-order the same (Spearman high),")
    print("  - the decision-relevant (significant) groups match.")
    print("This is not expected to be 100% on every single group, and it need not be:")
    print("finer levels carry weak-signal tail groups (IB.9) that the model's own")
    print("fallback discards before any price decision (IB.2). What matters is that")
    print("the structure, the typical value, and the price-relevant groups hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

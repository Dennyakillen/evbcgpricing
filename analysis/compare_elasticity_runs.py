"""
compare_elasticity_runs.py
==========================

Affarsfraga: Kan chefer fatta prisbeslut baserat pa growing-window-korningen
av BCG:s priselasticitetspipeline?

Skriptet besvarar tva separata fragor:

  1. REPLIKATIONS-TROVARDIGHET (vaxande vs BCG facit):
     - Hur manga KEY finns i bada korningar (inner join)
     - Hur skiljer sig elasticitet och p-varde for samma KEY mellan korningarna
     - Hur manga byter tecken pa elasticiteten (affarskritiskt larm)

  2. SANITY-GATE PA VAXANDE KORNING (fristaende):
     - IB.2-gate: hur manga KEY blir signifikanta (RSQ>=0.5 AND PVALUE<=0.2)
     - Distribution av elasticiteter (median, kvartiler, extremer)

Output:
  - Konsol: kort sammanfattningstabell
  - Excel: 3 flikar
      Summary           - hogniva sammanfattning
      Joined_comparison - alla matchade KEY med bada korningars varden
      Significant_only  - KEY som passerar IB.2-gate i vaxande korning

Skriptet ar idempotent och tar inga argument - sokvagarna ar hardkodade till
arkiverade outputs. Justera GROWING_PATH/BCG_PATH om filer flyttas.

Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB),
            assisterad av Claude.
Datum: 2026-06-05
Hor till: FAS F, Etapp F.6 - Cluster-korning pa vaxande fonster
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np


# =====================================================================
# KONFIGURATION
# =====================================================================

# Vaxande korning (just hamtad fran VM)
GROWING_PATH = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity"
    r"\2. Product Cluster Level Models\_archive_growing_2026-04-27"
    r"\output_summary.xlsx"
)

# BCG:s originalfacit (frusen window 2022-07..2025-06, 3812 KEY)
BCG_PATH = Path(
    r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvard AB"
    r"\Datastrategi\BCG\BCG_orginal_V2_New"
    r"\02. Elasticity\2. Product Cluster Level Models"
    r"\output\model\output_summary.xlsx"
)

# Output dit jamforelse-rapporten skrivs
OUTPUT_PATH = GROWING_PATH.parent / "compare_growing_vs_bcg_2026-06-05.xlsx"

# Kolumner i bada outputs
COL_KEY = "KEY"
COL_ELAST = "ELASTICITY_Regular_Price_fwbw_max_6"
COL_PVAL = "PVALUE_Regular_Price_fwbw_max_6"
COL_RSQ = "RSQ"

# IB.2-gate
GATE_RSQ_MIN = 0.5
GATE_PVAL_MAX = 0.2


# =====================================================================
# HJALPARFUNKTIONER
# =====================================================================

def load_output_summary(path: Path, label: str) -> pd.DataFrame:
    """Las output_summary.xlsx och verifiera kolumnstruktur."""
    if not path.exists():
        sys.exit(f"FEL: {label}-filen hittas inte: {path}")
    df = pd.read_excel(path)
    expected_cols = {COL_KEY, COL_ELAST, COL_PVAL, COL_RSQ}
    missing = expected_cols - set(df.columns)
    if missing:
        sys.exit(f"FEL: {label} saknar kolumner: {missing}")
    print(f"  Laddat {label}: {df.shape[0]:,} rader, {df[COL_KEY].nunique():,} unika KEY")
    return df


def apply_ib2_gate(df: pd.DataFrame) -> pd.Series:
    """IB.2: KEY ar signifikant om RSQ>=0.5 AND PVALUE<=0.2."""
    return (df[COL_RSQ] >= GATE_RSQ_MIN) & (df[COL_PVAL] <= GATE_PVAL_MAX)


def fmt_n(n: int, total: int) -> str:
    """Formatera antal med procent av total."""
    pct = 100 * n / total if total else 0
    return f"{n:,} ({pct:.1f}%)"


# =====================================================================
# JAMFORELSE 1: VAXANDE vs BCG (inner join)
# =====================================================================

def build_joined_comparison(growing: pd.DataFrame, bcg: pd.DataFrame) -> pd.DataFrame:
    """Inner join pa KEY, berakna skillnader och flaggor."""
    # Hall bara de kolumner vi behover med tydliga suffix
    g = growing[[COL_KEY, COL_ELAST, COL_PVAL, COL_RSQ]].rename(
        columns={
            COL_ELAST: "elast_growing",
            COL_PVAL: "pval_growing",
            COL_RSQ: "rsq_growing",
        }
    )
    b = bcg[[COL_KEY, COL_ELAST, COL_PVAL, COL_RSQ]].rename(
        columns={
            COL_ELAST: "elast_bcg",
            COL_PVAL: "pval_bcg",
            COL_RSQ: "rsq_bcg",
        }
    )

    joined = g.merge(b, on=COL_KEY, how="inner")

    # Beraknade kolumner
    joined["elast_diff_abs"] = joined["elast_growing"] - joined["elast_bcg"]
    joined["elast_diff_pct"] = np.where(
        joined["elast_bcg"].abs() > 1e-9,
        100 * joined["elast_diff_abs"] / joined["elast_bcg"].abs(),
        np.nan,
    )

    # Tecken-flip: positivt blev negativt eller tvartom
    # (nollor raknas inte som flip)
    joined["sign_flip"] = (
        ((joined["elast_growing"] > 0) & (joined["elast_bcg"] < 0))
        | ((joined["elast_growing"] < 0) & (joined["elast_bcg"] > 0))
    )

    # IB.2-gate i bada korningarna
    joined["sig_growing"] = (joined["rsq_growing"] >= GATE_RSQ_MIN) & (
        joined["pval_growing"] <= GATE_PVAL_MAX
    )
    joined["sig_bcg"] = (joined["rsq_bcg"] >= GATE_RSQ_MIN) & (
        joined["pval_bcg"] <= GATE_PVAL_MAX
    )

    # Sortera pa absolut elasticitet-skillnad fallande (chefen ser storsta forst)
    joined = joined.sort_values("elast_diff_abs", key=lambda s: s.abs(), ascending=False)
    return joined


# =====================================================================
# RAPPORTERING TILL KONSOL
# =====================================================================

def report_console(growing: pd.DataFrame, bcg: pd.DataFrame, joined: pd.DataFrame) -> None:
    n_g = growing.shape[0]
    n_b = bcg.shape[0]
    n_j = joined.shape[0]
    n_only_g = n_g - n_j
    n_only_b = n_b - n_j

    print()
    print("=" * 70)
    print("JAMFORELSE: VAXANDE FONSTER vs BCG ORIGINALFACIT")
    print("=" * 70)
    print()
    print(f"Vaxande korning (2026-04-27):  {n_g:,} KEY")
    print(f"BCG originalfacit (2025-06):   {n_b:,} KEY")
    print(f"Gemensamma KEY (inner join):   {n_j:,}")
    print(f"  - Endast i vaxande:          {n_only_g:,}")
    print(f"  - Endast i BCG:              {n_only_b:,}")
    print()
    print("-" * 70)
    print("IB.2-GATE (RSQ>=0.5 AND PVALUE<=0.2)")
    print("-" * 70)
    sig_g = apply_ib2_gate(growing).sum()
    sig_b = apply_ib2_gate(bcg).sum()
    print(f"Signifikanta i vaxande:        {fmt_n(sig_g, n_g)}")
    print(f"Signifikanta i BCG:            {fmt_n(sig_b, n_b)}")

    if n_j:
        both_sig = (joined["sig_growing"] & joined["sig_bcg"]).sum()
        only_g_sig = (joined["sig_growing"] & ~joined["sig_bcg"]).sum()
        only_b_sig = (~joined["sig_growing"] & joined["sig_bcg"]).sum()
        print(f"  - Bada signifikanta:         {fmt_n(both_sig, n_j)}")
        print(f"  - Bara vaxande signifikant:  {fmt_n(only_g_sig, n_j)}")
        print(f"  - Bara BCG signifikant:      {fmt_n(only_b_sig, n_j)}")
        print()
        print("-" * 70)
        print("ELASTICITETS-SKILLNADER (matchade KEY)")
        print("-" * 70)
        abs_diff = joined["elast_diff_abs"].abs()
        print(f"Median absolut skillnad:       {abs_diff.median():.4f}")
        print(f"Medel absolut skillnad:        {abs_diff.mean():.4f}")
        print(f"Max absolut skillnad:          {abs_diff.max():.4f}")
        for thr in (0.1, 0.25, 0.5, 1.0):
            n = (abs_diff > thr).sum()
            print(f"  > {thr:>4}:                    {fmt_n(n, n_j)}")
        print()
        print("-" * 70)
        print("TECKEN-FLIPPAR (affarskritiska larm)")
        print("-" * 70)
        n_flip = joined["sign_flip"].sum()
        print(f"Antal KEY som bytt tecken:     {fmt_n(n_flip, n_j)}")
        if n_flip:
            # Visa de starkaste fliparna
            flips = joined[joined["sign_flip"]].copy()
            flips["flip_magnitude"] = (
                flips["elast_growing"].abs() + flips["elast_bcg"].abs()
            )
            top_flips = flips.nlargest(5, "flip_magnitude")
            print()
            print("Top 5 starkaste tecken-flippar:")
            print(
                top_flips[
                    [COL_KEY, "elast_bcg", "elast_growing", "pval_growing"]
                ].to_string(index=False)
            )
        print()
        print("-" * 70)
        print("VAXANDE KORNING (FRISTAENDE) - ELASTICITETS-DISTRIBUTION")
        print("-" * 70)
        elast = growing[COL_ELAST]
        q = elast.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
        print(f"  Count : {int(q['count']):,}")
        print(f"  Mean  : {q['mean']:.4f}")
        print(f"  Std   : {q['std']:.4f}")
        print(f"  Min   : {q['min']:.4f}")
        print(f"   5%   : {q['5%']:.4f}")
        print(f"  25%   : {q['25%']:.4f}")
        print(f"  50%   : {q['50%']:.4f}")
        print(f"  75%   : {q['75%']:.4f}")
        print(f"  95%   : {q['95%']:.4f}")
        print(f"  Max   : {q['max']:.4f}")
    print()


# =====================================================================
# EXCEL-RAPPORT
# =====================================================================

def build_summary_sheet(
    growing: pd.DataFrame, bcg: pd.DataFrame, joined: pd.DataFrame
) -> pd.DataFrame:
    """Tabular summary - en rad per matt, ar 'Vaxande'/'BCG'/'Joined' kolumner."""
    n_g, n_b, n_j = growing.shape[0], bcg.shape[0], joined.shape[0]
    sig_g_mask = apply_ib2_gate(growing)
    sig_b_mask = apply_ib2_gate(bcg)

    rows = [
        ("Antal KEY", n_g, n_b, n_j),
        ("Signifikanta (IB.2-gate)", int(sig_g_mask.sum()), int(sig_b_mask.sum()),
         int((joined["sig_growing"] & joined["sig_bcg"]).sum()) if n_j else 0),
        ("Signifikans-andel %", round(100 * sig_g_mask.mean(), 2),
         round(100 * sig_b_mask.mean(), 2),
         round(100 * (joined["sig_growing"] & joined["sig_bcg"]).mean(), 2) if n_j else 0),
    ]
    if n_j:
        abs_diff = joined["elast_diff_abs"].abs()
        rows.extend([
            ("Median |elasticitets-skillnad|", "", "", round(abs_diff.median(), 4)),
            ("Max |elasticitets-skillnad|", "", "", round(abs_diff.max(), 4)),
            ("Antal med |diff| > 0.10", "", "", int((abs_diff > 0.10).sum())),
            ("Antal med |diff| > 0.25", "", "", int((abs_diff > 0.25).sum())),
            ("Antal med |diff| > 0.50", "", "", int((abs_diff > 0.50).sum())),
            ("Antal med |diff| > 1.00", "", "", int((abs_diff > 1.00).sum())),
            ("Tecken-flippar", "", "", int(joined["sign_flip"].sum())),
        ])
        e = growing[COL_ELAST]
        rows.extend([
            ("Vaxande elast median", round(e.median(), 4), "", ""),
            ("Vaxande elast mean", round(e.mean(), 4), "", ""),
            ("Vaxande elast 5-percentil", round(e.quantile(0.05), 4), "", ""),
            ("Vaxande elast 95-percentil", round(e.quantile(0.95), 4), "", ""),
        ])

    return pd.DataFrame(rows, columns=["Matt", "Vaxande", "BCG", "Joined"])


def write_excel(
    summary: pd.DataFrame,
    joined: pd.DataFrame,
    significant_only: pd.DataFrame,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        joined.to_excel(writer, sheet_name="Joined_comparison", index=False)
        significant_only.to_excel(writer, sheet_name="Significant_only", index=False)
    print(f"Excel-rapport sparad: {out_path}")


# =====================================================================
# HUVUDFLODE
# =====================================================================

def main() -> None:
    print("compare_elasticity_runs.py")
    print(f"  GROWING_PATH = {GROWING_PATH}")
    print(f"  BCG_PATH     = {BCG_PATH}")
    print()
    print("Laddar data...")
    growing = load_output_summary(GROWING_PATH, "Vaxande")
    bcg = load_output_summary(BCG_PATH, "BCG facit")
    print()
    print("Bygger inner join och berakningar...")
    joined = build_joined_comparison(growing, bcg)

    # Filtrera ut bara signifikanta KEY i vaxande for en separat flik
    significant_only = growing[apply_ib2_gate(growing)].copy()
    significant_only = significant_only.sort_values(
        COL_ELAST, key=lambda s: s.abs(), ascending=False
    )

    report_console(growing, bcg, joined)

    print("Skriver Excel-rapport...")
    summary = build_summary_sheet(growing, bcg, joined)
    write_excel(summary, joined, significant_only, OUTPUT_PATH)
    print()
    print("KLART.")


if __name__ == "__main__":
    main()

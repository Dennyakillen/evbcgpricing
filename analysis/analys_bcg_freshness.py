"""
analys_bcg_freshness.py  --  "Vad hände sedan BCG?"
====================================================
Decomposes how the final blended price elasticities changed between BCG's frozen
2025 snapshot and our growing run (10 extra months, through 2026-04). The headline
freshness check (verify_tool/provenance/validate_fallback_freshness.py) already showed
95% of products drift <0.5 -- stable. This goes deeper: WHERE does the movement sit?
A stable average can hide real shifts in specific services or clusters. We decompose
the drift per service, per cluster, per F-level, and revenue-weighted -- then the
THESIS is whatever the decomposition reveals (not assumed in advance).

Re-runnable: as periods grow, re-run against the newest Final_Fallback_Data. Returns
everything in-memory (no loose files) so an orchestrator can build the analyspaket
Excel + the presentation. Follows ANALYSPAKET_STANDARD: kör_analys(figur_dir) -> dict.

Grain: ProductKey + SiteCode + Clusters (Step 6 output row grain).
Drift = ours.final_elasticity - facit.final_elasticity (negative = more price-sensitive).

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-11.
"""
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

BCG_ROOT = Path(r"C:\Projekt\BCG")
FBL = BCG_ROOT / "Pipeline" / "02. Elasticity" / "6. Fall Back Logic"
BCG_FBL_FACIT = (
    Path("C:/Users/jepa02/OneDrive - Evidensia Djursjukvård AB/Datastrategi/BCG")
    / "BCG_orginal_V2_New" / "02. Elasticity" / "6. Fall Back Logic"
)

GRAIN = ["ProductKey", "SiteCode", "Clusters"]
DRIFT_ACCEPTABLE = 0.5      # |drift| below this = stable (IB.11-band analogue)
DRIFT_DECISION = 1.0        # |drift| above this = decision-relevant


def _find(patterns, prefer=None):
    cands = []
    for p in patterns:
        cands += glob.glob(str(p))
    if not cands:
        return None
    if prefer:
        for c in cands:
            if prefer in c:
                return Path(c)
    return Path(max(cands, key=os.path.getmtime))


def _load(path):
    df = pd.read_excel(path)
    for c in GRAIN:
        if c in df.columns:
            df[c] = df[c].astype(str)
    df["final_elasticity"] = pd.to_numeric(df.get("final_elasticity"), errors="coerce")
    if "TotalNet" in df.columns:
        df["TotalNet"] = pd.to_numeric(df["TotalNet"], errors="coerce")
    return df


def _wavg(values, weights):
    """Revenue-weighted mean, NaN-safe."""
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = v.notna() & w.notna() & (w > 0)
    if mask.sum() == 0 or w[mask].sum() == 0:
        return np.nan
    return float((v[mask] * w[mask]).sum() / w[mask].sum())


def kör_analys(figur_dir=None, our_path=None, facit_path=None):
    """Run the decomposition. Returns a dict with dataframes, log text, and
    (later) figure paths. figur_dir kept for ANALYSPAKET signature compatibility."""
    log = []

    def out(s=""):
        print(s)
        log.append(s)

    our_p = Path(our_path) if our_path else _find([
        FBL / "output_data" / "Final_Fallback_Data*.xlsx",
        FBL / "Final_Fallback_Data*.xlsx",
    ])
    facit_p = Path(facit_path) if facit_path else _find([
        BCG_FBL_FACIT / "output_data" / "Final_Fallback_Data*.xlsx",
        BCG_FBL_FACIT / "Final_Fallback_Data*.xlsx",
    ], prefer="20250930")

    if not our_p or not our_p.exists():
        raise FileNotFoundError("Growing Final_Fallback_Data not found -- run run_step6.py first.")
    if not facit_p or not facit_p.exists():
        raise FileNotFoundError(f"Frozen BCG facit not found under {BCG_FBL_FACIT}")

    out("=" * 70)
    out("VAD HÄNDE SEDAN BCG?  -  drift-dekomponering av priselasticiteten")
    out("=" * 70)
    out(f"Växande (våra) : {our_p.name}")
    out(f"Fruset (BCG)   : {facit_p.name}")
    out("")

    ours = _load(our_p)
    facit = _load(facit_p)

    # ---- align on grain ----
    keys = [c for c in GRAIN if c in ours.columns and c in facit.columns]
    m = ours.merge(
        facit[keys + ["final_elasticity"]].rename(columns={"final_elasticity": "fe_facit"}),
        on=keys, how="inner"
    )
    m["fe_ours"] = m["final_elasticity"]
    m["drift"] = m["fe_ours"] - m["fe_facit"]
    m = m.dropna(subset=["drift", "fe_facit", "fe_ours"])
    n = len(m)

    # ---- 1) HEADLINE ----
    ad = m["drift"].abs()
    headline = {
        "rows": n,
        "productkeys": int(m["ProductKey"].nunique()),
        "median_abs_drift": float(ad.median()),
        "mean_abs_drift": float(ad.mean()),
        "pct_stable": float(100 * (ad < DRIFT_ACCEPTABLE).mean()),
        "pct_decision": float(100 * (ad > DRIFT_DECISION).mean()),
        "n_decision": int((ad > DRIFT_DECISION).sum()),
        "median_fe_facit": float(m["fe_facit"].median()),
        "median_fe_ours": float(m["fe_ours"].median()),
        "stronger": float(100 * (m["drift"] < 0).mean()),   # more negative = more price-sensitive
        "weaker": float(100 * (m["drift"] > 0).mean()),
    }
    # revenue-weighted drift (the drift that actually moves money)
    if "TotalNet" in m.columns:
        headline["wavg_drift"] = _wavg(m["drift"], m["TotalNet"])
        headline["wavg_fe_facit"] = _wavg(m["fe_facit"], m["TotalNet"])
        headline["wavg_fe_ours"] = _wavg(m["fe_ours"], m["TotalNet"])

    out("--- HELHET ---")
    out(f"  aligned rows: {n:,}  ProductKeys: {headline['productkeys']:,}")
    out(f"  median |drift|: {headline['median_abs_drift']:.4f}   "
        f"stabila (<{DRIFT_ACCEPTABLE}): {headline['pct_stable']:.1f}%")
    out(f"  beslutsrelevant (>{DRIFT_DECISION}): {headline['pct_decision']:.1f}% "
        f"({headline['n_decision']:,} rader)")
    out(f"  median elasticitet: facit {headline['median_fe_facit']:.3f} -> "
        f"växande {headline['median_fe_ours']:.3f}")
    out(f"  riktning: {headline['stronger']:.1f}% starkare (mer priskänsliga), "
        f"{headline['weaker']:.1f}% svagare")
    if "wavg_drift" in headline:
        out(f"  omsättningsvägd drift: {headline['wavg_drift']:+.4f}  "
            f"(facit {headline['wavg_fe_facit']:.3f} -> växande {headline['wavg_fe_ours']:.3f})")
    out("")

    # ---- 2) PER SERVICE ----
    svc_col = "service" if "service" in m.columns else None
    per_service = pd.DataFrame()
    if svc_col:
        g = m.groupby(svc_col)
        per_service = pd.DataFrame({
            "rader": g.size(),
            "median_drift": g["drift"].median(),
            "median_abs_drift": g["drift"].apply(lambda s: s.abs().median()),
            "andel_starkare_%": g["drift"].apply(lambda s: 100 * (s < 0).mean()),
            "median_fe_facit": g["fe_facit"].median(),
            "median_fe_ours": g["fe_ours"].median(),
        })
        if "TotalNet" in m.columns:
            per_service["oms_vagd_drift"] = g[["drift","TotalNet"]].apply(lambda d: _wavg(d["drift"], d["TotalNet"]))
            per_service["oms_Mkr"] = g["TotalNet"].sum() / 1e6
        per_service = per_service.sort_values("median_abs_drift", ascending=False).reset_index()
        out("--- PER SERVICE (var sitter rörelsen?) ---")
        out(per_service.round(3).to_string(index=False))
        out("")

    # ---- 3) PER KLUSTER ----
    per_cluster = pd.DataFrame()
    if "Clusters" in m.columns:
        g = m.groupby("Clusters")
        per_cluster = pd.DataFrame({
            "rader": g.size(),
            "median_drift": g["drift"].median(),
            "median_abs_drift": g["drift"].apply(lambda s: s.abs().median()),
            "andel_starkare_%": g["drift"].apply(lambda s: 100 * (s < 0).mean()),
        })
        if "TotalNet" in m.columns:
            per_cluster["oms_vagd_drift"] = g[["drift","TotalNet"]].apply(lambda d: _wavg(d["drift"], d["TotalNet"]))
        per_cluster = per_cluster.sort_values("median_abs_drift", ascending=False).reset_index()
        out("--- PER KLUSTER ---")
        out(per_cluster.round(3).to_string(index=False))
        out("")

    # ---- 4) F-LEVEL MIX SHIFT ----
    f_mix = pd.DataFrame()
    if "elasticity_level" in ours.columns:
        ours_mix = ours["elasticity_level"].value_counts(normalize=True).mul(100)
        f_mix = ours_mix.round(1).reset_index()
        f_mix.columns = ["F_niva", "andel_%"]
        out("--- F-NIVÅ KÄLLMIX (växande) ---")
        out(f_mix.to_string(index=False))
        out("")

    # ---- 5) TOP MOVERS (revenue-weighted, deduped per ProductKey) ----
    top_movers = pd.DataFrame()
    if "TotalNet" in m.columns:
        pk = m.groupby("ProductKey").agg(
            fe_facit=("fe_facit", "median"),
            fe_ours=("fe_ours", "median"),
            oms_Mkr=("TotalNet", lambda s: s.sum() / 1e6),
            service=("service", "first") if svc_col else ("ProductKey", "first"),
        ).reset_index()
        pk["drift"] = pk["fe_ours"] - pk["fe_facit"]
        pk["oms_vagd_paverkam"] = pk["drift"].abs() * pk["oms_Mkr"]   # impact = drift x revenue
        top_movers = pk.sort_values("oms_vagd_paverkam", ascending=False).head(15).reset_index(drop=True)
        out("--- TOPP 15 RÖRELSER (drift × omsättning = beslutspåverkan) ---")
        out(top_movers.round(3).to_string(index=False))
        out("")

    return {
        "headline": headline,
        "per_service": per_service,
        "per_cluster": per_cluster,
        "f_mix": f_mix,
        "top_movers": top_movers,
        "merged": m,
        "logg_text": "\n".join(log),
        "our_file": our_p.name,
        "facit_file": facit_p.name,
        "figurer": [],   # filled by orchestrator/presentation step
    }


def main():
    res = kör_analys()
    print()
    print("[KLART] dekomponering färdig. Fynd ovan avgör tesen för presentationen.")
    # quick thesis hint
    h = res["headline"]
    print()
    print("=== TES-INDIKATION (data, inte gissning) ===")
    if h["pct_stable"] >= 90:
        print(f"  Helheten är STABIL ({h['pct_stable']:.0f}% <0.5 drift).")
    if not res["per_service"].empty:
        ps = res["per_service"]
        top = ps.iloc[0]
        print(f"  Men störst rörelse i service: '{top[ps.columns[0]]}' "
              f"(median |drift| {top['median_abs_drift']:.3f})")
    if "wavg_drift" in h:
        direction = "starkare/mer priskänsliga" if h["wavg_drift"] < 0 else "svagare"
        print(f"  Omsättningsvägt har elasticiteterna blivit {direction} "
              f"({h['wavg_drift']:+.3f}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fallback_blend.py  --  Standalone replication of BCG's step-5 fallback ("blended logic").
                       v2: built against the FULL source (data_prep_after_model_output.py 1-366,
                       model.py, constants.py) -- no longer a hypothesis.

Developer: Jens Palmoe (Senior Business Analyst, Evidensia Djursjukvard AB), with AI advisor.
Project:   evbcgpricing -- replication track, step 5 (fallback / blended_logic). Closes the last
           replication gap before the reasonableness gate (which we run LAST, pre-fresh-data).

===============================================================================================
WHAT IT REPLICATES (verbatim, from the read source -- line refs to BCG's file)
===============================================================================================
  model_output(path, prod_df)   [BCG L114-146]:
      1. read output_summary.xlsx                                  (BCG: pd.read_excel(path))
      2. KEY patch  'Clinics-nan-0' -> 'Clinics-NA-0'              (BCG L123)
      3. split KEY via regex -> Cluster + ItemCode                 (BCG L127-130)
      4. join prod_df -> Product Description, Rank, Service        (BCG L133-135)  [OPTIONAL here]
      5. Weighted elasticity / rsq / Pvalue = TotalNet * metric    (BCG L137-140)
      6. Check         = sign(Correl)==sign(ELASTICITY) ? 1 : 0    (BCG L144)
      7. Significant ? = RSQ>=0.5 AND PVALUE<=0.2 ? 1 : 0          (BCG L145)  (loose gate, not p<0.05)
      8. rename Cluster_Granularity -> 'Cluster'                   (BCG L146)

  blended_logic(model_output_df, model_result_1) [BCG L149-195]:
      1. Cluster --cluster_h_map--> New_cluster --clustermap--> big_cluster
      2. final_model = groupby(Service, big_cluster, New_cluster, Significant?).TotalNet.sum()
      3. sort [Significant? DESC, TotalNet DESC] -> drop_duplicates(Service, big_cluster)
         => "take the significant row if any, else the highest-revenue row" per (Service,big_cluster)
      4. merge winner back onto fine rows -> weak groups inherit the strong peer's representative

THE RULE IN ONE LINE: fallback is a REVENUE-WEIGHTED REPRESENTATIVE PICK within each
(Service x big_cluster), not a re-estimation. That is why 227 raw-significant becomes ~618 after
blending -- the flag is read on the BLENDED frame where weak groups carry a strong peer's stats.

===============================================================================================
WHAT IS DELIBERATELY OPTIONAL (and why)
===============================================================================================
prod_df (Rank / Product Description) -- BCG's rank_calc() reads a product file with columns
'Sum_SalesTotal' + 'ItemDescription English' that do NOT match Complete_Product_Data.xlsx
(SalesTotal / ItemDescription). The exact rank_calc source is an Alteryx-fed file we have not
pinned down. BUT the blend LOGIC depends only on Service / big_cluster / Significant? / TotalNet --
NOT on Rank or Description (those are carried for downstream output only). So:
  - If 'Service' (or ProductGroupL4Name) is ALREADY in output_summary, we use it -> no prod file needed.
  - Else, pass --prod-file with tolerant column mapping to join Service in.
This lets us validate the fallback RULE now, and pin rank_calc's exact source later if you want
the Rank column for the dashboard.  FLAG R (rank source unresolved) is logged, never silent.

CONSTANTS lifted verbatim from constants.py (line refs in comments).
Output: structural only -- safe to tee + paste back. Writes two CSVs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Encoding guard (Windows PS 5.1 / cp1252 console) -- lesson from project masters.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# -- Verbatim from constants.py (Cluster model) -------------------------------------------------
KEY                 = "KEY"                                  # L8
DOLLAR              = "TotalNet"                              # L4
UNIT                = "QuantitySold(SalesTotal>0)"           # L6
DATE                = "week_starting_monday"                 # L7
ALGO_REGULAR_PRICE  = "Regular_Price_fwbw_max_6"             # L10
ELASTICITY_COL      = "ELASTICITY_Regular_Price_fwbw_max_6"  # L38
RSQ_COL             = "RSQ"                                  # L39
ADJ_RSQ             = "ADJ_RSQ"                              # L40
Correl_col          = "Correl"                               # L41
PVALUE_PREFIX       = "PVALUE_"                              # L42
Product_Code_var    = "ItemCode"                             # L46
Cluster_Granularity = "Cluster"                              # L47
SERVICE_VAR         = "ProductGroupL4Name"                   # L48
DESC_COL_PRODUCT    = "ItemDescription"                      # L50
RANK                = "Rank"                                 # L32
SERVICE_OUTPUT_NAME = "Service"                              # L61  (blend groups on THIS)
Product_Code_var_data_prep = "Product Description"           # L66
NO_OF_SITES         = "No of Sites"                          # L67

PVALUE_COL = PVALUE_PREFIX + ALGO_REGULAR_PRICE

# Hierarchy maps -- verbatim constants.py L75/L78 (COMPLETE incl. Sjukhus seeds).
cluster_h_map = {
    "Clinics 0": "Clinics", "Clinics 1": "Clinics", "Clinics 2": "Clinics",
    "Clinics": "Clinics_CH", "Hospital": "Hospital_CH",
    "Sjukhus A": "Hospital", "Sjukhus B": "Hospital",
    "Sjukhus C": "Hospital", "Sjukhus Sodran": "Hospital",
    "Sjukhus S\u00f6dran": "Hospital",   # both ASCII + real diacritic, defensive
}
clustermap = {
    "Clinics": "Clinics", "Clinics_CH": "Clinics",
    "Hospital_CH": "Hospital", "Hospital": "Hospital",
}

RSQ_MIN    = 0.5
ALPHA_PVAL = 0.2


def log(tag: str, msg: str) -> None:
    try:
        print(f"[{tag}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{tag}] {msg}".encode("ascii", "replace").decode("ascii"), flush=True)


def build_prod_df(prod_path: Path) -> pd.DataFrame:
    """rank_calc analog: [ItemCode, Product Description, Rank, Service], tolerant to column names."""
    df = pd.read_excel(prod_path)
    cols = {c.lower().strip(): c for c in df.columns}

    def pick(*cands):
        for c in cands:
            if c.lower() in cols:
                return cols[c.lower()]
        return None

    ic    = pick("ItemCode")
    svc   = pick("ProductGroupL4Name", "Service")
    desc  = pick("ItemDescription English", "ItemDescription", "Product Description")
    sales = pick("Sum_SalesTotal", "SalesTotal")
    if ic is None or svc is None:
        raise KeyError(f"prod file needs ItemCode + a service column; got {df.columns.tolist()}")

    df["ItemCode"] = df[ic].astype(str).str.strip().str.upper()
    df[SERVICE_OUTPUT_NAME] = df[svc].astype(str).str.strip()
    df[Product_Code_var_data_prep] = df[desc].astype(str) if desc else ""

    if sales is not None:
        agg = (df.groupby([SERVICE_OUTPUT_NAME, "ItemCode", Product_Code_var_data_prep],
                          as_index=False)[sales].sum())
        agg[RANK] = agg[sales].rank(ascending=False, method="first")
    else:
        log("WARN", "FLAG R: no sales column for Rank -> blank (logic unaffected)")
        agg = df[[SERVICE_OUTPUT_NAME, "ItemCode", Product_Code_var_data_prep]].drop_duplicates()
        agg[RANK] = np.nan

    out = agg[["ItemCode", Product_Code_var_data_prep, RANK, SERVICE_OUTPUT_NAME]].drop_duplicates("ItemCode")
    log("PROD", f"prod_df built: {len(out)} ItemCodes, {out[SERVICE_OUTPUT_NAME].nunique()} services")
    return out


def model_output(summary_path: Path, prod_df):
    df = pd.read_excel(summary_path)                                          # BCG L122
    log("IN", f"output_summary: shape={df.shape} cols={df.columns.tolist()}")

    if KEY not in df.columns:
        raise KeyError(f"'{KEY}' not in output_summary columns {df.columns.tolist()}")

    df[KEY] = np.where(df[KEY] == "Clinics-nan-0", "Clinics-NA-0", df[KEY])   # BCG L123

    pattern = rf"^(?P<{Cluster_Granularity}>[^-]+)-(?P<{Product_Code_var}>.+)$"  # BCG L127
    out = df[KEY].astype(str).str.extract(pattern)
    df[Cluster_Granularity] = out[Cluster_Granularity]
    df[Product_Code_var] = out[Product_Code_var].str.strip().str.upper()

    unsplit = df[Cluster_Granularity].isna().sum()
    if unsplit:
        log("WARN", f"{unsplit} KEY(s) did not match Cluster-ItemCode pattern")

    if SERVICE_OUTPUT_NAME in df.columns:
        log("SVC", f"'{SERVICE_OUTPUT_NAME}' already present -> no prod join needed")
    elif SERVICE_VAR in df.columns:
        log("SVC", f"aliasing existing '{SERVICE_VAR}' -> '{SERVICE_OUTPUT_NAME}'")
        df[SERVICE_OUTPUT_NAME] = df[SERVICE_VAR]
    elif prod_df is not None:
        log("SVC", "joining Service/Rank/Description from --prod-file")
        df = df.merge(prod_df[[Product_Code_var, Product_Code_var_data_prep, RANK, SERVICE_OUTPUT_NAME]],
                      on=Product_Code_var, how="left")
        miss = df[SERVICE_OUTPUT_NAME].isna().sum()
        if miss:
            log("WARN", f"{miss} rows got no Service from prod join (ItemCode mismatch)")
    else:
        raise KeyError(
            f"No service column ('{SERVICE_OUTPUT_NAME}'/'{SERVICE_VAR}') and no --prod-file. "
            f"Blend groups on Service. Columns: {df.columns.tolist()}")

    df["Weighted elasticity"] = df[DOLLAR] * df[ELASTICITY_COL]              # BCG L137
    df["Weighted  rsq"]       = df[DOLLAR] * df[RSQ_COL]                     # BCG L138 (double space)
    if PVALUE_COL in df.columns:
        df["Weighted Pvalue"] = df[DOLLAR] * df[PVALUE_COL]                  # BCG L140
    else:
        log("WARN", f"FLAG P: '{PVALUE_COL}' absent -> Significant? all-0")

    df["Check"] = np.where(                                                 # BCG L144
        ((df[Correl_col] < 0) & (df[ELASTICITY_COL] < 0)) |
        ((df[Correl_col] > 0) & (df[ELASTICITY_COL] > 0)), 1, 0)

    if PVALUE_COL in df.columns:                                            # BCG L145
        df["Significant ?"] = np.where(
            (df[RSQ_COL] >= RSQ_MIN) & (df[PVALUE_COL] <= ALPHA_PVAL), 1, 0)
    else:
        df["Significant ?"] = 0

    return df


def blended_logic(model_output_df, model_result_1=None):
    df = model_output_df.copy()
    df["New_cluster"] = df[Cluster_Granularity].map(cluster_h_map)          # BCG L177
    df["big_cluster"] = df["New_cluster"].map(clustermap)                   # BCG L179

    unmapped = sorted(df[df["New_cluster"].isna()][Cluster_Granularity].dropna().astype(str).unique())
    if unmapped:
        log("WARN", f"FLAG H: {len(unmapped)} Cluster value(s) not in cluster_h_map -> DROP in blend: {unmapped[:10]}")

    final_model = (                                                         # BCG L182
        df.groupby([SERVICE_OUTPUT_NAME, "big_cluster", "New_cluster", "Significant ?"], dropna=False)
          .agg({DOLLAR: "sum"}).reset_index()
    )
    final_model = (                                                         # BCG L183
        final_model.sort_values(by=["Significant ?", DOLLAR], ascending=[False, False])
                   .drop_duplicates([SERVICE_OUTPUT_NAME, "big_cluster"])
                   .sort_values(by=SERVICE_OUTPUT_NAME)
    )

    model_output_df_1 = df.merge(final_model, on=[SERVICE_OUTPUT_NAME, "big_cluster", "New_cluster"])  # BCG L185
    if "TotalNet_y" in model_output_df_1.columns:
        model_output_df_1 = model_output_df_1.drop(columns=["TotalNet_y", "Significant ?_y"])
        model_output_df_1 = model_output_df_1.rename(
            columns={"TotalNet_x": "TotalNet", "Significant ?_x": "Significant ?"})

    model_result_2 = None
    if model_result_1 is not None:
        mr = model_result_1.copy()
        mr["New_cluster"] = mr[Cluster_Granularity].map(cluster_h_map)
        mr["big_cluster"] = mr["New_cluster"].map(clustermap)
        model_result_2 = mr.merge(final_model, on=[SERVICE_OUTPUT_NAME, "big_cluster", "New_cluster"])

    return model_output_df_1, model_result_2, final_model


def validate_against_facit(final_model, facit_path: Path) -> None:
    facit = pd.read_excel(facit_path)
    log("FACIT", f"facit shape={facit.shape} ours={final_model.shape}")
    keycols = [SERVICE_OUTPUT_NAME, "big_cluster", "New_cluster"]
    if not all(c in facit.columns for c in keycols):
        log("FACIT", f"facit missing key cols; has {facit.columns.tolist()}")
        return
    f = facit[keycols + ["Significant ?"]].copy()
    o = final_model[keycols + ["Significant ?"]].copy()
    for d in (f, o):
        for c in keycols:
            d[c] = d[c].astype(str).str.strip()
    merged = f.merge(o, on=keycols, how="outer", suffixes=("_facit", "_ours"), indicator=True)
    both   = (merged["_merge"] == "both").sum()
    only_f = (merged["_merge"] == "left_only").sum()
    only_o = (merged["_merge"] == "right_only").sum()
    log("FACIT", f"(Service,big_cluster,New_cluster) match: both={both} only_facit={only_f} only_ours={only_o}")
    if both:
        m = merged[merged["_merge"] == "both"]
        agree = (m["Significant ?_facit"] == m["Significant ?_ours"]).sum()
        log("FACIT", f"Significant? agreement on matched rows: {agree}/{both}")
    log("FACIT", f"representative-set match: {'PASS' if (only_f == 0 and only_o == 0) else 'REVIEW'}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Replicate BCG step-5 fallback (model_output + blended_logic).")
    ap.add_argument("--output-summary", required=True, help="Path to output_summary.xlsx")
    ap.add_argument("--prod-file", default=None, help="Optional product file for Service/Rank")
    ap.add_argument("--facit", default=None, help="Optional final_model_*.xlsx to validate against")
    ap.add_argument("--out", default="blended_output.csv", help="Output CSV path")
    args = ap.parse_args()

    summary = Path(args.output_summary)
    if not summary.exists():
        log("ERROR", f"output_summary not found: {summary}")
        return 2

    prod_df = None
    if args.prod_file:
        pf = Path(args.prod_file)
        if not pf.exists():
            log("ERROR", f"prod file not found: {pf}")
            return 2
        prod_df = build_prod_df(pf)

    mo = model_output(summary, prod_df)
    log("STEP", f"after model_output: shape={mo.shape}")
    sig = int(pd.to_numeric(mo["Significant ?"], errors="coerce").fillna(0).sum())
    chk = int(pd.to_numeric(mo["Check"], errors="coerce").fillna(0).sum())
    log("KPI", f"pre-blend: Significant?=1 {sig}/{len(mo)}  Check=1 {chk}/{len(mo)}")

    blended, _, final_model = blended_logic(mo, model_result_1=None)
    log("STEP", f"after blend: rows={len(blended)}  representatives={len(final_model)}")
    log("KPI", f"New_cluster distinct: {sorted(blended['New_cluster'].dropna().astype(str).unique())}")
    log("KPI", f"big_cluster distinct: {sorted(blended['big_cluster'].dropna().astype(str).unique())}")
    sig_b = int(pd.to_numeric(blended['Significant ?'], errors='coerce').fillna(0).sum())
    log("KPI", f"post-blend: Significant?=1 {sig_b}/{len(blended)}")

    if args.facit:
        fp = Path(args.facit)
        if fp.exists():
            validate_against_facit(final_model, fp)
        else:
            log("WARN", f"facit not found: {fp}")

    out = Path(args.out)
    blended.to_csv(out, index=False, encoding="cp1252", errors="replace")
    log("Saved", f"blended output -> {out} ({len(blended)} rows)")
    fm_out = out.with_name(out.stem + "_final_model.csv")
    final_model.to_csv(fm_out, index=False, encoding="cp1252", errors="replace")
    log("Saved", f"final_model (representatives) -> {fm_out} ({len(final_model)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

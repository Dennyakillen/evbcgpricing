"""
pipeline_contracts.py  --  boundary-kontrakt for modellkedjan (Phase Z, additivt)
=================================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.  KALIBRERAD 2026-06-26 mot faktiska kolumner (--calibrate).

SYFTE
-----
Flytta valideringen FRAN efter gransen TILL gransen, och gor den BLOCKERANDE.
Verifierar FORM (kolumner), VOLYM (radantal) och INVARIANTER (icke-null nyckel,
numerisk elasticitet) och VAGRAR starta nasta steg annars. Felet pekar pa VILKEN
input och VILKEN kolumn -- inte en KeyError djupt i Fall_Back_Logic.

KALIBRERINGSLOGG (mat, gissa inte -- de FAKTISKA kolumnerna, ej gissade)
------------------------------------------------------------------------
Forsta utkastet GISSADE kolumner; --calibrate visade att flera var FEL. Rattat:
  blended_model  : 10 kol -> KEY, Cluster, ItemCode, QuantitySold(SalesTotal>0),
                   ELASTICITY_..., PVALUE_..., Correl, RSQ, ADJ_RSQ, TotalNet. [OK]
  blended_output : 5 kol -> ['New_cluster','Service','Significant ?','TotalNet',
                   'big_cluster']. INGEN KEY (min gissning var FEL). Fall_Back_Logic
                   doper om Service->ProductGroupL4Name, New_cluster->Service_Granularity,
                   big_cluster->New_Cluster (rad 634) och mergar pa de tva sista.
                   Kontrakt: kravx exakt dessa 5 (sa en namndrift -- t.ex. 'New_cluster'
                   vs 'New_Cluster' -- FANGAS, den ar en akta fralla har).
  bundle_cluster : 8 kol -> KEY, ELASTICITY_..., PVALUE_..., Correl, RSQ, ADJ_RSQ,
                   Bundle_visits, basket_revenue. (Min gissning saknade KEY +
                   basket_revenue.) Rattat.
  df_all_product : 8 kol -> Cluster, ID_Department, ItemCode, ItemDescription,
                   New_Cluster, ProductGroupL4Name, SalesTotal, SalesTotal_YearEnding25.
                   20 null i ItemCode = "Na (Natrium) Catalyst"/"Internal" = icke-
                   prissatta (se prefilter_unpriced.py). Hanteras nedan.
  prod_site      : 8 kol -> KEY, ELASTICITY_..., PVALUE_..., QuantitySold(...),
                   Correl, RSQ, ADJ_RSQ, TotalNet. Rattat (gissning saknade KEY).

NULL-NYCKEL: ICKE-PRISSATT vs PRISSATT (det smarta undantaget)
--------------------------------------------------------------
De 20 null-ItemCode ar labbreagens-kostnad ("Internal"), ej prissatt -> SKA falla
ur (de hanteras explicit av prefilter_unpriced.py FORE detta kontrakt, sa nar
kontraktet kor ar de redan borta). Kontraktet validerar HELLER inte bara "20 null
OK" -- det kraver: null ItemCode tillats ENDAST pa icke-prissatt kategori. En null
pa en PRISSATT produkt ar en akta bugg och blockerar. Sa cementeras felKLASSEN,
inte bara instansen: nasta icke-prissatta hanteras ratt, nasta prissatta-utan-
nyckel stoppas.

ORDNING I run_step6.preflight():
  1. prefilter_unpriced.prefilter_weave_weights(src)  -> clean_path (icke-prissatta bort)
  2. placera clean_path
  3. pipeline_contracts.validate_all()                -> blockerar pa allt ovrigt
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
ELAST = REPO / "Pipeline" / "02. Elasticity"
FBL = ELAST / "6. Fall Back Logic"

# icke-prissatta kategorier -- MASTE spegla prefilter_unpriced.UNPRICED_CATEGORIES
UNPRICED_CATEGORIES = {"internal"}


# ===========================================================================
@dataclass
class Contract:
    label: str
    path: Path
    required_cols: list[str] = field(default_factory=list)
    min_rows: int = 1
    non_null: list[str] = field(default_factory=list)
    numeric: list[str] = field(default_factory=list)
    # null tillaten pa nyckeln ENDAST nar kategori-kolumnen ar icke-prissatt:
    null_ok_when_unpriced: "tuple[str, str] | None" = None  # (key_col, category_col)
    note: str = ""


# ===========================================================================
# KALIBRERADE KONTRAKT (faktiska kolumner per --calibrate 2026-06-26)
# ===========================================================================
CONTRACTS: list[Contract] = [
    Contract(
        label="blended_model (Cluster step 1-4)",
        path=ELAST / "2. Product Cluster Level Models" / "output" / "output_summary_ready.xlsx",
        required_cols=["KEY", "Cluster", "ItemCode", "QuantitySold(SalesTotal>0)",
                       "ELASTICITY_Regular_Price_fwbw_max_6", "PVALUE_Regular_Price_fwbw_max_6"],
        min_rows=3000,
        non_null=["KEY"],
        numeric=["ELASTICITY_Regular_Price_fwbw_max_6"],
        note="LIVE GROWING. KEY -> Cluster+ItemCode (LB.52). [10 kol verifierat, 4180]",
    ),
    Contract(
        label="blended_output (Cluster step-5 blend)",
        path=ELAST / "2. Product Cluster Level Models" / "output" / "final_model_cluster_granularity.xlsx",
        # KALIBRERAT: exakt de 5 faktiska kolumnerna. Fangar namndrift (t.ex.
        # 'New_cluster' -> 'New_Cluster') -- en akta fralla, Fall_Back_Logic rad 634
        # doper om exakt 'New_cluster'/'Service'/'big_cluster'.
        required_cols=["New_cluster", "Service", "Significant ?", "TotalNet", "big_cluster"],
        min_rows=1,
        note="FROZEN (FD.15). 5 kol, cluster-granularitet, ingen KEY. Namndrift fangas. [43]",
    ),
    Contract(
        label="bundle_cluster (Bundle model)",
        path=ELAST / "5. Bundle Clinic Models" / "output" / "model" / "output_summary.xlsx",
        required_cols=["KEY", "ELASTICITY_Regular_Price_fwbw_max_6",
                       "PVALUE_Regular_Price_fwbw_max_6", "basket_revenue"],
        min_rows=50,
        numeric=["ELASTICITY_Regular_Price_fwbw_max_6"],
        note="FROZEN (FD.11). PULL fran Blob. [8 kol verifierat, 125]",
    ),
    Contract(
        label="df_all_product (weave weights)",
        path=FBL / "input_data" / "Complete_Product_Data.xlsx",
        required_cols=["ItemCode", "ItemDescription", "ProductGroupL4Name", "New_Cluster",
                       "ID_Department", "SalesTotal", "SalesTotal_YearEnding25"],
        min_rows=1,
        # null ItemCode OK ENBART pa icke-prissatt kategori; prissatt-null blockerar.
        null_ok_when_unpriced=("ItemCode", "ProductGroupL4Name"),
        note="FROZEN (FD.14). null ItemCode tillats endast pa icke-prissatt (Internal). [8 kol]",
    ),
    Contract(
        label="prod_site (Site model)",
        path=ELAST / "3. Product Site Level Models" / "output" / "model" / "output_summary.xlsx",
        required_cols=["KEY", "QuantitySold(SalesTotal>0)",
                       "ELASTICITY_Regular_Price_fwbw_max_6", "PVALUE_Regular_Price_fwbw_max_6"],
        min_rows=4000,
        numeric=["ELASTICITY_Regular_Price_fwbw_max_6"],
        note="LIVE GROWING. [8 kol verifierat, 6604]",
    ),
]


# ===========================================================================
@dataclass
class Result:
    label: str
    status: str   # OK | FAIL | REVIEW
    detail: str


def _check_one(c: Contract, calibrate: bool) -> list[Result]:
    out: list[Result] = []
    if not c.path.exists():
        return [Result(c.label, "FAIL", f"SAKNAS: {c.path}")]
    try:
        import pandas as pd
    except ImportError:
        return [Result(c.label, "OK", "pandas saknas -- existenskoll (INFO)")]
    try:
        df = pd.read_excel(c.path)
    except Exception as e:  # noqa: BLE001
        return [Result(c.label, "FAIL", f"kunde ej lasa: {type(e).__name__}: {e}")]

    cols = set(map(str, df.columns))
    if calibrate:
        return [Result(c.label, "OK",
                       f"FAKTISKT: {len(df):,} rader, {len(cols)} kolumner -> {sorted(cols)}")]

    # form
    missing = [col for col in c.required_cols if col not in cols]
    if missing:
        out.append(Result(c.label, "FAIL", f"saknar kolumn(er): {missing}"))
    elif c.required_cols:
        out.append(Result(c.label, "OK", f"alla {len(c.required_cols)} kravkolumner finns"))
    else:
        out.append(Result(c.label, "OK", "existens/volym-vakt"))

    # volym
    if len(df) < c.min_rows:
        out.append(Result(c.label, "FAIL",
                          f"VOLYM under golv: {len(df):,} < min {c.min_rows:,} (tyst tapp?)"))
    else:
        out.append(Result(c.label, "OK", f"volym OK: {len(df):,} rader (golv {c.min_rows:,})"))

    # non-null (hard)
    for col in c.non_null:
        if col in cols:
            n = int(df[col].isna().sum())
            out.append(Result(c.label, "OK" if n == 0 else "FAIL",
                              f"{col}: inga null" if n == 0 else f"{col}: {n} null (blockerar)"))

    # null tillaten endast pa icke-prissatt kategori
    if c.null_ok_when_unpriced:
        key_col, cat_col = c.null_ok_when_unpriced
        if key_col in cols and cat_col in cols:
            null_key = df[key_col].isna()
            cat_norm = df[cat_col].astype(str).str.lower().str.strip()
            unpriced_null = int((null_key & cat_norm.isin(UNPRICED_CATEGORIES)).sum())
            priced_null = int((null_key & ~cat_norm.isin(UNPRICED_CATEGORIES)).sum())
            if priced_null == 0:
                out.append(Result(c.label, "REVIEW" if unpriced_null else "OK",
                                  f"{key_col}: {unpriced_null} null pa icke-prissatt "
                                  f"({'/'.join(UNPRICED_CATEGORIES)}) -- vantat, hanteras av "
                                  f"prefilter. 0 null pa prissatt produkt." if unpriced_null
                                  else f"{key_col}: inga null"))
            else:
                out.append(Result(c.label, "FAIL",
                                  f"{key_col}: {priced_null} null pa PRISSATT produkt "
                                  f"-- akta avvikelse, blockerar (icke-prissatta: {unpriced_null})"))

    # numerisk
    for col in c.numeric:
        if col in cols:
            import pandas as pd
            coerced = pd.to_numeric(df[col], errors="coerce")
            bad = int(coerced.isna().sum() - df[col].isna().sum())
            out.append(Result(c.label, "OK" if bad == 0 else "FAIL",
                              f"{col}: numerisk OK" if bad == 0 else f"{col}: {bad} icke-numeriska"))
    return out


def validate_all(calibrate: bool = False) -> bool:
    """True om inga FAIL (REVIEW blockerar inte). Anropas av run_step6.preflight()
    EFTER prefilter_unpriced:
        if not validate_all(): return False"""
    mode = "KALIBRERING (faller aldrig)" if calibrate else "BLOCKERANDE"
    print("=" * 72)
    print(f"PIPELINE CONTRACTS  --  Step 6 boundary  --  lage: {mode}")
    print("=" * 72)
    has_fail = has_review = False
    for c in CONTRACTS:
        print(f"\n[{c.label}]  {c.note}")
        for r in _check_one(c, calibrate):
            mark = {"OK": "  OK ", "FAIL": " FAIL", "REVIEW": "REVUE"}.get(r.status, r.status)
            print(f"   [{mark}] {r.detail}")
            if r.status == "FAIL" and not calibrate:
                has_fail = True
            if r.status == "REVIEW":
                has_review = True
    print("\n" + "-" * 72)
    if calibrate:
        print("KALIBRERING klar.")
        return True
    if has_fail:
        print("KONTRAKTSBROTT -- nasta steg far INTE kora. Atgarda ovan.")
        return False
    if has_review:
        print("ALLA KONTRAKT UPPFYLLDA (med vantade icke-prissatta null -- se REVUE).")
        return True
    print("ALLA KONTRAKT UPPFYLLDA -- gransen ar saker.")
    return True


if __name__ == "__main__":
    sys.exit(0 if validate_all(calibrate="--calibrate" in sys.argv) else 1)

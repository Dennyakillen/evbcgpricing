"""
prefilter_unpriced.py  --  additiv pre-filter for Step 6-input (HANTVERKSLAGNINGEN)
==================================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.

VAD DETTA LAGAR (rotorsaken, inte symptomet)
--------------------------------------------
Sond + kallasning bevisade: Complete_Product_Data.xlsx (FD.14 vav-vikter) bar 20
rader "Na (Natrium) Catalyst" / ProductGroupL4Name "Internal" UTAN ItemCode. De
ar labbreagens-KOSTNAD, inte prissatt saljbar produkt -> de SKA inte ha elasticitet.

I Fall_Back_Logic.py faller de redan ur -- men TYST, via en inner join utan how=
(read_blended_model_data rad ~252: dfcluster.merge(service_map, on=ProductKey)).
NaN-nyckel matchar inte -> raderna forsvinner utan spar. RATT utfall, FEL mekanism:
  - en VERKLIG produkt som tappar sin ItemCode (akta bugg) gommer sig i SAMMA
    tysta hal och upptacks aldrig.
  - ingen logg sager vad som foll bort eller varfor.

LAGNINGEN (additiv -- BCG-koden orord)
--------------------------------------
Gor det avsiktliga EXPLICIT: ta bort icke-prissatta poster FORE de nar vaven, med
en loggrad som sager exakt vad och varfor. Da sker ratt sak av ratt anledning,
synligt, och en null pa en PRISSATT produkt blockeras anda (av kontraktet).

"Harled, deklarera inte tva ganger": vilka kategorier som ar icke-prissatta bor pa
ETT stalle (UNPRICED_CATEGORIES). Andras affarsregeln sags det har, inte spritt.

ANVANDS AV run_step6.preflight() FORE placering:
    from prefilter_unpriced import prefilter_weave_weights
    clean_path, report = prefilter_weave_weights(src_path)
    # placera clean_path istallet for src_path; logga report

KOR FRISTAENDE (rapport utan att skriva):
    py -3.11 prefilter_unpriced.py --report
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

FBL = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\6. Fall Back Logic")
DEFAULT_SRC = FBL / "input_data" / "Complete_Product_Data.xlsx"

# ---------------------------------------------------------------------------
# AFFARSREGEL (single source) -- kategorier vars poster INTE ar prissatta och
# darfor legitimt saknar ItemCode. Utoka HAR om fler icke-prissatta dyker upp.
# ---------------------------------------------------------------------------
UNPRICED_CATEGORIES = {"internal"}   # ProductGroupL4Name (lower/strip-normaliserat)
KEY_COL = "ItemCode"
CATEGORY_COL = "ProductGroupL4Name"
MONEY_COLS = ("SalesTotal", "SalesTotal_YearEnding25")


@dataclass
class FilterReport:
    src_rows: int = 0
    kept_rows: int = 0
    removed_unpriced: int = 0
    removed_unpriced_revenue: float = 0.0
    suspicious_priced_nulls: int = 0          # null ItemCode pa EJ icke-prissatt kategori
    suspicious_detail: list = field(default_factory=list)

    def ok(self) -> bool:
        """Ren filtrering ar OK; MISSTANKTA null (prissatt produkt utan nyckel) ar
        en akta avvikelse som ska blockera tills bedomd."""
        return self.suspicious_priced_nulls == 0


def prefilter_weave_weights(src: "str | Path" = DEFAULT_SRC,
                            write: bool = True) -> tuple[Path | None, FilterReport]:
    """Filtrera bort icke-prissatta poster (legitim null-nyckel) och FLAGGA
    misstankta null (prissatt produkt utan nyckel). Returnerar (clean_path, report).
    clean_path = None om write=False."""
    import pandas as pd

    src = Path(src)
    rep = FilterReport()
    if not src.exists():
        print(f"[prefilter] SAKNAS: {src}")
        return None, rep

    df = pd.read_excel(src)
    rep.src_rows = len(df)

    if KEY_COL not in df.columns or CATEGORY_COL not in df.columns:
        print(f"[prefilter] kolumn saknas ({KEY_COL}/{CATEGORY_COL}) -- ingen filtrering, "
              "skickar vidare orort.")
        return (src if not write else src), rep

    cat_norm = df[CATEGORY_COL].astype(str).str.lower().str.strip()
    null_key = df[KEY_COL].isna()

    # (a) legitim: null nyckel PA icke-prissatt kategori -> ta bort, logga
    is_unpriced = null_key & cat_norm.isin(UNPRICED_CATEGORIES)
    rep.removed_unpriced = int(is_unpriced.sum())
    if rep.removed_unpriced:
        for mc in MONEY_COLS:
            if mc in df.columns:
                rep.removed_unpriced_revenue += float(
                    pd.to_numeric(df.loc[is_unpriced, mc], errors="coerce").fillna(0).sum())

    # (b) MISSTANKT: null nyckel pa EJ icke-prissatt kategori -> akta avvikelse
    is_suspicious = null_key & ~cat_norm.isin(UNPRICED_CATEGORIES)
    rep.suspicious_priced_nulls = int(is_suspicious.sum())
    if rep.suspicious_priced_nulls:
        cols = [c for c in (CATEGORY_COL, "ItemDescription", *MONEY_COLS) if c in df.columns]
        rep.suspicious_detail = df.loc[is_suspicious, cols].head(20).to_dict("records")

    # Behall allt UTOM de legitima icke-prissatta. (Misstankta lamnas kvar sa de
    # syns nedstroms OCH far kontraktet att blockera -- vi gommer dem inte.)
    clean = df.loc[~is_unpriced].copy()
    rep.kept_rows = len(clean)

    print(f"[prefilter] {src.name}: {rep.src_rows:,} rader in")
    print(f"[prefilter]   borttagna icke-prissatta ({'/'.join(UNPRICED_CATEGORIES)}): "
          f"{rep.removed_unpriced} rader, {rep.removed_unpriced_revenue:,.0f} kr "
          f"(legitimt -- ej prissatta, ska ej ha elasticitet)")
    if rep.suspicious_priced_nulls:
        print(f"[prefilter]   !! MISSTANKT: {rep.suspicious_priced_nulls} null {KEY_COL} pa "
              f"PRISSATT kategori -- akta avvikelse, lamnas kvar (kontraktet blockerar)")
        for r in rep.suspicious_detail[:5]:
            print(f"[prefilter]        {r}")
    print(f"[prefilter]   {rep.kept_rows:,} rader vidare")

    if not write:
        return None, rep

    out = src.with_name(src.stem + "_prefiltered.xlsx")
    clean.to_excel(out, index=False, engine="openpyxl")
    print(f"[prefilter] skrev {out.name}")
    return out, rep


def main() -> int:
    report_only = "--report" in sys.argv
    _, rep = prefilter_weave_weights(write=not report_only)
    if not rep.ok():
        print("\n[prefilter] STATUS: MISSTANKTA null pa prissatt produkt -- bedom fore korning.")
        return 1
    print("\n[prefilter] STATUS: ren (endast legitima icke-prissatta borttagna).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

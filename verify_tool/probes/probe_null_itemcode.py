"""
probe_null_itemcode.py  --  ENGANGS-sond: vad ar de 20 null-ItemCode-raderna?
=============================================================================
Utvecklare: Jens Palmo. Forfattare: Claude advisor.

SYFTE (spike, ej harden)
------------------------
pipeline_contracts hittade 20 rader i Complete_Product_Data.xlsx (FD.14 vav-
vikter) som saknar ItemCode -- nyckeln column_rename_dict_df_product doper om
till ProductKey (det vaven joinar pa). Innan vi DOMER (benign svans? tyst tapp?)
MATER vi. Den har sonden visar de 20 raderna sa du kan avgora.

Detta ar en SPIKE: den ska koras EN gang, ge dig svaret, och sedan slangas.
Beslutet den leder till hardas i pipeline_contracts (justera non_null, eller
lagg en transform som droppar svansen explicit). Probe-to-invariant i praktik.

KOR
---
    py -3.11 probe_null_itemcode.py
"""
from __future__ import annotations
from pathlib import Path

FBL = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\6. Fall Back Logic")
PATH = FBL / "input_data" / "Complete_Product_Data.xlsx"


def main() -> int:
    import pandas as pd
    if not PATH.exists():
        print(f"SAKNAS: {PATH}")
        return 1

    df = pd.read_excel(PATH)
    print(f"Fil: {PATH.name}")
    print(f"Totalt: {len(df):,} rader, {len(df.columns)} kolumner\n")

    if "ItemCode" not in df.columns:
        print("ItemCode-kolumnen finns inte alls -- annan struktur an vantat.")
        print(f"Kolumner: {list(df.columns)}")
        return 1

    null_mask = df["ItemCode"].isna()
    n_null = int(null_mask.sum())
    print(f"Rader med null ItemCode: {n_null}\n")
    if n_null == 0:
        print("Inga null -- inget att granska (kanske redan atgardat).")
        return 0

    # Visa hela de drabbade raderna. Ar de tomma overallt (svans)? Eller bar de
    # data men saknar bara nyckeln (tyst tapp)?
    nulls = df[null_mask]

    # Hur fyllda ar de pa OVRIGA kolumner? (helt tomma rader = benign svans)
    other_cols = [c for c in df.columns if c != "ItemCode"]
    fill = nulls[other_cols].notna().sum(axis=1)
    print("Hur manga AV-NOLLA falt har varje null-rad (av "
          f"{len(other_cols)} ovriga kolumner)?")
    print(f"   helt tomma (0 falt)         : {int((fill == 0).sum())}")
    print(f"   nastan tomma (1-2 falt)     : {int(((fill >= 1) & (fill <= 2)).sum())}")
    print(f"   delvis fyllda (3+ falt)     : {int((fill >= 3).sum())}")
    print()

    # Bar de nagon omsattning? En rad utan nyckel MEN med pengar = verklig tapp.
    money_cols = [c for c in ("SalesTotal", "SalesTotal_YearEnding25") if c in df.columns]
    if money_cols:
        for mc in money_cols:
            vals = pd.to_numeric(nulls[mc], errors="coerce")
            nonzero = int((vals.fillna(0) != 0).sum())
            total = float(vals.fillna(0).sum())
            print(f"   {mc}: {nonzero} rader med varde != 0, summa {total:,.0f}")
        print()

    # Skriv ut de faktiska raderna (forsta ~25) sa du SER vad de ar.
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 30)
    print("De drabbade raderna (forsta 25):")
    print(nulls.head(25).to_string())
    print()

    # Dom-hjalp (inte dom -- du avgor):
    if int((fill == 0).sum()) == n_null:
        print(">>> TOLKNING: alla null-rader ar HELT TOMMA -> benign svans "
              "(Alteryx-export lamnar ofta tomrader). Atgard: droppa explicit "
              "i en transform, eller satt non_null=[] for denna input i kontraktet "
              "OM du forst bekraftar att Fall_Back_Logic redan droppar dem.")
    elif money_cols and any(
        int((pd.to_numeric(nulls[mc], errors="coerce").fillna(0) != 0).sum()) > 0
        for mc in money_cols
    ):
        print(">>> TOLKNING: minst en null-rad bar OMSATTNING men saknar nyckel "
              "-> POTENTIELL TYST TAPP. Vaven kan inte joina dessa produkter. "
              "Granska hur Fall_Back_Logic hanterar null ProductKey FORE du tystar "
              "kontraktet. Detta ar exakt den klass 73%-droppen tillhorde.")
    else:
        print(">>> TOLKNING: null-rader bar viss data men ingen omsattning. "
              "Troligen benigna men bekrafta mot Fall_Back_Logic:s join innan "
              "du andrar kontraktet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

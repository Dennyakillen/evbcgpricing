"""
Diagnos: var fÃ¶rsvinner AAP130 och 60% av KEY mellan BCG-facit och vÃ¥r output?

Kollar tre lager:
1. BCG fryst facit (3812 KEY fÃ¶rvÃ¤ntat)
2. VÃ¥r vÃ¤xande input CSV (det vi matar in i pipelinen)
3. VÃ¥r vÃ¤xande output (1521 KEY fÃ¶rvÃ¤ntat)
"""
import pandas as pd
from pathlib import Path

BCG_FACIT = Path(
    r"C:\Users\jepa02\OneDrive - Evidensia DjursjukvÃ¥rd AB"
    r"\Datastrategi\BCG\BCG_orginal_V2_New"
    r"\02. Elasticity\2. Product Cluster Level Models\output\model\output_summary.xlsx"
)
PIPELINE_ROOT = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models")
VART_OUTPUT = PIPELINE_ROOT / "_archive_growing_2026-04-27" / "output_summary.xlsx"
VART_INPUT  = PIPELINE_ROOT / "data" / "0828_Sweden_weekly_model_data_P_C.csv"

print("=" * 75)
print("AAP130 â€” finns var?")
print("=" * 75)

# 1. BCG fryst facit
print("\n[1] BCG fryst facit:")
df_bcg = pd.read_excel(BCG_FACIT)
print(f"    Kolumner: {list(df_bcg.columns)}")
aap_bcg = df_bcg[df_bcg["KEY"].str.contains("AAP130", na=False)]
print(f"    AAP130-rader: {len(aap_bcg)}")
if len(aap_bcg) > 0:
    print(f"    Exempel: {aap_bcg['KEY'].tolist()[:7]}")
print(f"    Totalt KEY: {df_bcg['KEY'].nunique()}, totalt rader: {len(df_bcg)}")

# 2. VÃ¥r vÃ¤xande output
print("\n[2] VÃ¥r vÃ¤xande output:")
df_v = pd.read_excel(VART_OUTPUT)
aap_v = df_v[df_v["KEY"].str.contains("AAP130", na=False)]
print(f"    AAP130-rader: {len(aap_v)}")
if len(aap_v) > 0:
    print(f"    Exempel: {aap_v['KEY'].tolist()[:7]}")
print(f"    Totalt KEY: {df_v['KEY'].nunique()}, totalt rader: {len(df_v)}")

# 3. VÃ¥r vÃ¤xande input CSV (pipelinen fÃ¥r denna som indata)
print("\n[3] VÃ¥r vÃ¤xande input CSV:")
df_in = pd.read_csv(VART_INPUT, encoding="cp1252", low_memory=False)
print(f"    Kolumner (fÃ¶rsta 12): {list(df_in.columns)[:12]}")
if "ItemCode" in df_in.columns:
    n_aap = (df_in["ItemCode"] == "AAP130").sum()
    print(f"    AAP130-rader (vecko-data): {n_aap}")
    if n_aap > 0:
        sub = df_in[df_in["ItemCode"] == "AAP130"]
        if "Cluster" in sub.columns:
            print(f"    Distinct Cluster fÃ¶r AAP130 i input: {sub['Cluster'].unique().tolist()}")
    print(f"    Totalt distinct ItemCode i input: {df_in['ItemCode'].nunique()}")
print(f"    Totalt rader i input: {len(df_in)}")

# === TÃ¤ckningsgrad ===
print("\n" + "=" * 75)
print("TÃ„CKNINGSGRAD per lager")
print("=" * 75)

n_bcg = df_bcg["KEY"].nunique()
ic_bcg = set(df_bcg["KEY"].str.split("-").str[-1].unique())

n_v_out = df_v["KEY"].nunique()
ic_v_out = set(df_v["KEY"].str.split("-").str[-1].unique())

ic_v_in = set(df_in["ItemCode"].unique()) if "ItemCode" in df_in.columns else set()

print(f"\nBCG fryst facit:        {n_bcg:>6} KEY  /  {len(ic_bcg):>5} distinct ItemCode")
print(f"VÃ¥r input CSV:                /  {len(ic_v_in):>5} distinct ItemCode")
print(f"VÃ¥r output:             {n_v_out:>6} KEY  /  {len(ic_v_out):>5} distinct ItemCode")

print(f"\nItemCodes i input som EJ i output: {len(ic_v_in - ic_v_out)} / {len(ic_v_in)}")
print(f"  (bortfall under pipelinen)")
print(f"\nItemCodes i BCG men EJ i vÃ¥r output: {len(ic_bcg - ic_v_out)} / {len(ic_bcg)}")
print(f"  Exempel pÃ¥ saknade: {sorted(list(ic_bcg - ic_v_out))[:15]}")

print(f"\nItemCodes i BCG men EJ i vÃ¥r INPUT (DW-bortfall): {len(ic_bcg - ic_v_in)} / {len(ic_bcg)}")
print(f"  Exempel: {sorted(list(ic_bcg - ic_v_in))[:15]}")

# === OmsÃ¤ttning per lager ===
print("\n" + "=" * 75)
print("OMSÃ„TTNING â€” fÃ¶r validering mot externa rapporter")
print("=" * 75)

print("\nVÃ¥r input CSV (2022-07-01 â†’ 2026-04-27):")
for col in ["SalesTotal", "TotalNet", "SoldQuantity", "NoofUnits"]:
    if col in df_in.columns:
        total = df_in[col].sum()
        print(f"  Sum {col:<15}: {total:>20,.0f}")

if "ID_Department" in df_in.columns:
    print(f"\n  Distinct Departments: {df_in['ID_Department'].nunique()}")

date_col = None
for c in ["Date", "YearWeek", "Week", "WeekStart"]:
    if c in df_in.columns:
        date_col = c
        break

if date_col:
    print(f"  Datumkolumn: {date_col}")
    print(f"  Antal distinkta perioder: {df_in[date_col].nunique()}")
    print(f"  FÃ¶rsta: {df_in[date_col].min()}")
    print(f"  Sista:  {df_in[date_col].max()}")

print("\n=== KLAR ===")


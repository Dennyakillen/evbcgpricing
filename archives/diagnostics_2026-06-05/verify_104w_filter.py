"""
Verifiera 103-veckors-filtret på vår växande input.
Per KEY-resolution: räkna unika veckor per Cluster × ItemCode-par.
Det är så data_prepration.py filtrerar.
"""
import pandas as pd
from pathlib import Path

CSV = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv")

df = pd.read_csv(CSV, encoding="cp1252", encoding_errors="ignore", low_memory=False)
df["ItemCode"] = df["ItemCode"].astype(str).str.strip().str.upper()

# Bygg KEY som pipelinen gör: Cluster + "-" + ItemCode (alternativt redan i CSV)
if "Cluster" in df.columns:
    df["KEY"] = df["Cluster"].astype(str) + "-" + df["ItemCode"]
else:
    print("Cluster-kolumn saknas")
    raise SystemExit(1)

# Per KEY: räkna unika veckor
weeks_per_key = df.groupby("KEY")["week_starting_monday"].nunique().reset_index()
weeks_per_key.columns = ["KEY", "n_weeks"]

print("=" * 75)
print("Veckor per KEY i input-CSV")
print("=" * 75)
print(f"Total distinct KEY: {len(weeks_per_key)}")
print(f"KEY med > 103 veckor (passerar filtret): {(weeks_per_key['n_weeks'] > 103).sum()}")
print(f"KEY med <= 103 veckor (DROPPAS): {(weeks_per_key['n_weeks'] <= 103).sum()}")
print()
print(f"Distribution av veckor per KEY:")
print(weeks_per_key["n_weeks"].describe().round(1).to_string())
print()
print(f"Histogram-buckets:")
bins = [0, 26, 52, 78, 103, 130, 156, 200, 250]
labels = ["0-26 (6m)", "27-52 (1y)", "53-78 (1.5y)", "79-103 (FILTRET)", "104-130", "131-156", "157-200", "201+"]
weeks_per_key["bucket"] = pd.cut(weeks_per_key["n_weeks"], bins=bins, labels=labels, include_lowest=True)
print(weeks_per_key["bucket"].value_counts().sort_index().to_string())
print()

print("=" * 75)
print("AAP130 per cluster")
print("=" * 75)
aap130 = weeks_per_key[weeks_per_key["KEY"].str.contains("AAP130")]
print(aap130.to_string(index=False))
print()
print(f"AAP130: {len(aap130)} KEY total, {(aap130['n_weeks'] > 103).sum()} passerar filtret")
print()

print("=" * 75)
print("Andra exempel-koder")
print("=" * 75)
for code in ["AAP115", "AAP120", "DUS112", "SBAS0004", "OVR0001"]:
    sub = weeks_per_key[weeks_per_key["KEY"].str.contains(code, regex=False)]
    if len(sub) > 0:
        pass_count = (sub['n_weeks'] > 103).sum()
        print(f"\n{code}: {len(sub)} cluster-KEY, {pass_count} passerar 103-filtret")
        print(sub.to_string(index=False))

print()
print("=" * 75)
print("OMSATTNING-VALIDERING (Jens specifikt onskar detta)")
print("=" * 75)
print()
print("Vart input-fil (vaxande fonster 2022-07 -> 2026-04):")
print(f"  Total rader: {len(df):,}")
print(f"  Total TotalNet (brutto inkl VAT): {df['TotalNet'].sum():,.0f} SEK")
if "TotalNetXVat" in df.columns:
    print(f"  Total TotalNetXVat (netto ex VAT): {df['TotalNetXVat'].sum():,.0f} SEK")
print(f"  Total SoldQuantity: {df['SoldQuantity'].sum():,.0f}")
if "NoofUnits" in df.columns:
    print(f"  Total NoofUnits: {df['NoofUnits'].sum():,.0f}")
print()

# Period-uppdelad omsattning
print("Per ar (for jamforelse mot externa rapporter):")
df["year"] = pd.to_datetime(df["week_starting_monday"]).dt.year
year_summary = df.groupby("year").agg(
    rader=("KEY", "count"),
    TotalNet=("TotalNet", "sum"),
    SoldQuantity=("SoldQuantity", "sum"),
).round(0)
print(year_summary.to_string())
print()

# Frusen fonster (BCG:s 2022-07-01 -> 2025-06-28)
print("Frusen fonster delmangd (BCG:s 2022-07-01 -> 2025-06-28) for direkt jamforelse:")
mask = (df["week_starting_monday"] >= "2022-07-01") & (df["week_starting_monday"] <= "2025-06-28")
frozen = df[mask]
print(f"  Rader: {len(frozen):,}")
print(f"  Total TotalNet: {frozen['TotalNet'].sum():,.0f} SEK")
print(f"  Total SoldQuantity: {frozen['SoldQuantity'].sum():,.0f}")
print()
print("BCG facit (frusen fonster, fran tidigare loggar):")
print("  Sum TotalNet: 6,505,900,000 SEK (var fryst replikering pa validerings-CSV)")
print("  Skillnad: jamfor frozen vs BCG ovan")

# Drop summa for de KEY som droppas av 103-filtret
print()
print("=" * 75)
print("VAD DROPPAS AV 103-VECKORS-FILTRET?")
print("=" * 75)
dropped_keys = weeks_per_key[weeks_per_key["n_weeks"] <= 103]["KEY"].tolist()
df["dropped"] = df["KEY"].isin(dropped_keys)
dropped_rows = df[df["dropped"]]
print(f"Antal KEY som droppas: {len(dropped_keys)}")
print(f"Antal rader som droppas: {len(dropped_rows):,}")
print(f"Total TotalNet som droppas: {dropped_rows['TotalNet'].sum():,.0f} SEK")
print(f"Andel av total omsattning som droppas: {100 * dropped_rows['TotalNet'].sum() / df['TotalNet'].sum():.1f}%")

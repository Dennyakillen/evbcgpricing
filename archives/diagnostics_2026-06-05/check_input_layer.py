import pandas as pd
from pathlib import Path

CSV = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv")

df = pd.read_csv(CSV, encoding="cp1252", encoding_errors="ignore", low_memory=False)
df["ItemCode"] = df["ItemCode"].astype(str).str.strip().str.upper()

print(f"Var vaxande input CSV: {len(df):,} rader, {df['ItemCode'].nunique()} distinct ItemCode")
print(f"Datumfonster: {df['week_starting_monday'].min()} -> {df['week_starting_monday'].max()}")
print()

for code in ["AAP130", "DUS112", "AAP115", "AAP120"]:
    n = (df["ItemCode"] == code).sum()
    if n > 0:
        sub = df[df["ItemCode"] == code]
        clusters = sub["Cluster"].unique() if "Cluster" in sub.columns else []
        weeks = sub["week_starting_monday"].nunique()
        sales = sub["TotalNet"].sum() if "TotalNet" in sub.columns else 0
        print(f"{code}: {n} rader, {weeks} veckor, {len(clusters)} cluster, sum TotalNet = {sales:,.0f}")
        print(f"  Cluster: {sorted(clusters)}")
    else:
        print(f"{code}: SAKNAS i input")

print()
print("Total omsattning i var input (for jamforelse mot externa rapporter):")
print(f"  Sum TotalNet: {df['TotalNet'].sum():,.0f} SEK")
if "TotalNetXVat" in df.columns:
    print(f"  Sum TotalNetXVat: {df['TotalNetXVat'].sum():,.0f} SEK")
print(f"  Sum SoldQuantity: {df['SoldQuantity'].sum():,.0f}")

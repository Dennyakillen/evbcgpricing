"""
TEST AV DEFINITIV ROTORSAK:
Hypotes: ProductGroupL4Name (Service) saknas (NULL) for vissa ItemCodes i var input.
yoy_seasonality() pa rad 345 inner-mergar pa service+week -> NULL service drops.

Detta forklarar varfor AAP130 (som finns i input med 7 cluster x 201 veckor)
ar HELT borta i output men OVR0001 (med exakt samma struktur) ar med.
"""
import pandas as pd
from pathlib import Path

CSV = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv")

df = pd.read_csv(CSV, encoding="cp1252", encoding_errors="ignore", low_memory=False)
df["ItemCode"] = df["ItemCode"].astype(str).str.strip().str.upper()

print("=" * 75)
print("Test 1: ProductGroupL4Name fyllningsgrad i input")
print("=" * 75)
total = len(df)
nonnull = df["ProductGroupL4Name"].notna().sum()
nullcount = df["ProductGroupL4Name"].isna().sum()
print(f"Total rader: {total:,}")
print(f"  ProductGroupL4Name non-null: {nonnull:,} ({100*nonnull/total:.1f}%)")
print(f"  ProductGroupL4Name NULL:     {nullcount:,} ({100*nullcount/total:.1f}%)")
print()

print("=" * 75)
print("Test 2: Per ItemCode - har den NULL ProductGroupL4Name?")
print("=" * 75)
per_code = df.groupby("ItemCode")["ProductGroupL4Name"].apply(
    lambda x: pd.Series({
        "n_rows": len(x),
        "n_null_pg4": x.isna().sum(),
        "n_nonnull_pg4": x.notna().sum(),
        "pct_null": 100 * x.isna().sum() / len(x),
    })
).unstack()

# Hur manga ItemCodes har 100% NULL pg4?
all_null = per_code[per_code["pct_null"] == 100.0]
no_null = per_code[per_code["pct_null"] == 0.0]
some_null = per_code[(per_code["pct_null"] > 0) & (per_code["pct_null"] < 100)]

print(f"ItemCodes total: {len(per_code)}")
print(f"  Med 100% NULL pg4 (HELT borta i output):   {len(all_null)}")
print(f"  Med 0% NULL pg4 (helt OK):                  {len(no_null)}")
print(f"  Med blandat (drops partially):              {len(some_null)}")
print()

print("Forsta 20 ItemCodes med 100% NULL pg4:")
print(sorted(all_null.index.tolist())[:20])
print()

print("=" * 75)
print("Test 3: Specifika koder - AAP130 vs OVR0001")
print("=" * 75)
for code in ["AAP130", "AAP115", "AAP120", "DUS112", "DUS111", "OVR0001", "SBAS0004"]:
    sub = df[df["ItemCode"] == code]
    if len(sub) == 0:
        print(f"{code}: SAKNAS")
        continue
    pg4_values = sub["ProductGroupL4Name"].value_counts(dropna=False)
    pct_null = 100 * sub["ProductGroupL4Name"].isna().sum() / len(sub)
    print(f"\n{code}: {len(sub)} rader, {pct_null:.0f}% NULL pg4")
    print(f"  pg4 values:")
    for val, count in pg4_values.head(5).items():
        print(f"    {val!r}: {count}")

print()
print("=" * 75)
print("SLUTSATS")
print("=" * 75)
if len(all_null) > 0:
    print(f"\n>>> {len(all_null)} ItemCodes har 100% NULL ProductGroupL4Name <<<")
    print(f">>> Dessa droppas i yoy_seasonality() inner merge <<<")
    print(f">>> Detta forklarar varfor input har 1151 ItemCodes men output bara ~{1151 - len(all_null) - len(some_null)} <<<")
else:
    print("\nIngen ItemCode har 100% NULL pg4. Hypotesen avvisas, sok vidare.")

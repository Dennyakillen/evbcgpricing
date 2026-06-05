import pandas as pd
from pathlib import Path

# BCG:s frusna 0828 - vad har den for pg4-fyllningsgrad?
FACIT = Path(r"C:\Projekt\Business_Analytics\bcg_inputs\0828_Sweden_weekly_model_data_P_C.csv")

df = pd.read_csv(FACIT, encoding="cp1252", encoding_errors="ignore", low_memory=False)
df["ItemCode"] = df["ItemCode"].astype(str).str.strip().str.upper()

print("BCG:s frusna 0828-CSV:")
print(f"  Total rader: {len(df):,}")
print(f"  Distinct ItemCode: {df['ItemCode'].nunique()}")
print(f"  Kolumner: {list(df.columns)[:12]}")
print()

# pg4-fyllningsgrad
if "ProductGroupL4Name" in df.columns:
    nonnull = df["ProductGroupL4Name"].notna().sum()
    nullcount = df["ProductGroupL4Name"].isna().sum()
    print(f"ProductGroupL4Name:")
    print(f"  non-null: {nonnull:,} ({100*nonnull/len(df):.1f}%)")
    print(f"  NULL:     {nullcount:,} ({100*nullcount/len(df):.1f}%)")
    print()

    # Per ItemCode
    per_code = df.groupby("ItemCode")["ProductGroupL4Name"].apply(lambda x: x.notna().any())
    has_pg4 = per_code.sum()
    no_pg4 = (~per_code).sum()
    print(f"  ItemCodes med pg4: {has_pg4}")
    print(f"  ItemCodes utan pg4: {no_pg4}")
    print()

    # AAP130 specifik
    aap130 = df[df["ItemCode"] == "AAP130"]
    if len(aap130) > 0:
        print(f"AAP130 i BCG:s 0828:")
        print(f"  Rader: {len(aap130)}")
        pg4_vals = aap130["ProductGroupL4Name"].value_counts(dropna=False)
        print(f"  pg4-varden:")
        for val, count in pg4_vals.items():
            print(f"    {val!r}: {count}")

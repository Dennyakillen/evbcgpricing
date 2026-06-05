import pandas as pd
from pathlib import Path

CSV = Path(r"C:\Projekt\Business_Analytics\bcg_inputs\0828_Sweden_weekly_model_data_P_C.csv")
df = pd.read_csv(CSV, encoding="cp1252", encoding_errors="ignore", low_memory=False)
df["ItemCode"] = df["ItemCode"].astype(str).str.strip().str.upper()

print("=" * 75)
print("BCG:s pg4-kategorier (vad har de for granularitet?)")
print("=" * 75)
pg4_dist = df.groupby("ProductGroupL4Name").agg(
    n_ItemCodes=("ItemCode", "nunique"),
    n_rows=("ItemCode", "count"),
).sort_values("n_rows", ascending=False)
print(pg4_dist.to_string())
print()
print(f"Total distinct pg4-kategorier: {df['ProductGroupL4Name'].nunique()}")
print()

print("=" * 75)
print("Per ItemCode: konsistent pg4 eller flera olika?")
print("=" * 75)
per_code = df.groupby("ItemCode")["ProductGroupL4Name"].apply(
    lambda x: pd.Series({
        "n_total": len(x),
        "n_pg4_null": x.isna().sum(),
        "n_pg4_nonnull": x.notna().sum(),
        "distinct_pg4": x.dropna().nunique(),
    })
).unstack()

mixed_null = per_code[(per_code["n_pg4_null"] > 0) & (per_code["n_pg4_nonnull"] > 0)]
multi_pg4 = per_code[per_code["distinct_pg4"] > 1]
print(f"ItemCodes med BLANDADE pg4-rader (null + nonnull): {len(mixed_null)}")
print(f"ItemCodes med FLERA olika pg4-varden:               {len(multi_pg4)}")

if len(multi_pg4) > 0:
    print()
    print("Forsta 5 exempel pa ItemCode med olika pg4-varden:")
    for code in multi_pg4.head(5).index:
        vals = df[df["ItemCode"] == code]["ProductGroupL4Name"].dropna().unique()
        print(f"  {code}: {list(vals)}")

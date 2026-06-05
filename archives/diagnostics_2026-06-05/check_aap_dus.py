import pandas as pd
df = pd.read_csv(
    r"C:\Projekt\Business_Analytics\bcg_inputs\0828_Sweden_weekly_model_data_P_C.csv",
    encoding="cp1252", encoding_errors="ignore",
    usecols=["ItemCode"], low_memory=False,
)
df["ItemCode"] = df["ItemCode"].astype(str).str.strip().str.upper()
codes = set(df["ItemCode"].unique())

aap = sorted([c for c in codes if c.startswith("AAP")])
dus = sorted([c for c in codes if c.startswith("DUS")])

print(f"BCG facit total distinct ItemCode: {len(codes)}")
print()
print(f"AAP-koder i BCG facit: {len(aap)}")
print(f"  Exempel: {aap[:15]}")
print()
print(f"DUS-koder i BCG facit: {len(dus)}")
print(f"  Exempel: {dus[:15]}")
print()
print(f"AAP130 i facit: {'AAP130' in codes}")
print(f"DUS112 i facit: {'DUS112' in codes}")

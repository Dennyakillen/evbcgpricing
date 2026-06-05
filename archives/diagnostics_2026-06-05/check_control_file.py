import pandas as pd
from pathlib import Path

CF = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\code\control_files\control_file.xlsx")
df = pd.read_excel(CF)
print(f"control_file.xlsx i lokal repo:")
print(f"  Total KEY: {len(df)}")
print(f"  RUN=YES: {(df['RUN'] == 'YES').sum() if 'RUN' in df.columns else 'RUN-kolumn saknas'}")
print(f"  RUN=NO: {(df['RUN'] == 'NO').sum() if 'RUN' in df.columns else 'N/A'}")
print()

aap130_keys = df[df['KEY'].str.contains('AAP130', na=False)]
print(f"AAP130 i control_file: {len(aap130_keys)} rader")
if len(aap130_keys) > 0:
    print(aap130_keys[['KEY', 'RUN']].to_string(index=False))
else:
    print("  -> AAP130 SAKNAS i control_file. BEKRAFTAR HYPOTESEN.")

print()
print("Forsta 5 KEY i control_file:")
print(df['KEY'].head(5).tolist())

# check_maj_dataprep_csvs.py -- READ-ONLY: vilka CSV:er producerade maj-data_prep? Finns cluster-CSV?
import duckdb
from pathlib import Path
import datetime

SQLOUT = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output")
print("=== CSV:er i SQL-output-mappen (vad producerade data_prep?) ===")
if not SQLOUT.exists():
    print("  [SAKNAS]", SQLOUT)
else:
    for f in sorted(SQLOUT.glob("*.csv")):
        mb = round(f.stat().st_size / 1e6, 1)
        mod = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {f.name:<50} {mb:>8} MB  {mod}")

# Hitta cluster-CSV (P_C = Product x Cluster) och mat dess periodtackning
con = duckdb.connect()
for pat in ["*P_C*.csv", "*cluster*.csv"]:
    for f in sorted(SQLOUT.glob(pat)) if SQLOUT.exists() else []:
        p = str(f).replace("\\", "/")
        print(f"\n=== Periodtackning: {f.name} ===")
        try:
            r = con.sql(f"SELECT MIN(week_starting_monday) mn, MAX(week_starting_monday) mx, "
                        f"COUNT(DISTINCT week_starting_monday) wk "
                        f"FROM read_csv_auto('{p}', encoding='latin-1', header=true)").df()
            print(f"  min={r['mn'].iloc[0]}  max={r['mx'].iloc[0]}  veckor={r['wk'].iloc[0]}")
            print("  -> MAX 2026-05 = maj-data (redo att scp:a); 2026-04 = april (kor om data_prep)")
        except Exception as e:
            print(f"  kunde ej mata: {e}")

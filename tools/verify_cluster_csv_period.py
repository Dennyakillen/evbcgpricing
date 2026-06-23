# verify_cluster_csv_period.py -- READ-ONLY: ar maj-cluster-CSV:n faktiskt maj?
import duckdb
from pathlib import Path

CSV = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output\Sweden_weekly_model_data_P_C.csv")
p = str(CSV).replace("\\", "/")
con = duckdb.connect()
# Lat duckdb auto-detektera encoding (dessa CSV:er ar UTF-8, ej latin-1)
try:
    r = con.sql(f"SELECT MIN(week_starting_monday) mn, MAX(week_starting_monday) mx, "
                f"COUNT(DISTINCT week_starting_monday) wk, COUNT(*) n "
                f"FROM read_csv_auto('{p}', header=true)").df()
    print("=== Sweden_weekly_model_data_P_C.csv (cluster-bransle) ===")
    print(f"  min={r['mn'].iloc[0]}  max={r['mx'].iloc[0]}  veckor={r['wk'].iloc[0]}  rader={r['n'].iloc[0]:,}")
    mx = str(r['mx'].iloc[0])
    if "2026-05" in mx:
        print("  -> MAJ (MAX i 2026-05). Redo att scp:a till VM.")
    elif "2026-04" in mx:
        print("  -> APRIL. INTE maj -- kor om data_prep.")
    else:
        print(f"  -> ovantat slutdatum: {mx}")
except Exception as e:
    print(f"  kunde ej mata: {e}")

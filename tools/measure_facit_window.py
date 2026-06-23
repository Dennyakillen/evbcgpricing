# measure_facit_window.py -- READ-ONLY: var slutar BCG:s frusna facit faktiskt?
# Facit-CSV ar latin-1 (bekraftat: proof_chain 2026-05-28 "facit encoding = latin-1").
# Developer: Jens Palmo. Author: Claude advisor.
import duckdb, os

FACIT = (r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG"
         r"\BCG_orginal_V2_New\02. Elasticity\2. Product Cluster Level Models"
         r"\data\0828_Sweden_weekly_model_data_P_C.csv")

if not os.path.exists(FACIT):
    print("[STOPP] facit-CSV ej funnen:")
    print("  " + FACIT)
    raise SystemExit(1)

p = FACIT.replace("\\", "/")
con = duckdb.connect()
# latin-1 + header=true (facit HAR header enligt BCG-schemat)
READ = "read_csv_auto('" + p + "', encoding='latin-1', header=true)"

cols = con.sql("DESCRIBE SELECT * FROM " + READ).df()
print("Kolumner i facit-CSV:")
print("  " + ", ".join(cols["column_name"].tolist()))

cand = [c for c in cols["column_name"] if any(k in c.lower() for k in ("week", "monday", "date"))]
print("")
print("Datum-liknande kolumner: " + str(cand))
for c in cand:
    try:
        r = con.sql('SELECT MIN("' + c + '") mn, MAX("' + c + '") mx, COUNT(DISTINCT "' + c + '") wk FROM ' + READ).df()
        print("")
        print("  " + c + ":  min=" + str(r["mn"].iloc[0]) + "  max=" + str(r["mx"].iloc[0]) + "  distinkta=" + str(r["wk"].iloc[0]))
    except Exception as e:
        print("  " + c + ": kunde ej aggregera (" + str(e) + ")")

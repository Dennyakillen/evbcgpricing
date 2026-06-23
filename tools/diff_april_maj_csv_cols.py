import subprocess

def cols_of(path):
    h = subprocess.run(["ssh", "azureuser@172.18.148.4", f"head -1 {path}"],
                       capture_output=True, text=True, timeout=30).stdout.strip()
    return [c.strip() for c in h.split(",")]

# April-arkivet (.pre_maj_*) — hitta exakt namn forst
arch = subprocess.run(["ssh", "azureuser@172.18.148.4",
    "ls ~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv.pre_maj_* 2>/dev/null | head -1"],
    capture_output=True, text=True, timeout=30).stdout.strip()

maj = cols_of("~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv")
print(f"MAJ-CSV: {len(maj)} kolumner")
if arch:
    apr = cols_of(arch)
    print(f"APRIL-CSV (arkiv): {len(apr)} kolumner")
    print(f"\n=== I MAJ men EJ april (nya kolumner maj-data_prep lade till) ===")
    for c in maj:
        if c not in apr: print(f"  + {c}")
    print(f"\n=== I APRIL men EJ maj (kolumner maj-data_prep tappade) ===")
    for c in apr:
        if c not in maj: print(f"  - {c}")
    print(f"\n=== Namn-drifter (mellanslag<->understreck) ===")
    aprset = set(apr)
    for c in maj:
        if c not in aprset:
            alt = c.replace("_"," ") if "_" in c else c.replace(" ","_")
            if alt in aprset: print(f"  MAJ '{c}' <-> APRIL '{alt}'")
else:
    print("April-arkiv ej hittat (.pre_maj_*) — visar bara maj-kolumner:")
    for c in maj: print(f"  {c}")

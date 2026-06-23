import subprocess

# Hamta CSV-header fran VM
csv_hdr = subprocess.run(
    ["ssh", "azureuser@172.18.148.4",
     "head -1 ~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv"],
    capture_output=True, text=True, timeout=30).stdout.strip()
csv_cols = set(c.strip() for c in csv_hdr.split(","))

# Hamta config col_type-nycklar fran VM
cfg = subprocess.run(
    ["ssh", "azureuser@172.18.148.4",
     "sed -n '57,120p' ~/bcg/cluster/code/src/config.yml"],
    capture_output=True, text=True, timeout=30).stdout
cfg_keys = set()
for line in cfg.splitlines():
    if ":" in line and "'" in line:
        key = line.split(":")[0].strip()
        if key:
            cfg_keys.add(key)

print("=== CSV-kolumner som SAKNAS i config col_type (kraschar feature_selection) ===")
missing = csv_cols - cfg_keys
for c in sorted(missing):
    # finns en namnvariant i config? (mellanslag<->understreck)
    alt_us = c.replace(" ", "_")
    alt_sp = c.replace("_", " ")
    hint = ""
    if alt_us in cfg_keys: hint = f"  <- config har '{alt_us}' (understreck-drift)"
    elif alt_sp in cfg_keys: hint = f"  <- config har '{alt_sp}' (mellanslag-drift)"
    print(f"  CSV: '{c}'{hint}")
if not missing:
    print("  (inga saknade — alla CSV-kolumner finns i config)")

print("\n=== config-nycklar som INTE ar CSV-kolumner (ofarligt, men FYI) ===")
for c in sorted(cfg_keys - csv_cols):
    print(f"  config: '{c}'")

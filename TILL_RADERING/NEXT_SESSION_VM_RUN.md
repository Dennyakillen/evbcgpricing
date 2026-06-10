# VM-KÖRNING — Cluster pipeline på växande fönster (post-pg4-fix)

**Datum:** 2026-06-05 (kvällsval, kvällskörning)
**Mål:** Producera Cluster output_summary.xlsx med ~4000+ KEY (mot 1521 idag)
**Beräknad tid:** 2.5-3 timmar aktiv tid, 30-60 min total körtid
**VM:** `bcg-poc-vm` (Standard_E16s_v5, 128 GB RAM, IP 172.18.148.4)

---

## FÖRUTSÄTTNINGAR (alla bekräftade)

- [x] Patch applicerad i export_b4b_for_model.py
- [x] Ny CSV producerad: 0828_Sweden_weekly_model_data_P_C.csv (608k rader, 1151 codes)
- [x] 100% pg4-täckning verifierad
- [x] Frusen delmängd diffar -0.043% mot BCG facit (inom 0.5% gate)
- [x] FTE NULL för 19.89% (förväntat, dokumenterat)

---

## STEG A — VM-start och pre-flight (5 min)

### A.1 — Starta VM och kör pre-flight

```powershell
# I PowerShell C:\
cd C:\Projekt\BCG\_session_prep
.\check_env.ps1 -StartVm
```

**Förväntat:** 16+ PASS. VM startad. Spara tid: ~3 min för VM-start.

### A.2 — Verifiera ssh-konnektivitet

```powershell
ssh azureuser@172.18.148.4 "hostname && date && df -h /home/azureuser | tail -1"
```

**Förväntat:** Hostname `bcg-poc-vm`, datum stämmer, /home har > 50 GB ledigt.

---

## STEG B — Ladda upp ny CSV till VM (3 min)

### B.1 — Verifiera fil och storlek lokalt

```powershell
$src = "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv"
Get-Item $src | Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}}, LastWriteTime
```

**Förväntat:** ~85-100 MB, LastWriteTime = nyss.

### B.2 — Identifiera rätt VM-sökväg

```powershell
ssh azureuser@172.18.148.4 "ls -la ~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv 2>/dev/null && echo '---' && ls ~/bcg/cluster/code/control_files/ 2>/dev/null"
```

**Notera:** VM kommer visa gamla 1521-KEY-filen från idag. Den måste raderas i steg C.

### B.3 — Ladda upp (scp)

```powershell
scp $src azureuser@172.18.148.4:~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv
```

**Förväntat:** ~10-30 sek beroende på link.

### B.4 — Verifiera filen på VM

```powershell
ssh azureuser@172.18.148.4 "ls -la ~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv && wc -l ~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv"
```

**Förväntat:** Storlek matchar lokal. Radantal ~608,945 (header + 608,944 data).

---

## STEG C — KRITISKT: Rensa stale control_file (1 min)

**Detta är obligatoriskt.** Utan rensning ärvs gårdagens 1521-KEY-fil och hela körningen blir bortkastad.

```powershell
ssh azureuser@172.18.148.4 "
cd ~/bcg/cluster &&
ls code/control_files/ &&
echo '---' &&
rm -fv code/control_files/control_file.xlsx &&
echo 'Rensning klar:' &&
ls code/control_files/
"
```

**Förväntat:** `control_file.xlsx` borttagen. Eventuella _FULL.xlsx-backups behålls.

---

## STEG D — Steg 1: regular_price.py (~3-5 min)

### D.1 — Starta körning med tee

```powershell
ssh azureuser@172.18.148.4 "
cd ~/bcg/cluster &&
source .venv/bin/activate &&
export BCG_START_DATE='2022-07-01' &&
export BCG_END_DATE='2026-04-27' &&
echo '=== STEG 1: regular_price.py ===' &&
echo 'Start: '`date` &&
python code/regular_price.py 2>&1 | tee ~/run_log_step1.txt &&
echo 'End: '`date`
"
```

### D.2 — Validera utfallet (kritiska loggrader)

```powershell
ssh azureuser@172.18.148.4 "
grep -E 'Number of Unique Products|Number of Rows|Before removing|After removing|Unique Key' ~/run_log_step1.txt
"
```

**Förväntat:**
- `Number of Unique Products: 1151` (mot 1151 idag — samma)
- `Number of Rows: 608944` (mot 610039 idag — ungefär samma)
- `After removing 103 weeks min data` rad: ~520-530k (mot 523k idag)
- `Unique Key Final data frame = ~3000-3050` (mot 3027 idag)

**Rött ljus:** Om "Unique Key Final" är < 2900 eller > 3200 — stoppa, diagnostisera.

---

## STEG E — Steg 2: data_prepration.py (~10-15 min)

### E.1 — Starta körning

```powershell
ssh azureuser@172.18.148.4 "
cd ~/bcg/cluster &&
source .venv/bin/activate &&
export BCG_START_DATE='2022-07-01' &&
export BCG_END_DATE='2026-04-27' &&
echo '=== STEG 2: data_prepration.py ===' &&
echo 'Start: '`date` &&
python code/data_prepration.py 2>&1 | tee ~/run_log_step2.txt &&
echo 'End: '`date`
"
```

### E.2 — Validera utfallet

```powershell
ssh azureuser@172.18.identity.4 "
grep -E 'Unique Key|service|YOY|data_for_model|Final data frame Shape|Saved' ~/run_log_step2.txt
"
```

**Förväntat NU efter pg4-fix:**
- `Unique Key Beginning = ~4500-4900` (mot 1521 idag — DEN KRITISKA SKILLNADEN)
- `Unique Key Data for model = ~4500-4900`
- `data_for_model.csv` sparas med ~500-600k rader

**Rött ljus:** Om "Unique Key Data for model" fortfarande är ~1521 — patchen tog inte. Stoppa.

### E.3 — Verifiera data_for_model.csv-storlek

```powershell
ssh azureuser@172.18.148.4 "
ls -la ~/bcg/cluster/code/data_for_model.csv 2>/dev/null ||
ls -la ~/bcg/cluster/output/regular_price/data_for_model.csv 2>/dev/null ||
find ~/bcg -name 'data_for_model.csv' -exec ls -la {} \;
"
```

**Förväntat:** ~80-90 MB.

---

## STEG F — Steg 3: feature_selection.py i tmux (60-120 min, BAKGRUND)

**Detta är det tunga steget.** Ray-parallellt, Bundle-mässigt: ~5000 grupper × ~20 features.

### F.1 — Skapa output-mappar (CZ.5)

```powershell
ssh azureuser@172.18.148.4 "
cd ~/bcg/cluster &&
mkdir -p output/model/automl/results &&
mkdir -p 'output/regular price' &&
ls -la output/
"
```

### F.2 — Starta i tmux (detacherad, kan stänga ssh)

```powershell
ssh azureuser@172.18.148.4 "
cd ~/bcg/cluster &&
tmux kill-session -t fs 2>/dev/null || true &&
tmux new-session -d -s fs '
  cd ~/bcg/cluster &&
  source .venv/bin/activate &&
  export BCG_START_DATE=\"2022-07-01\" &&
  export BCG_END_DATE=\"2026-04-27\" &&
  echo \"=== STEG 3: feature_selection.py ===\" &&
  echo \"Start: \"\$(date) &&
  python code/feature_selection.py 2>&1 | tee ~/run_log_step3.txt &&
  echo \"End: \"\$(date) &&
  echo \"Exit code: \$?\"
' &&
sleep 3 &&
tmux ls
"
```

**Förväntat:** `fs: 1 windows (created ...)` — sessionen kör.

### F.3 — Poll status var 15:e minut

```powershell
# Kör detta var 15:e minut for status
ssh azureuser@172.18.148.4 "
echo '--- tmux active: ---' && tmux ls 2>&1
echo '' && echo '--- senaste 5 rader log: ---'
tail -5 ~/run_log_step3.txt 2>/dev/null
echo '' && echo '--- CPU/MEM: ---'
top -bn1 | head -10
"
```

**Forskriden:**
- Steg "Filtering data": ~5 min
- Steg "Creating features": ~20-30 min
- Steg "Running feature selection per group": ~30-60 min (Ray-parallellt)
- Total: 60-90 min för 4500-4900 grupper

### F.4 — Detektera att steg 3 är klar

```powershell
ssh azureuser@172.18.148.4 "
if tmux ls 2>&1 | grep -q 'fs:'; then
    echo 'STATUS: Steg 3 körs fortfarande'
    tail -5 ~/run_log_step3.txt
else
    echo 'STATUS: Steg 3 KLAR'
    grep -E 'Saved|Error|Exit code|Pipeline completed' ~/run_log_step3.txt | tail -10
fi
"
```

**Rött ljus om logg innehåller:**
- `MemoryError` → OOM, behöver mer RAM
- `Worker died` → Ray-krasch
- `Exit code: 1` → fel
- Stabil sista rad i 10+ min utan progress → hängd

---

## STEG G — Steg 4: model.py (~20-30 min)

### G.1 — Verifiera att control_file har genererats korrekt

```powershell
ssh azureuser@172.18.148.4 "
ls -la ~/bcg/cluster/code/control_files/ &&
echo '---' &&
python3 -c \"
import pandas as pd
df = pd.read_excel('/home/azureuser/bcg/cluster/code/control_files/control_file.xlsx')
print(f'KEY count: {len(df)}')
print(f'RUN=YES: {(df[\\\"RUN\\\"] == \\\"YES\\\").sum() if \\\"RUN\\\" in df.columns else \\\"NA\\\"}')
print(f'First 5: {df[\\\"KEY\\\"].head().tolist()}')
print(f'AAP130 in control: {df[\\\"KEY\\\"].str.contains(\\\"AAP130\\\").any()}')
\"
"
```

**Förväntat:**
- KEY count: ~4500-4900 (mot 1521 idag — DEN KRITISKA SKILLNADEN)
- RUN=YES: alla
- AAP130 in control: **True** (mot False idag)

**Rött ljus:** Om KEY count ~1521 eller AAP130 fortfarande False — stoppa, diagnos behövs.

### G.2 — Starta model.py

```powershell
ssh azureuser@172.18.148.4 "
cd ~/bcg/cluster &&
source .venv/bin/activate &&
export BCG_START_DATE='2022-07-01' &&
export BCG_END_DATE='2026-04-27' &&
echo '=== STEG 4: model.py ===' &&
echo 'Start: '`date` &&
python code/model.py 2>&1 | tee ~/run_log_step4.txt &&
echo 'End: '`date`
"
```

### G.3 — Validera utfall

```powershell
ssh azureuser@172.18.148.4 "
grep -E 'Saved|Error|output_summary|Pipeline completed|Total|signifikant' ~/run_log_step4.txt | tail -20
"
```

**Förväntat:** "Pipeline completed" + "Saved output_summary.xlsx".

**OBS:** "Pipeline completed" skrivs även vid fel (R7). Kontrollera output_summary.xlsx-filen finns:

```powershell
ssh azureuser@172.18.148.4 "ls -la ~/bcg/cluster/output/model/output_summary.xlsx"
```

---

## STEG H — Hämta hem och deallokera (5 min)

### H.1 — Skapa lokal arkivmapp

```powershell
$archive = "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27_v2"
New-Item -ItemType Directory -Path $archive -Force | Out-Null
New-Item -ItemType Directory -Path "$archive\_run_logs" -Force | Out-Null
Write-Host "Skapat: $archive"
```

### H.2 — Hämta hem alla outputs

```powershell
# Output-filer
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/output_summary.xlsx "$archive\"
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/model_summary.xlsx "$archive\"
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/model_results.csv "$archive\"
scp azureuser@172.18.148.4:~/bcg/cluster/code/control_files/control_file.xlsx "$archive\"

# Loggar
scp azureuser@172.18.148.4:~/run_log_step1.txt "$archive\_run_logs\"
scp azureuser@172.18.148.4:~/run_log_step2.txt "$archive\_run_logs\"
scp azureuser@172.18.148.4:~/run_log_step3.txt "$archive\_run_logs\"
scp azureuser@172.18.148.4:~/run_log_step4.txt "$archive\_run_logs\"

# Visa hämtning
Get-ChildItem $archive -Recurse | Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}
```

### H.3 — Deallokera VM (kritiskt för kostnad)

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --no-wait
Write-Host "VM deallokerad. Bekrafta:"
sleep 30
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" -o tsv
```

**Förväntat:** `VM deallocated`.

---

## STEG I — Validering av output (5 min)

### I.1 — Snabbkoll på output_summary.xlsx

```powershell
$archive = "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27_v2"
cd C:\Projekt\Business_Analytics
& ".\.venv\Scripts\Activate.ps1"

python -c @"
import pandas as pd
df = pd.read_excel(r'$archive\output_summary.xlsx')
print(f'Total KEY: {len(df)}')
print(f'Distinct ItemCode: {df[\"ItemCode\"].nunique()}')
print(f'AAP130 rows: {df[df[\"ItemCode\"] == \"AAP130\"].shape[0]}')
print(f'DUS112 rows: {df[df[\"ItemCode\"] == \"DUS112\"].shape[0]}')
print(f'Significant?: {df[\"Significant ?\"].value_counts().to_dict()}')
print(f'Service column distinct: {df[\"ProductGroupL4Name\"].nunique()}')
"@
```

**Förväntat (success criteria):**
- Total KEY: **~4000-4900** (mot 1521 idag)
- Distinct ItemCode: **~1100-1150** (mot 317 idag)
- AAP130 rows: **7** (mot 0 idag)
- DUS112 rows: **7** (mot 0 idag)
- Service column distinct: **23** (mot ~14 idag)

### I.2 — Kör verify-suite (FR-1..4)

```powershell
cd C:\Projekt\BCG\verify_tool
py -3.11 run_all.py
```

**Förväntat:** FR-1..4 PASS. Replikering bevarad.

### I.3 — Compare growing vs BCG facit

```powershell
cd C:\Projekt\BCG
python compare_elasticity_runs.py
```

Detta visar nu en **äkta** jämförelse mellan vår växande och BCG:s frusna — på samma population.

---

## VID FEL — felsöknings-checklist

| Symptom | Trolig orsak | Åtgärd |
|---|---|---|
| Steg 1 KEY < 2900 | SQL-källan ändrad eller env-var saknas | Verifiera BCG_END_DATE satt + ny CSV laddad |
| Steg 2 KEY ~1521 | Patch tog inte / gammal CSV på VM | Bekräfta CSV-uppladdning, kör validate_extraction lokalt först |
| Steg 3 hänger | OOM eller Ray-krasch | `top -bn1` på VM, kolla MEM% |
| AAP130 saknas i control_file | Pg4-NULL fortfarande | Kör check_pg4_dropout på CSV på VM |
| FTE NULL > 25% | Way 1-fil korrupt | Verifiera FTE_XLSX-vägen + radantal |
| Pipeline completed men output_summary saknas | Fel i sista save | Sök "Error" i run_log_step4.txt |

---

## TIDSESTIMERING

| Steg | Min | Tid |
|---|---|---|
| A: Pre-flight + VM-start | 5 | 0:05 |
| B: scp upload | 3 | 0:08 |
| C: Rensa control_file | 1 | 0:09 |
| D: regular_price.py | 5 | 0:14 |
| E: data_prepration.py | 15 | 0:29 |
| F: feature_selection.py (tmux) | 90 | 1:59 |
| G: model.py | 25 | 2:24 |
| H: Hämta + deallokera | 5 | 2:29 |
| I: Validera | 5 | 2:34 |
| **TOTAL** | | **~2.5h** |

**VM-kostnad:** ~9 kr/h × 2.5h = ~23 kr.

---

*Skapad 2026-06-05 efter pg4-fix + extraktions-validering. Förväntat utfall: ~4000+ KEY från ~1150 ItemCodes, AAP130 + tjänster INKLUDERADE.*

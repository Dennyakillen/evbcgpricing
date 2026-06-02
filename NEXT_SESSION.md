# NEXT_SESSION — Fas F: Cluster-körning på Azure VM (växande fönster)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst
på Evidensia Djursjukvård AB. Följ KÄRNPRINCIPER.md samt relevanta MASTER_*.md.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) att lägga i relevant MASTER_*.md.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing
- **Lokal sökväg:** `C:\Projekt\BCG`
- **Senaste commit på origin/fas-f-fresh-data:** `74f1ab0` — *Add session_prep env-check tool (v3) and update .gitignore*
- **Branch:** `fas-f-fresh-data` (INTE main — Fas F är pågående feature-branch)
- **Venv:** Pipeline-venv (`Pipeline\02. Elasticity\.venv`), Python 3.11.9

**Kompletterande repo:**
- **Business_Analytics:** `C:\Projekt\Business_Analytics` på `main` @ `6ea8116`
  (G7 env-override patchad och pushad föregående session)

---

## Status vid sessionsstart

**Hela förberedelsen för cluster-körning på Azure VM är klar. Nästa session börjar med "tryck kör".**

### Klart (verifierat 2026-06-02)

- ✅ Steg 1 (`regular_price.py`) körd lokalt på växande fönster, 84.8 MB output
- ✅ Steg 2 (`data_prepration.py`) körd lokalt, 70 MB data_for_model.csv
- ✅ Smoke 50 KEY på `feature_selection.py` lyckades (proof-of-concept växande fönster)
- ✅ Full lokal körning av cluster-modell hängde på 50% (OOM på 31 GB → bekräftar VM behövs)
- ✅ Alla 4 inputfiler uppladdade på VM (`~/bcg/cluster/`)
- ✅ `constants.py` G7-patchad på VM (env-overridable, verifierad live)
- ✅ Gamla frusen-resultat arkiverade till `~/bcg/cluster/_archive_frozen_2026-05-26/`
- ✅ `/tmp/ray_spill` skapad (auto-fixas av check_env vid behov)
- ✅ Pipeline-venv på VM funkar (Python 3.11.9, Ray 2.41.0, statsmodels 0.14.4, pandas 2.2.3)
- ✅ check_env.py v3 byggt och pushat (`74f1ab0`)
- ✅ Båda repon committade och pushade

### Referensvärden från senaste check_env-körning

| Mätning | Värde |
|---|---|
| Lokala filer för VM-upload | 132 MB i 4 filer |
| `control_file.xlsx` | KEY=1521, RUN=YES=1521 |
| `data_for_model.csv` rader | 258,905 |
| Datafönster | 2022-07-04 → 2026-04-27 (200 veckor) |
| Unika KEY i data | 1521 (matchar control_file) |
| VM RAM ledigt under inventering | 124 GB av 128 GB |
| VM disk ledigt (`/`) | 118 GB |
| Frozen baseline (BCG-fönster) | 5.8 KB output_summary.xlsx |

### Återstående pending (sessionsmål)

- ⏳ Kör steg 3 (`feature_selection.py`) + steg 4 (`model.py`) på VM
- ⏳ Hämta hem `output_summary.xlsx` för växande fönster
- ⏳ Bygg `compare_elasticity_runs.py` (frusen vs växande rimlighetsanalys)
- ⏳ Dokumentera dagens lärdomar (LB.31-37 + 1 master_python lärdom)

---

## Mål för denna session

### Primärt: Etapp F.X — Cluster-körning på växande fönster

**Syfte:** Producera `output_summary.xlsx` för 1521 KEY på växande fönster (2022-07-04 → 2026-04-27), validera mot frusen baseline, dokumentera resultat.

**Leveranser:**

1. **`output_summary.xlsx`** för växande fönster, hämtad lokalt och arkiverad i `_archive_growing_2026-04-27/`
2. **`compare_elasticity_runs.py`** — script som jämför växande vs frusen output:
   - IB.2-gate (RSQ≥0.5 AND PVALUE≤0.2): antal signifikanta KEY
   - Top-N största elasticitets-förändringar mellan körningar
   - Tecken-flippar (positiva som blev negativa eller tvärtom)
   - Avvikelser > X procent
3. **`LESSONS_BCG.md`** uppdaterad med LB.31-37
4. **`MASTER_PYTHON.md`** uppdaterad med ny Python-lärdom (subprocess Windows)

**Förväntad körtid på VM:**
- Steg 3 (`feature_selection.py`): 30-50 min (1521 KEY vs BCG:s 3812 → kortare)
- Steg 4 (`model.py`): 30-40 min
- **Totalt: 60-90 min**

**Förväntad kostnad:** ~15 kr (VM-tid)

---

## Etappstruktur Fas F

| Etapp | Innehåll | Status |
|---|---|---|
| F.1 | DW-extraktion växande fönster (export_b4b_for_model.py G7) | STÄNGD |
| F.2 | Steg 1+2 lokalt på växande fönster | STÄNGD |
| F.3 | Smoke 50 KEY (proof-of-concept) | STÄNGD |
| F.4 | VM-prep (filer, constants.py G7, ray_spill) | STÄNGD |
| F.5 | check_env-verktyg byggt och validerat | STÄNGD |
| **F.6** | **VM-körning steg 3+4, rimlighetsanalys** | **← DENNA SESSION** |
| F.7 | Reasonableness gate på output, kalibrering | Planerad |
| F.8 | Site- och Bundle-modeller (samma flöde) | Planerad |

---

## Filer att ladda upp vid sessionsstart

### Obligatorisk kontext

| # | Fil | Sökväg |
|---|---|---|
| 1 | KÄRNPRINCIPER.md | Bibliotek/ |
| 2 | MASTER_PYTHON.md | Bibliotek/ |
| 3 | MASTER_AZURE_COMPUTE.md | Bibliotek/ |
| 4 | MASTER_SQL.md | Bibliotek/ |
| 5 | NEXT_SESSION.md | denna fil |

### Referens vid behov

| # | Fil | Sökväg | Syfte |
|---|---|---|---|
| 6 | MASTER_AZURE.md | Bibliotek/ | Token-renewal, ProvetDiscount-kontext |
| 7 | BCG_PRICING_PLAYBOOK.md | C:\Projekt\BCG | Modell-arkitektur referens |
| 8 | UBUNTU_AZURE_VM.md | C:\Projekt\BCG | VM-kommando-referens |
| 9 | LESSONS_BCG.md | C:\Projekt\BCG | Projektspecifika lärdomar |

---

## Pre-flight

### 1. Token-renewal (KRITISKT — token dör efter ~4h)

```powershell
az login --scope https://management.core.windows.net//.default
```

```powershell
az login --scope https://database.windows.net/.default
```

### 2. Pre-flight pre-flight — check_env

```powershell
cd C:\Projekt\BCG\_session_prep
.\check_env.ps1
```

**Förväntat:** ~39 checks, STATUS: WARN eller PASS. Inga FAIL. WARN ok på:
- Git: 2-3 uncommittade filer (PDF + .bak från B_A)
- CODE_INTEGRITY: `feature_selection.py` har `C:\\` lokalt (men EJ på VM)
- STORAGE: stora filer kvar (azure_run_dataprep_* etc)

### 3. Git-status

```powershell
cd C:\Projekt\BCG
git log --oneline -3
git status
```

**Förväntat:** senaste commit `74f1ab0`, branch `fas-f-fresh-data`.

### 4. Full kedjekontroll med VM (~5 kr, 7 min)

```powershell
cd C:\Projekt\BCG\_session_prep
.\check_env.ps1 -StartVm
```

**Förväntat:** Alla VM-INNER checks PASS, `/tmp/ray_spill` ev `[FIX]` (auto-skapas),
constants.py G7-hash `[INFO]` (förväntat skiljer mot lokal — vi har patchat VM separat).
Slutet: `VM deallocated. Ingen mer kostnad tickar.`

---

## Sessionens huvudkörning — VM-pipeline

### A) Manuell VM-start (alternativt — om check_env -StartVm redan körts)

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
Start-Sleep -Seconds 60
ssh azureuser@172.18.148.4 "echo SSH OK"
```

### B) Säkerställ `/tmp/ray_spill` (försvinner efter VM-omstart, CZ.5)

```powershell
ssh azureuser@172.18.148.4 "mkdir -p /tmp/ray_spill && ls -ld /tmp/ray_spill"
```

### C) Starta steg 3 (feature_selection.py) i tmux med env-override

```powershell
ssh azureuser@172.18.148.4 "tmux new -d -s bcgrun 'cd ~/bcg/cluster/code && BCG_END_DATE=2026-04-27 ~/bcg/cluster/.venv/bin/python feature_selection.py 2>&1 | tee ~/run_log_fs_growing.txt'"
```

### D) Status-koll utifrån (var 10-15:e min)

```powershell
ssh azureuser@172.18.148.4 "pgrep -af feature_selection.py; echo '---'; tail -5 ~/run_log_fs_growing.txt; echo '---'; free -h | head -2"
```

**Klart** = `pgrep` tomt + sista loggrad innehåller exit-info.

### E) Steg 4 (model.py) när F klart

```powershell
ssh azureuser@172.18.148.4 "tmux new -d -s bcgmodel 'cd ~/bcg/cluster/code && BCG_END_DATE=2026-04-27 ~/bcg/cluster/.venv/bin/python model.py 2>&1 | tee ~/run_log_model_growing.txt'"
```

### F) Hämta hem resultat

```powershell
$dst = "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27"
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/output_summary.xlsx "$dst\output_summary.xlsx"
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/model_summary.xlsx "$dst\model_summary.xlsx"
scp "azureuser@172.18.148.4:~/run_log_*_growing.txt" "$dst\_run_logs\"
```

### G) DEALLOCATE (KRITISKT — annars tickar kostnaden)

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" --output tsv
```

**Förväntat:** `VM deallocated`

---

## Standarder att följa

### Lärdomar relevanta för denna session

- **CZ.5** — Hårdkodade Windows-sökvägar och saknade output-mappar. `/tmp/ray_spill`
  måste finnas. Auto-fixas av check_env.
- **CZ.6** — tmux för run-to-completion. Detacha med `tmux new -d -s namn`.
  Status från utsidan via `pgrep` + `tail` + `free -h`.
- **CZ.7** — VM löste OOM med marginal. 128 GB räcker. Mät RAM under körning för
  att se headroom.
- **E.3** — Azure-token dör efter 4h. Re-login vid behov mitt under session.
- **L.16** — Verifiera tabellschema/kolumnnamn innan SQL/CSV skrivs. Gäller även
  Python-skript som läser CSV (jag missade detta i v3 check_env initialt).
- **L.43** — Antag aldrig att indata är vad du tror. Verifiera empiriskt.
- **R.7** — Verifiera utfall mot fil, inte mot loggrad.

### Nya lärdomar att fånga (från senaste sessionen)

| ID | Titel | Var |
|---|---|---|
| LB.31 | Tee-Object i PS 5.1 fångar inte stderr även med `2>&1` | LESSONS_BCG.md |
| LB.32 | Ray-OOM på Windows: plateau ≠ återhämtning, mät CPU-tidens tillväxttakt | LESSONS_BCG.md |
| LB.33 | Pre-flight smoke-extrapolation underskattar Ray:s peak-RAM icke-linjärt | LESSONS_BCG.md |
| LB.34 | `/tmp/ray_spill` försvinner vid VM-omstart, måste skapas vid varje session | LESSONS_BCG.md |
| LB.35 | Imports propageras inte automatiskt vid str_replace-patch | LESSONS_BCG.md |
| LB.36 | data_prepration.py:s "Shape"-print loggar input, inte output (~50% diff p.g.a. L4-NULL-dropp) | LESSONS_BCG.md |
| LB.37 | PowerShell-multi-line-regex är opålitlig på Python-källkod, använd Python själv för patches | LESSONS_BCG.md |
| L.42 | `subprocess.run([cmd, args], shell=False)` hittar inte .cmd/.bat på Windows | MASTER_PYTHON.md |

---

## Sessionens viktigaste verktyg

- `check_env.ps1` i `C:\Projekt\BCG\_session_prep\` — ~50 checks på 10 sek
- VM_RUN_PLAYBOOK.md (denna fil tjänstgör som playbook tills separat skapas)

---

## Risker och kända begränsningar

- **Token-utgång:** Conditional Access dödar token efter ~70 min - ~4h. Re-login vid behov.
- **Lokal körning omöjlig:** Cluster på 1521 KEY OOM:ar på 31 GB. VM är enda vägen.
- **Tee-Object stderr-bug:** Använd bash på VM (`tee`) istället för PS Tee-Object för pipeline-loggar.
- **tmux dör vid deallocate:** Starta ny session efter VM-omstart.
- **`/tmp/ray_spill` försvinner:** check_env auto-fixar, men måste säkerställas innan tmux startas.
- **`feature_selection.py` lokalt har `C:\\` kvar:** Linux-vägen finns bara på VM. Ladda inte upp lokal version utan portning.

---

## Vid sessionsslut

1. Committa output_summary.xlsx och compare_elasticity_runs.py på `fas-f-fresh-data`
2. Verifiera `git status` är rent
3. Uppdatera denna fil:
   - Ny SHA
   - Startpunkt för nästa etapp (F.7 reasonableness gate)
   - Eventuella nya lärdomar
4. Lägg LB.31-37 i `LESSONS_BCG.md`
5. Lägg ny Python-lärdom i `MASTER_PYTHON.md`
6. Säkerställ att VM är deallocated:
   ```powershell
   az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" --output tsv
   ```
   Förväntat: `VM deallocated`

---

*Skapad: 2026-06-02 vid avslut av session där check_env v3 byggdes (74f1ab0).
Inom 2 minuter ska AI:n kunna läsa filen och utan ytterligare kontext förstå exakt
var projektet befinner sig och vad nästa session ska göra.*

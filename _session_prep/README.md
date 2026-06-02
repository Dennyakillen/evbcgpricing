# _session_prep — Environment check tool v3

**Developer:** Jens Palmö
**Plats:** `C:\Projekt\BCG\_session_prep\`
**Senast uppdaterad:** 2026-06-02

Verktyg som ger fullständig miljö-validering med ~50 kontroller i 9 grupper.
Designat för sessionsstart **och** för presentation inför beslutsfattare.

---

## Snabbstart

### Sessionsstart (gratis, ~10 sek)
```powershell
cd C:\Projekt\BCG\_session_prep
.\check_env.ps1
```

### Full kedjekontroll (kostar ~5 kr, ~7 min)
```powershell
.\check_env.ps1 -StartVm
```

### Snabbkoll utan CSV-läsning (~3 sek)
```powershell
.\check_env.ps1 -SkipData
```

---

## Kontrollgrupper

### LOCAL (~15 checks)

- Båda Git-repon: branch, SHA, working tree-status
- Båda venvs: Python-version, importer
- Azure CLI-token: giltig + rätt subscription
- 4 lokala filer för pipeline-körning
- control_file.xlsx innehåll (KEY, RUN=YES)
- Disk C: ledigt utrymme
- `_archive_growing_2026-04-27/` finns + filräkning
- `_share_to_claude/` flaggas om för stor
- `_session_prep/` finns

### CODE_INTEGRITY (~10 checks)

- MD5-hash av kritiska Python-filer:
  - constants.py
  - feature_selection.py
  - model.py
  - data_prepration.py
  - regular_price.py
- Misstänkta strängar i Linux-körda filer:
  - `C:\\` (hårdkodad Windows-stig)
  - `xlwings` (Windows-only)
  - `import win32` (Windows-only)
- Cross-check mot VM-hashes (vid -VmInner)

### CONFIG (~5 checks)

- config.yml existens + nyckel-räkning
- "Dead config" varning (kända L.39-fall: competitor_data, InScope_Mapping)
- KEY-konsistens: data_for_model.csv = control_file.xlsx
- transform_control_TT.csv struktur

### AZURE (~2 checks)

- VM-status (deallocated/running/stopped)
- VM IP

### PIPELINE_DATA (~10 checks, kräver CSV-läsning)

Läser `data_for_model.csv` direkt och rapporterar:
- Totalt antal rader
- Antal unika KEY (cross-check mot control_file)
- Datafönster (min → max week, antal veckor)
- NULL-räkning i 6 kritiska kolumner
- Förväntade kolumner finns
- Total kolumnantal

### PIPELINE_CTX (~3 checks)

- Frusen baseline (output_summary.xlsx från BCG-fönster)
- Smoke 50 KEY PoC
- Growing output (om producerad)

### HISTORY (~6+ checks)

- Alla `_archive_*`-mappar (filer, storlek)
- Alla `_backup_*`-mappar (filer, storlek)
- Run logs i `_run_logs/`
- Senaste 3 commit-meddelanden (BCG)

### STORAGE (~3 checks)

- `__pycache__`-storlek totalt
- Stora filer (>100 MB) utanför arkiv (varning)
- Backup-filer (.bak) i kod-mappen (varning)

### VM_INNER (~20 checks, kräver VM running)

- SSH-anslutning
- Pipeline-venv på VM (importer)
- Python-version match (lokal vs VM)
- constants.py G7-patch (env-override testas live)
- **MD5-hash av alla kritiska filer på VM, jämfört med lokala**
- `/tmp/ray_spill` (auto-fixas)
- ray_spill-stig i feature_selection.py
- Misstänkta strängar i Linux-körda filer på VM
- 4 input-filer med rätt storlek
- VM control_file KEY-count (cross-check)
- Frusen arkivmapp på VM
- Senaste filändring i output/
- VM RAM/disk (`/` och `/tmp`)

### SUMMARY + EXECUTIVE SUMMARY

Sammanräknad statistik + verbal sammanfattning på svenska, bygger
narrativ från kontrollresultat.

---

## Status-typer

| Status | Betydelse |
|---|---|
| `[PASS]` | Allt OK |
| `[WARN]` | Avvikelse, ej blockerande |
| `[FAIL]` | Blockerande problem, åtgärda |
| `[FIX]`  | Verktyget auto-fixade ett problem |
| `[INFO]` | Informativt värde |
| `[SKIP]` | Check ej körd |

Exit code: `0` om alla PASS, `1` om något FAIL.

---

## Auto-fix

- **`/tmp/ray_spill`** på VM — försvinner vid VM-omstart. Auto-skapas via SSH.

Skippa med `-NoAutoFix`.

---

## Förväntad output (~50 checks)

```
LOCAL                      15
CODE_INTEGRITY              5-10
CONFIG                      4-5
AZURE                       2
PIPELINE_DATA              10
PIPELINE_CTX                3
HISTORY                     6-10
STORAGE                     3
VM_INNER                   20  (om -VmInner)
─────────────────────────────────
Totalt utan VM:           ~50
Totalt med VM:            ~70
```

---

## Filer

- `check_env.py` — Python-modul (~35 KB)
- `check_env.ps1` — PowerShell-wrapper (~3 KB)
- `README.md` — denna fil

---

## Designprinciper

1. **Startar aldrig VM automatiskt.** `-StartVm` är opt-in.
2. **Auto-fix där säkert.** Triviala fel fixas; allt annat rapporteras.
3. **Cross-check mellan lager.** Lokala värden vs VM-värden vs konfig.
4. **Narrativ + teknik.** Både PASS/WARN/FAIL för utvecklare och Executive Summary för beslutsfattare.
5. **Inkrementell.** Lägg till nya checks när nya lärdomar fångas.

---

## Kommande förbättringar (frivilliga)

- Stöd för konfigurerbar `EXPECTED_WINDOW_END` via CLI
- Integration med LESSONS_BCG.md för att lista i Executive Summary
- JSON-snapshot till disk för historisk jämförelse
- Test mot Azure SQL DW (Business_Analytics-domänen)

---

## Kända begränsningar

- Förutsätter sökvägar `C:\Projekt\BCG\` och `C:\Projekt\Business_Analytics\`
- Förutsätter VM `bcg-poc-vm` i `ev-openai-swce-rg-test`
- Förutsätter privat IP `172.18.148.4`
- CSV-läsning tar ~5 sek per fil (skippa med `-SkipData`)

För annat projekt: ändra konstanterna högst upp i `check_env.py`.

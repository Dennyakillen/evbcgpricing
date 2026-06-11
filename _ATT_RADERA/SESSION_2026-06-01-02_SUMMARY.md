# Session 2026-06-01/02 — Sammanställning

**Status:** Avslutad
**Commits:** `74f1ab0` (evbcgpricing) + `6ea8116` (Business_Analytics)
**Längd:** Två sittningar (kväll → morgon) över ca 12 timmar
**Resultat:** VM fullt förberedd för cluster-körning, check_env v3-verktyg byggt och pushat

---

## Vad som åstadkoms

### Tekniskt

1. **DW-extraktion växande fönster validerad** — `export_b4b_for_model.py` G7-patchad,
   producerade `0828_Sweden_weekly_model_data_P_C.csv` (610k rader, 2022-07..2026-04)
2. **Lokal steg 1+2 körda** — `regular_price.py` (84.8 MB) → `data_prepration.py`
   (70 MB data_for_model.csv, 258,905 rader, 1521 KEY)
3. **Smoke 50 KEY validerade** — `feature_selection.py` producerade tolkbara elasticiteter
   på växande fönster (proof-of-concept)
4. **Lokal full cluster-körning misslyckades** (OOM på 31 GB efter 50%) — bekräftar
   userMemories: lokal hård gräns, VM krävs
5. **VM fullt förberedd:**
   - 4 input-filer uppladdade (132 MB)
   - `constants.py` G7-patchad och verifierad live med env-override
   - `/tmp/ray_spill` skapad
   - Gamla frusen-resultat arkiverade till `_archive_frozen_2026-05-26/`
6. **check_env v3 byggt** — ~50 checks i 9 grupper, Executive Summary, auto-fix för
   `/tmp/ray_spill`, MD5-cross-check lokal vs VM, datakvalitets-mätningar från CSV
7. **Git städat** — .gitignore uppdaterad, två rena commits pushade

### Slutsatser

- **Lokal körning är definitivt utesluten** för cluster på växande fönster
  (1521 KEY × 200 veckor → > 31 GB RAM-tak)
- **VM Standard_E16s_v5 har 4x marginal** (124 GB ledigt vid frusen körning maj 26)
- **G7-mönstret fungerar** på både `export_b4b_for_model.py` (DW-extraktion) och
  `constants.py` (pipeline-konstanter) — env-overridable utan att bryta default

---

## Lärdomar att fånga (LB.31-37 + en MASTER_PYTHON)

### LB.31 — Tee-Object i PS 5.1 fångar inte stderr även med `2>&1`

**Symptom:** Pipeline-logg innehöll bara PowerShell:s eget felmeddelande om
Ray, inte Ray:s faktiska progress-rader trots `python ... 2>&1 | Tee-Object`.
Ray loggar till stderr som syns i terminal men hamnar inte i filen.

**Rotorsak:** `Tee-Object` i PS 5.1 fångar bara stdout, inte stderr, även när
stderr omdirigerats till stdout med `2>&1`. Kvarvarande bug i PS-versionen.

**Regel:** För Python-körning där stderr-output måste loggas:
- På VM (bash): använd `python ... 2>&1 | tee logfile.txt` (fungerar korrekt)
- Lokalt PS 5.1: använd `Start-Transcript` eller `*>&1`-omdirigering, INTE
  `2>&1 | Tee-Object`. Eller skicka stderr separat: `python ... 2> stderr.log`

### LB.32 — Ray-OOM på Windows: plateau ≠ återhämtning

**Symptom:** Efter `dlmalloc.cc:129 GetLastError=1450` ("Attempting to recover 25
lost objects"), stabil RAM och stabilt antal Python-processer i 47 minuter.
Tolkades som "Ray återhämtade sig, kör vidare". Faktiskt: processen hängde —
CPU-tid växte med <10% av väntat.

**Rotorsak:** Ray's recovery-flöde kan låsa workers i väntan på resurser som
aldrig blir tillgängliga om systemet är på minneskanten. Stabil RAM + döda
workers = "Ray gav upp", inte "Ray jobbar långsamt".

**Regel:** Vid Ray-OOM med "Attempting to recover" — mät **CPU-tidens
tillväxttakt** över workers. Förväntat: ~50-100% av en CPU-kärna per worker
per minut. Om <10% i 5+ minuter = avbryt körningen, processen hänger.
Ej snapshot av RAM/process-count.

### LB.33 — Pre-flight smoke-extrapolation underskattar Ray:s peak-RAM icke-linjärt

**Symptom:** Smoke 50 KEY lyckades med 13 GB headroom. Extrapolation till
1521 KEY antog linjär skalning → bedömdes som "85% sannolikhet att lyckas".
Faktiskt: full körning OOM:ade vid ~50%.

**Rotorsak:** Ray:s peak-RAM beror på antal **samtidigt aktiva workers med
datakopia**, vilket växer icke-linjärt med batch-volym. Smoke 50 KEY körde
få samtidiga workers; 1521 KEY körde många parallellt.

**Regel:** Pre-flight smoke är bra för "fungerar logiken?" men opålitlig för
"klarar systemet skalan?". Stora körningar på vertikalt begränsad hårdvara →
testa med 30-50% av målmängd, inte 3%. Eller acceptera att lokal körning är
för riskabel och gå direkt till VM.

### LB.34 — `/tmp/ray_spill` försvinner vid VM-omstart

**Symptom:** Skapade `/tmp/ray_spill` manuellt på VM. Stoppade VM över natten.
Nästa morgon: mappen saknades. Pipeline skulle krascha vid Ray-start.

**Rotorsak:** Ubuntu Azure VM:s `/tmp` är inte persistent. Vid VM-omstart
(start efter deallocate) städas `/tmp` rent. Pipeline-koden förutsätter att
mappen finns men skapar den inte själv (CZ.5-fixen är path-byte, inte
mkdir-fix).

**Regel:** Vid varje VM-session (efter start från deallocate): kör
`ssh azureuser@<ip> "mkdir -p /tmp/ray_spill"` innan pipeline startas.
check_env v3 auto-fixar detta vid `-StartVm` eller `-VmInner`.

### LB.35 — Imports propageras inte automatiskt vid str_replace-patch

**Symptom:** Patchade `constants.py` med `datetime.strptime(...)` via
str_replace. Test-import kraschade: `NameError: name 'datetime' is not defined`.

**Rotorsak:** Ursprungsfilen hade inte `from datetime import datetime, timedelta`.
Min patch lade till **användning** av `datetime` utan att lägga till **importen**.
Ren str_replace ser inte sammanhanget.

**Regel:** Patches som introducerar nya beroenden måste **explicit lägga till
imports** — eller verifieras via `python -c "import <modul>"` direkt efter
applikation. Pre-flight test-import är 5 sek arbete som sparar 50 min.

### LB.36 — `data_prepration.py`:s "Shape"-print loggar input, inte output

**Symptom:** Loggraden `Data for model Shape: (523172, 33)` i steg 2. Faktiskt
output `data_for_model.csv`: 258,905 rader (50% av loggat värde).

**Rotorsak:** Print-statementet är placerat **före** YOY-merge som droppar
L4-NULL-grupper. Loggar `df_raw.shape` (input), inte `df_for_model.shape`
(output). Verkligt output är ~50% av loggat värde p.g.a. L4-NULL-dropp.

**Regel:** Verifiera output-storlek mot **fil**, inte mot **loggrad**.
`ls -la output/` eller `pd.read_csv(file).shape` är sanning. Loggrader kan
referera till mellansteg.

### LB.37 — PowerShell-multi-line-regex är opålitlig på Python-källkod

**Symptom:** Försökte patcha `check_env.py` via `-replace`-regex i PowerShell
för att ändra `subprocess.run`-anrop. Multipla patches misslyckades med
"hittades inte exakt" trots korrekt sträng.

**Rotorsak:** PowerShell `-replace` använder .NET regex som behandlar `.` som
"vilken char som helst utom newline" by default. Multi-line strängar med
`\n` matchar inte utan `(?s)`-flagga eller `[regex]::Singleline`.

**Regel:** För patches på Python-källkod — använd ett **Python-skript** kört
från PowerShell, inte direkt-PowerShell-regex. Python `str.replace()` är
exakt strängmatchning, ingen regex-tolkning. Eller `re.DOTALL`-flagga vid
behov.

### L.42 (MASTER_PYTHON) — `subprocess.run([cmd, args], shell=False)` hittar inte .cmd/.bat på Windows

**Symptom:** Python-skript som anropade `subprocess.run(["az", "account", ...])`
gav `WinError 2 — fil kunde inte hittas` trots att `az` fungerar i PowerShell.

**Rotorsak:** På Windows är `az` installerat som `az.cmd`, inte `az.exe`. Python
`subprocess.run` med `shell=False` använder direkt `CreateProcess` som bara
söker efter `.exe`-filer. `shell=True` skulle hjälpa men öppnar för cmd-shell-
problem med JMESPath-queries (`[?...]` tolkas som glob-patterns).

**Regel:** För Windows-CLI-verktyg installerade som `.cmd`/`.bat`:
```python
import shutil
exe = shutil.which("az.cmd") or shutil.which("az")
subprocess.run([exe, "command", "args"], shell=False)
```
`shutil.which()` letar i PATH med standard-Windows-konventioner (.cmd, .bat,
.exe). Sen `shell=False` för säker arg-passning.

---

## Tre obesvarade frågor inför nästa session

1. **PIPELINE_DATA-checken i check_env.py** har en kvarstående bug — gissade
   YOY-kolumnnamn fel. Den faktiska kolumnen heter `YOY_SEASONALITY`, inte
   `pricerelativeequal0_yoy`. Patch designad men ej applicerad p.g.a. tidsbrist.

2. **Lokal `feature_selection.py` har fortfarande `C:\\ray_spill`** kvar i
   kodbasen. VM-versionen är fixad. Risk: någon kopierar lokal version till VM
   utan G7-fix. Värt att portera lokalt också för konsistens?

3. **Tre stora filer kvar utanför arkiv:**
   - `azure_run_dataprep_data_for_model.csv` (152 MB)
   - `all_x_for_models.csv` (212 MB)
   - `model_results.csv` (261 MB)
   Värda att arkivera eller städa? Avgör nästa session efter VM-körning.

---

## Tidsåtgång denna session

| Aktivitet | Tid |
|---|---|
| Lokal cluster-körning + OOM-diagnos (kväll) | ~3 h |
| Dashboard-utveckling + Tee-Object-felsökning | ~1 h |
| VM-prep (start, inventering, scp, constants-patch) | ~1 h |
| check_env v1 design och initial implementation | ~45 min |
| check_env v2 (utbyggnad + executive summary) | ~30 min |
| check_env v3 (~50 checks + alla nya grupper) | ~45 min |
| Patches: az_cmd, JMESPath-helvete, CSV-kolumner | ~45 min |
| Git-städning + commits | ~15 min |
| Dokumentation (denna fil + NEXT_SESSION) | ~30 min |
| **Total session-tid** | **~8 h** |

---

*Skapad: 2026-06-02 14:30 vid sessionsslut. Författare: Jens Palmö (Senior Business
Analyst, Evidensia Djursjukvård AB), assisterad av Claude.*

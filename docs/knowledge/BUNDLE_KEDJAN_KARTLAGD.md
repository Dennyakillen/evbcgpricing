# BUNDLE-KEDJAN — fullständigt kartlagd (maj-fönstret, 2026-06-24)

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia). **Författare:** Claude-rådgivare.
**Syfte:** fånga den fullständiga förståelsen av bundle-kedjan så den inte tappas — bestående
referens som framtida körningar och schema-strukturen följer. Validerad end-to-end via
`bundle_chain_validator.py` + bevisad körning på maj 2026-06-24 (125 KEY, rationality FAIL=0).

> **Varför detta dokument finns:** bundle-kedjan är den mest komplexa av de tre familjerna
> (korsar lokal+VM, har en CSV→xlsx-brygga utan skript, Ray-krav som tvingar VM, namnkonflikter
> i config, ETT G7-lås som missades). Under maj-körningen kartlades varje led empiriskt efter
> att bundle först kraschat i fem olika lager. Detta fångar resultatet så att nästa fönster körs
> uppifrån och ner utan att återupptäcka samma sanningar.

---

## 1. HELA KEDJAN — översikt med miljö per steg

```
[FÖREGÅENDE: data_prep]
  Sweden_masterdata.csv  (DW-export, ~7.3 GB, komma-separerad, InvoiceDate → maj)
  Plats: Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output\

   │  STEG A — convert_masterdata_to_parquet.py          [LOKAL, global py-3.11, DuckDB]
   ▼
  sweden_master_data.parquet  (~834 MB, all_varchar, YearFlag t.o.m. Jun NN)
  Plats: ...\4. Bundle Clinic Data Prep\Sweden_Bundling_Data_Prep\parquet\

   │  STEG B — run_bundle_dataprep.py (00→01→02 SQL)     [LOKAL, global py-3.11, DuckDB]
   ▼
  4 CSV i Sweden_Bundling_Data_Prep\output\:
    - Raw_Data_Clinic_Hospital.csv       (~177 MB, bundle-cluster weekly — C:s input)
    - Sweden_Clinic_Hospital_FTE_Data.csv
    - bundlegroup_bundle_mapping.csv
    - Bundle_Clinic_Data.csv             (exploded membership — EJ C:s output, se §5)

   │  STEG C — 2.Sweden_Bundle_Clinic_Model_Data_Creation.py   [** VM **, Ray, ~17s]
   │           (Ray KRASCHAR lokalt på Windows 31 GB — MÅSTE köras på VM, se §3)
   ▼
  Bundle_Clinic_Data.csv  (10-kolumners model-data — SKRIVER ÖVER B:s likanämnda fil)
  Plats VM: ~/bcg/bundle_dataprep/data/

   │  CSV→XLSX-BRYGGA — bundle_csv_to_xlsx.py (inget BCG-skript gör detta, se §4)
   ▼
  bundle_weekly_model_data_clinic_hospital.xlsx
  Plats VM: ~/bcg/bundle/data/  (där modellen läser)

   │  STEG D — run_bundle_model.py (mapp 5: regular_price→...→model)  [VM, Ray]
   │           FÖRKRAV: G7-patchad constants.py (§6) + automl-mappar finns (§7)
   ▼
  output_summary.xlsx  (~125 KEY)  -- skapas av model.py L516, EJ Step5
  Plats VM: ~/bcg/bundle/output/model/

   │  STEG E — run_all_rationality.py                    [LOKAL]
   ▼
  validation receipts

[KOMMANDE: steg 6]
  Fall_Back_Logic använder output_summary från ALLA familjer (kräver Site+Bundle klara)
```

**Miljö-sammanfattning (KRITISK — bundle korsar miljöer):**
| Steg | Miljö | Varför |
|------|-------|--------|
| A | LOKAL (global py-3.11) | DuckDB streaming, fungerar lokalt |
| B | LOKAL (global py-3.11) | DuckDB SQL, fungerar lokalt |
| **C** | **VM (Ray)** | **Ray kraschar lokalt på Windows 31 GB (access violation) — bevisat 2x** |
| D | VM (Ray) | Modell, tung beräkning, 128 GB |
| E | LOKAL | rationality läser xlsx |

---

## 2. KÄLLOR & SEPARATA PARQUETER (lätt att blanda ihop)

- **Cluster/Site** använder `transaction_data.parquet`
- **Bundle** använder `sweden_master_data.parquet` — EN ANNAN PARQUET
- Båda byggs från samma `Sweden_masterdata.csv` (DW-export) men är separata filer i separata mappar.
- **Konsekvens:** att cluster-maj fungerar betyder INTE att bundle-parqueten har maj. De
  regenereras oberoende. Verifiera alltid bundle-parquetens datumspann separat (grind A).

---

## 3. STEG C MÅSTE KÖRAS PÅ VM — dyrköpt lärdom (LB-kandidat)

**Symptom (lokalt):** `Windows fatal exception: access violation` i Ray:s remote_function.py,
vid `all_bundle_data_creation` (bundle_utils.py ~rad 151), på anropet `build_bundle_for_type.remote()`.

**Rotorsak:** model-data-creation använder Ray (`@ray.remote`, 5 träffar). bundle_utils.py
initierar Ray med `num_cpus=12, object_store_memory=2 GB`. Lokala Windows-maskinen (31 GB)
klarar inte Ray:s shared-memory-allokering → access violation. Samma minnesvägg som hela
modell-pipelinen (därför finns VM:en).

**Bevis:** kraschade identiskt 2026-06-24 OCH i FAS 18 (2026-06-17).

**Regel:** steg C körs ALLTID på VM (~/bcg/bundle_dataprep/). Lokalt kör man BARA A och B (DuckDB, ej Ray).

**VM-körning:**
```
ssh ... 'cd ~/bcg/bundle_dataprep/code && ~/bcg/cluster/.venv/bin/python "2.Sweden_Bundle_Clinic_Model_Data_Creation.py"'
```

---

## 4. CSV→XLSX-BRYGGAN — inget BCG-skript gör detta (LB-kandidat)

**Sanning:** model-data-creation-skriptet slutar med `bundle_data_final_all.to_csv(output_data)`
→ skriver `Bundle_Clinic_Data.csv` (CSV). Men bundle-MODELLEN (regular_price.py) läser
`bundle_weekly_model_data_clinic_hospital.xlsx`. Inget skript i mapp 4 eller 5 konverterar
CSV→xlsx (sökning to_excel/openpyxl = tomt). Hittills gjordes det manuellt i Excel.

**Lösning (permanent):** `tools/bundle_csv_to_xlsx.py` (RAM-lätt, openpyxl, ingen Ray) konverterar
programmatiskt. Körs på VM efter steg C:
```
~/bcg/cluster/.venv/bin/python ~/bundle_csv_to_xlsx.py \
    --csv ~/bcg/bundle_dataprep/data/Bundle_Clinic_Data.csv \
    --xlsx ~/bcg/bundle/data/bundle_weekly_model_data_clinic_hospital.xlsx
```

**10-kolumners struktur (både CSV och xlsx):**
`Clusters, week_starting_monday, Bundle_description, Bundle_code, Bundle_visits, basket_price,
basket_revenue, bundle_visits_per_site, num_of_sites, FTE_Interpolated`

---

## 5. NAMNKONFLIKT — Bundle_Clinic_Data.csv (förvirrande men ofarlig)

**TVÅ steg skriver samma filnamn med olika struktur:**
- **Steg B** (SQL 02_export): exploded bundle membership (header: `Bundle, Products, Visits, ...`)
- **Steg C** (model-data-creation): 10-kolumners model-data

Olika mappar, krockar inte fysiskt. B:s version används INTE nedströms (modellen läser xlsx
byggd från C:s version). Ofarligt, men dokumenterat så ingen tror de är samma fil.

---

## 6. G7-LÅSET — bundle-modellen var ALDRIG G7-patchad (HUVUDROTORSAKEN, LB-kandidat)

**Symptom:** bundle-modellen kördes på maj-input men data_for_model.csv slutade 2025-06-23
(BCG:s frysta fönster), model.py "Finished in 6.57 sec" utan output.

**Rotorsak:** bundle constants.py (mapp 5) hade HÅRDKODADE datum:
```
START_DATE = '2022-07-01'
END_DATE   = '2025-06-29'    ← kapade maj
END_DATE2  = '2025-06-30'
```
Använda som filter i model.py L482 och regular_price.py L224:
`df[(week >= START_DATE) & (week < END_DATE2)]` → all maj-data kapades.

**Cluster + Site G7-patchades i FAS 13. Bundle MISSADES.** Bundle-runnern injicerade redan
`export BCG_START_DATE/BCG_END_DATE` korrekt (run_bundle_model L150), men constants.py läste
aldrig env:en.

**Fix:** `tools/patch_bundle_constants_g7.py` — env-override speglad på cluster:
```
START_DATE = os.environ.get("BCG_START_DATE", "2022-07-01")
END_DATE   = os.environ.get("BCG_END_DATE",   "2025-06-29")
END_DATE2  = (datetime.strptime(END_DATE, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
```
Tomma env = BCG fryst (bit-identisk repro). END_DATE2 HÄRLEDS alltid (+1 dag), aldrig hårdkodad.

**OBS:** patchen kördes på VM. Lokal bundle constants.py (Pipeline-mappen) bör OCKSÅ patchas
så fixen är permanent i repot (annars borta vid nästa upload av lokal constants).

---

## 7. AUTOML-MAPPARNA — feature_selection skapar dem inte själv (LB-kandidat)

**Symptom:** efter G7-fix nådde feature_selection automl-iterationen men kraschade med
`RayTaskError(OSError)` vid `to_excel(f"{summary_path}{mg}_All_itrs.xlsx")` (rad 338).

**Rotorsak:** feature_selection skriver per-KEY xlsx till `output/model/automl/` men har INGEN
`makedirs` — mappen måste finnas. Vår egen cleanup (`rm -rf output/model/*`) raderade den.
FAS 18 hade mappen kvar sedan tidigare körning, så felet syntes aldrig då.

**Fix (snabb):** skapa mapparna före körning:
```
ssh ... 'mkdir -p ~/bcg/bundle/output/model/automl/details ~/bcg/bundle/output/model/automl/results ~/bcg/bundle/output/model/model_objects'
```
**Permanent kandidat:** patcha feature_selection med `os.makedirs(summary_path, exist_ok=True)`.

---

## 8. POLL RAPPORTERAR running=True EFTER KRASCH (LB-kandidat)

**Symptom:** run_bundle_model:s poll visade "running=True | Finished data_prepration.py" i
28 minuter EFTER att pipelinen kraschat (pipeline dog efter 24 sek).

**Konsekvens:** lita ALDRIG på poll-raden för sann status. Mät istället:
```
ssh ... 'tail -20 ~/bcg/logs/<run_id>_p1_bundle.log; pgrep -af launcher.py || echo INGEN'
```
Remote-logg + pgrep = sanning. (Samma klass som LB.60: verifiera mot faktiskt tillstånd.)

---

## 9. STATISKA/FRYSTA STÖDFILER (uppdateras INTE per fönster)

Steg C läser tre filer via config.yml — bara EN växer per fönster:
- `Raw_Data_Clinic_Hospital.csv` — **VÄXANDE** (från steg B)
- `0826_bundle_data.csv` — **STATISK** (bundle-definitioner, BCG)
- `0825_..._june25.xlsx` (FTE) — **FRYST** (FTE-cap 2025-06, LB.14 → NULL FTE för 2025-07+ VÄNTAT)

**Konsekvens för nytt fönster:** ladda BARA upp ny Raw_Data till VM. Stödfilerna finns kvar.

---

## 10. VM-LAYOUT (bundle)

```
~/bcg/bundle_dataprep/          ← STEG C (model-data-creation)
   code/  2.Sweden_..._Model_Data_Creation.py, bundle_utils.py, src/config.yml
   data/  Raw_Data_Clinic_Hospital.csv (uppdateras per fönster), 0826_bundle_data.csv,
          FTE-xlsx (statiska), Bundle_Clinic_Data.csv (C:s output)
~/bcg/bundle/                   ← STEG D (modell)
   code/  launcher.py, regular_price.py, ..., constants.py (G7-patchad), src/config.yml
          control_files/control_file.xlsx (two-pass)
   data/  bundle_weekly_model_data_clinic_hospital.xlsx (modell-input — från xlsx-bryggan)
   output/model/  output_summary.xlsx + automl/ (MÅSTE finnas, §7)
~/bcg/cluster/.venv/            ← DELAD venv (Python 3.11.9, Ray 2.41.0) — Site+Bundle delar Cluster:s
```

---

## 11. KÖRORDNING FÖR NYTT FÖNSTER (sammanfattning, alla fällor inbyggda)

1. **A (lokal):** convert_masterdata_to_parquet.py --bundle-only → grind: parquet har fönstret
2. **B (lokal):** run_bundle_dataprep.py → grind: 4 CSV, Raw_Data har fönstret
3. **upload:** maj-Raw_Data → VM ~/bcg/bundle_dataprep/data/ (upload_input_to_vm.py)
4. **C (VM):** model-data-creation via ~/bcg/cluster/.venv → grind: Bundle_Clinic_Data.csv 10-kol, rader>0
5. **xlsx-brygga (VM):** bundle_csv_to_xlsx.py → VM ~/bcg/bundle/data/
6. **FÖRKRAV D:** (a) constants.py G7-patchad, (b) automl-mappar skapade (mkdir -p), (c) control_file two-pass
7. **D (VM):** run_bundle_model.py --start-date ... --end-date ...
   - pass 1 kraschar på control_file (väntat) → pass 2 laddar → feature_selection automl (~1h, 2639 KEY)
   - → model.py producerar output_summary → benign Step5 (LB.44)
   - grind: output_summary ~125 KEY, visits ≠ föregående fönster (oberoende bevis)
8. **E (lokal):** rationality + status-patch + DEALLOKERA VM

**Validera hela kedjan när som helst:** `py -3.11 verify_tool\probes\bundle_chain_validator.py [--vm]`
**Diagnostisera modell-output:** `~/bcg/cluster/.venv/bin/python ~/bundle_model_output_sond.py` (på VM)

---

## 12. BEVIS PÅ ÄKTA MAJ-KÖRNING (2026-06-24)

| Kriterium | Bevis |
|-----------|-------|
| data_for_model når maj | veckospann → 2026-05-25 (G7-fix; tidigare 2025-06-23) |
| feature_selection körde | ~1h automl-iteration (tidigare 6.57s-krasch) |
| output_summary skapad | 125 KEY, 16:09 lokal hämtning |
| model.py räknade faktiskt | maj-tid >> 6.57s |
| maj ≠ april (oberoende) | SUM_visits 41291 (maj) vs 32854 (april) |
| rimlighet | 85% neg, median -0.213 (FAS 18-ref: 86%, -0.21), rationality FAIL=0 |

# BCG_PRICING_PLAYBOOK — Replikering och migrering av BCG:s prissättningsflöde

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_AZURE.md`
och `MASTER_AZURE_COMPUTE.md`. Linux/bash-handhavande: `UBUNTU_AZURE_VM.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md vid sessionsslut.

**Syfte:** En läsare ska förstå exakt var projektet står, vilka steg vi tagit och ska ta,
vilka beslut som är fattade och vilka som återstår — utan att rekonstruera kontext.

**Projektets natur:** Replikering och migrering, inte utveckling. Vi återskapar BCG:s flöde
faithfully (trogna namn, verbatim-kopia) och städar/rättar *längs vägen*. Designfel loggas
i avsnitt 9 för att specas mot konsult senare — åtgärdas inte nu.

**Nuläge i en mening:** Hela den VM-körbara pipelinen (regular_price → data_prepration →
feature_selection → model) är körd i full skala på Azure och **validerad mot BCG:s frusna facit** —
modellelasticiteten matchar bit-för-bit och vår egen `data_for_model.csv` är bit-för-bit identisk
med BCG:s; endast steg 5 (`data_prep_after_model`, xlwings/Excel) återstår och hör till Windows.

**Senast uppdaterad:** 2026-05-21 (Azure-modellkörning + facit-validering).

---

## 1. Beslut (decision log)

| # | Beslut | Motivering |
|---|---|---|
| D1 | Källa = `BCG_orginal_V2_New` | BCG:s bekräftade slutversion; innehåller v2-fixar |
| D2 | Alteryx skippas helt | SQL-steget ersätter Alteryx; `.yxmd`/`.yxdb` kopieras ej |
| D3 | Allt ut ur OneDrive till `C:\Projekt\BCG` | Löser venv-i-OneDrive, sync-låsning, sökvägs-strul |
| D4 | `duckdb.exe` ersätts av duckdb-Python-paketet | AppLocker blockerar `.exe`; IT: exe är dött |
| D5 | Ray-resurser sätts i `config.yml` (`ray:`-sektionen) per maskin | v2 flyttade parametrarna dit; inget i koden ändras |
| D6 | Interim-input: BCG:s `0828_*` CSV:er tills SQL-steget validerats | Frikopplar modellvalidering från SQL-migrering |
| D7 | Trogna namn, verbatim-kopia i fas 1; städning senare | Spårbarhet, minimera replikeringsfel |
| D8 | Azure blir testmotorn (PoC) — lokal maskin räcker inte | 31 GB RAM → OOM; bevisat 2026-05-20 |
| D9 | VM utan publik IP, i befintligt VNet, nås från kontorsnätet | Tenant-policy förbjuder publika IP:n |
| D10 | Eget Git-repo (`evbcgpricing`), endast våra artefakter | Git för vårt arbete; data/kod bor i V2_New/Azure |
| D11 | PoC-genväg: lånar LZ3-connectivity-subnet, VM-disk ej Blob | Bevis först, elegant drift sen |
| **D12** | **Väg B: kör modellstegen isolerat på BCG:s mellanfil `data_for_model.csv`** | Frikopplar de tunga modellstegen från de blockerade input-stegen (saknad `InScope Mapping.xlsx`) — låter oss validera kärnan utan att vänta på Kent |
| **D13** | **Plattformsanpassningar tillåtna när koden annars ej kan köra på Linux** | Som D4: hårdkodad Windows-sökväg (`C:\ray_spill`) är en plattformsblockerare, ej logik. Minsta möjliga ändring, loggas i §9. Modelllogik rörs aldrig |
| **D14** | **Steg 5 (`data_prep_after_model_output.py`) körs INTE på VM:en** | `import xlwings` kräver Excel + Windows COM. Headless Linux saknar det. Steget är en Windows-/Excel-uppgift per BCG:s design (R9) — egen senare uppgift, ej VM-arbete |

## Öppna beslut

| # | Fråga | Behöver |
|---|---|---|
| O1 | Owner på `ev-openai-swce-rg-test`? | Kent — krävs för dataroller/Blob/ACR, ej för VM-PoC |
| O3 | ~~Krävs `InScope Mapping.xlsx`?~~ | **✅ AVFÄRDAD — död config.** `regular_price.py` refererar aldrig `in_scope_data`/`competitor` (verifierat med `Select-String`). Configen deklarerar filen men koden läser den aldrig. Input-stegen körda utan den |
| O4 | Blob + DW-vyer (spår B, drift) — när? | Efter PoC validerad |

---

## 2. Migreringsfaser

| Fas | Innehåll | Status |
|---|---|---|
| 0 | Orientering, scan, källa & rotorsaker | ✅ KLAR |
| 1 | Replikera struktur + kopiera källor | ✅ KLAR |
| 2 | Miljö: venv + `requirements.txt` (lokalt + Azure) | ✅ KLAR |
| 3 | Ray-config + feature_selection (brute-force, Ray) | ✅ **KLAR — körd fullt på Azure, validerad mot facit** |
| 8 | Azure-motor (PoC): VM, data+kod+venv+körning | ✅ **KLAR — två tunga steg körda i full skala** |
| 4 (model) | OLS-regression per grupp | ✅ **KLAR — körd fullt, bit-för-bit-match mot facit** |
| 7 | Validera output mot facit (KPI/population/features) | ✅ **KLAR — model + feature_selection + data_for_model validerade** |
| **4 (input)** | **regular_price + data_prepration (producerar `data_for_model.csv`)** | ✅ **KLAR — körda; vår `data_for_model.csv` BIT-FÖR-BIT identisk med BCG:s (max diff 1e-15, floating-point-brus)** |
| 5 | `data_prep_after_model` (xlwings/Excel) | ⬜ Windows-uppgift, ej VM (D14) |
| 4 (SQL prep) | SQL data prep (ersätt `duckdb.exe` med Python) | ⬜ Kvar (egen fas, ej replikering utan migrering) |
| 6 | Fall Back Logic (fixa hårdkodade sökvägar) | ⬜ Kvar |
| 9 | Git-baslinje (eget repo) | ✅ Pågående |
| B | DW-vyer + Blob input-folder (drift) | ⬜ Senare |

**Kritisk insikt:** Pipelinen delar sig i en **input-del** (steg regular_price + data_prepration,
blockerade på externa filer från Kent) och en **modell-del** (feature_selection + model, körbara på
vår mellanfil). VM-PoC:en validerade modell-delen. Input-delen är nästa, egen fas — den kräver
`InScope Mapping.xlsx`. Steg 5 (efterbearbetning) är Windows/Excel, utanför VM:en (D14).

---

## 3. Dagens stora lärdomar (2026-05-21)

1. **Bit-för-bit-validering lyckades.** `model.py` kört fullt på Azure (3812 grupper, ~35 min),
   `output_summary.xlsx` jämförd mot facit: elasticitet identisk på alla 3812 (max diff 0,000000,
   korr 1,0). Replikeringen återskapar BCG:s resultat exakt. Konsulternas "solid"-beskrivning bekräftad.
2. **OOM:en var ett RAM-tak, inte algoritmisk.** På 128 GB pegades minnet aldrig (`available` ~83 GB
   under feature_selection, `Swap 0B` genomgående). Ray spillde ~33 GB till `/tmp/ray_spill` utan att
   pressa OS:et. CZ.1 bekräftad i praktik: skala vertikalt, inte kluster.
3. **feature_selection troget replikerat.** Körd fullt (3812 grupper, brute-force/Ray), validerad:
   feature-val identiskt på 93,1%, elasticitet/Adj R2 i praktiken identisk (korr 1,0). De 263 avvikande
   grupperna skiljer på *en* gränsfallsfeature (`negative_media_coverage_flag_jan25` / `No of Sites`)
   utan att påverka elasticiteten — inneboende numerisk instabilitet i brute-force på tröskel-features,
   ej replikeringsfel.
4. **Antal grupper = 3812**, inte ~2450 som tidigare antagits. Justerar tidsförväntan.
4b. **Hela kedjan sluten.** Input-stegen (regular_price + data_prepration) körda; vår egen
   `data_for_model.csv` jämförd mot BCG:s: BIT-FÖR-BIT identisk (max numerisk diff 1e-15 =
   floating-point-brus, 0 text-mismatchar). Enda filskillnaden var radslut (CRLF vs LF). Cirkeln
   sluten: vår input → samma mellanfil → samma modellresultat → matchar facit.
4c. **`InScope Mapping.xlsx` / competitor-data är DÖD CONFIG.** Configen deklarerar dem, men
   `regular_price.py`/`data_prepration.py` refererar dem aldrig (verifierat). Lärdom: läs vad koden
   *gör*, inte vad configen *påstår*. Filerna behövs ej — input-stegen körde rent utan dem.
5. **`C:\ray_spill` hårdkodad i `feature_selection.py` (rad 43)** dödar Linux-körning. Fix: `/tmp/ray_spill`
   (D13). Mappen måste skapas (`mkdir -p`) innan körning. → §9.
6. **`data_prep_after_model` är xlwings-bundet** — kan ej köra på headless Linux (D14, R9 skarp).
7. **Mojibake i produktnamn** (`VeterinÃ¤rkonsultation`) i `model_results` — `cp1252` +
   `encoding_errors='ignore'` i `read_data` sväljer svenska tecken. Påverkar ej siffror. → §9.
8. **tmux frikopplar långa körningar** från SSH/dator. Kör → detacha (`Ctrl+B`, `D`) → kolla utifrån.
9. **Token-utgång bevisad** (`AADSTS70043`, 4 h). Körningen överlevde — den rör inte Azure-API:t.
   Bekräftar Managed-Identity-regeln (CZ.3) för riktig drift.

---

## 4. Azure-läget (fas 8)

| Resurs | Värde |
|---|---|
| Subscription | `ev-lz3-ai (SE)` — `42f726f8-91ee-44d4-832f-9d9ec412ef8f` |
| Resursgrupp | `ev-openai-swce-rg-test` (sandlåda, PIM Contributor) |
| VM | `bcg-poc-vm`, `Standard_E16s_v5` (16 vCPU / 128 GB RAM), Ubuntu 22.04, 128 GB disk |
| Privat IP | `172.18.148.4` (ingen publik — kontorsnät via SSH) |
| VNet/subnet | `ev-lz3-swce-vnet-prod` / `ev-lz3backend-swce-snet-prod` (lånat, D11) |
| Arbetsrot på VM | `~/bcg/cluster/` (`code/`, `data/`, `output/`, `.venv/`) |
| Python | 3.11.9 via uv (isolerad; systemets 3.10 orörd) |
| Status | **Deallocated** — disken består, allt arbete kvar |

**Kostnadsdisciplin (KRITISKT):** VM ~8–10 kr/h igång, nära noll deallokerad. Mönster: `az vm start`
→ jobba → `az vm deallocate`. Deallocate (ej stop) stoppar debiteringen. Driftkort i `README.md`.

---

## 5. Vad pipelinen gör (config-/strukturnivå)

Priselasticitetsmodell för efterfrågan. Beroende variabel: `QuantitySold(SalesTotal>0)`.
Per produktgrupp (`KEY`) körs **OLS-regression** (`statsmodels`); priskoefficienten *är*
elasticiteten (`ELASTICITY_Regular_Price_fwbw_max_6`). Feature-selection är en **brute-force
delmängdssökning** (`itertools`) parallelliserad över Ray. Glesa grupper hanteras via
klustring + fallback/blend (`final_elasticity`). Domänanpassningar: bemanning som kontrollvariabel,
dummies för två negativa medieperioder (mar24/jan25).

**Körordning (launcher):** regular_price → data_prepration → feature_selection → model →
data_prep_after_model. feature_selection skriver `control_file.xlsx`; model läser den.

---

## 6. Riskregister

| ID | Symptom | Rotorsak | Status |
|---|---|---|---|
| R1 🔴→✅ | Ray OOM-krasch | Hårdkodat 80 GB i config | Löst: Azure 128 GB; minnet pegades aldrig |
| R2 🔴 | DuckDB-steget kraschar | Blockerad `duckdb.exe` | Ersätts av Python på Linux (input-fas) |
| R3–R5 🔵→✅ | venv/pip/CWD-strul | Diverse | Lösta |
| R6 🟡→✅ | Hårdkodad sökväg (`C:\ray_spill`) | Ej parametriserad | Löst för Linux (D13); §9 mot konsult |
| R7 🟡 | "Pipeline completed" vid fel | Saknad exit-code | Verifierar alltid output-fil — tillämpad genomgående |
| R8 🟡 | "output from Alteryx" i logg | Ej omdöpt | Spec mot konsult |
| R9 🔵→⚠️ | xlwings/pywin32 | Excel-beroende | **Skarp:** `data_prep_after_model` ej VM-körbart (D14) |
| R10 🔵→✅ | Mojibake i `.ps1` | PS 5.1/CP1252 | Script ASCII |
| **R12b** 🟡 | Mojibake i produktnamn (output) | `cp1252`+`encoding_errors='ignore'` | §9 — påverkar ej siffror |
| **R13** 🔵 | UTF-16-kodad `requirements.txt` | Windows "Unicode"-spar | Löst via `iconv` (MASTER_PYTHON) |
| **R14** 🔵 | scp bär Windows-rättigheter (`dr-x---r-x`) | OS-rättighetsmodeller | Löst: `chmod -R u+w` på egen mapp |

---

## 7. Ray-config (KLAR)

`...\code\src\config.yml`, `ray:`-sektionen. På Azure-VM (128 GB): `cpus: 14`, `memory: 32`,
`batch: 128`. Object store = `memory × 1024³` = 32 GB; spill till `/tmp/ray_spill` (D13).
`feature_selection.py` rörs aldrig utom den enda spill-sökvägsraden.

---

## 8. Vad nästa pass gör (efter VM-kedjan)

**Hela den VM-körbara pipelinen är klar och validerad.** Återstående arbete är inte VM-bundet:

1. **Steg 5 — `data_prep_after_model_output.py`** (Windows/Excel). Körs lokalt med Excel installerat
   (xlwings, D14). Matar in i prismodell-arbetsboken. Egen Windows-session.
2. **SQL data prep** (egen fas, migrering snarare än replikering). Ersätt DuckDB-flödet, ev. mot
   DW-vyer (spår B). Större, eget spår.
3. **Fall Back Logic (fas 6)** — oläst, hårdkodade sökvägar (R6). Egen session.

Varje del är nu en mindre, isolerad session som ärver den infrastruktur vi byggt. Mönstret är satt:
rökstest → full körning → validera mot facit → dokumentera.

---

## 9. Återbesök mot konsult (spec senare)

Maskinspecifik config (delvis fixad i v2) · `.exe`-beroende · "Pipeline completed" vid fel ·
hårdkodade Fall Back-sökvägar · **`C:\ray_spill` hårdkodad spill-katalog (rad 43 feature_selection)** ·
hårdkodade datum i `constants.py` (START/END_DATE, SPECIAL_WEEKS) — filtrerar bort data efter jun 2025 ·
**`cp1252`+`encoding_errors='ignore'` → mojibake i svenska produktnamn** ·
**feature_selectionens känslighet: 263/3812 grupper väljer olika gränsfallsfeature vid numerisk drift
(påverkar ej elasticitet)** · Alteryx-referenser i logg · död config (`reference.csv`/`baseline_control.csv`) ·
`data_prep_after_model` xlwings-bundet (ej Linux-körbart).

---

## 10. Nya lärdomar till MASTER-filerna

**MASTER_PYTHON:**
- Windows-textfiler kan vara UTF-16 (`fffe`/`feff`-BOM + 00-byte/tecken). `xxd` före strip;
  `iconv -f UTF-16 -t UTF-8` på HELA filen, ej bara BOM. CRLF (`0d0a`) ofarligt för pip. (R13)
- `$Args` reserverat i PowerShell; `.ps1` ska vara ASCII (befintliga).

**MASTER_AZURE_COMPUTE:**
- CZ.4: scp bär Windows-rättigheter → `dr-x---r-x`, `sed` failar. `chmod -R u+w ~/egenmapp`
  (aldrig system-/delade kataloger). venv-aktivering gäller per skal — aktivera om i tmux. (R14)
- CZ.3 bekräftad: token dog mitt i session; körning överlevde (rörde ej Azure-API:t).
- tmux för run-to-completion: `tmux new -s namn` → kör med tee → `Ctrl+B D` → kolla utifrån.
- Efter `az vm start`: ge VM:en ~1 min innan ssh. `Connection refused` direkt = vänta, ej fel.
- `/tmp/ray_spill` (skapad med `mkdir -p`) för Ray-spill på Linux; ersätter hårdkodad Windows-sökväg.

**Validering (generell metod):**
- Validera mot facit i lager (population → kolumner → KPI), strikt + tolerant + korrelation.
  Lita inte på en hårdkodad tröskeldom — visa avvikelserna och tänk på vad de betyder
  (brute-force-feature-val kan skilja på gränsfall utan att slutresultatet rörs).

---

*Skapad av Jens Palmö (utvecklare) med AI-rådgivaren. Reviderad 2026-05-21 vid Azure-modellvalidering.*

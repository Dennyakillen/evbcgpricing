# NEXT_SESSION — BCG Pricing (efter PoC-2: modellen facit-validerad på DW-data)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_SQL.md` (Python/Azure-lärdomar
ligger även där tills separata masters skapas), `UBUNTU_AZURE_VM.md`, `BCG_PRICING_PLAYBOOK.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel)
> och lägg i relevant master.

---

## Aktuellt projekt

- **Repo (replikering + golden reference):** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Repo (DW-native arbete):** https://github.com/Dennyakillen/Business_Analytics.git — `C:\Projekt\Business_Analytics` (D-B5)
- **DW:** server `se-az-we-bi-sql-01.database.windows.net`, db `se-az-we-bi-dw-sqldb-01`. Anslutning via
  `data_access.py` (pyodbc + DefaultAzureCredential + .env). `az login --scope https://database.windows.net/.default` (token ~4h).
- **Azure-VM:** `bcg-poc-vm`, deallocated. Full 1311-grupps-körning är en VM-uppgift (ej lokal).

---

## 🟢 MILSTOLPE 2026-05-25 — PoC-2 BEVISAD MOT FACIT

**Kärnfrågan ("kan vi köra BCG:s metod på vår DW-data och få samma svar?") är besvarad: JA, validerat mot facit.**

Hela kedjan kör nu end-to-end lokalt på Evidensias DW-data:
`export_b4b_for_model.py (DW + BCG-seed + BCG-kodurval + FTE)` → `regular_price` → `data_prepration`
→ `make_smoke_control` (CV-urval) → `feature_selection` (per-grupp-features, FTE tvingad in) → `model` → elasticiteter.

**Facit-jämförelsen som stänger frågan (BCG:s `Model_output`-flik i Sweden_Product_Cluster_Elasticity_Dashboard.xlsx):**
- Våra OVR0001-elasticiteter (−0,09…−0,19, icke-sig) **matchar BCG:s** OVR0001 (−0,12 / −0,15, p=0,055 / 0,18).
- **BCG:s egen baslinje: bara 227/1276 (17,8%) rått signifikanta (p<0,05).** Icke-signifikans på fin
  kluster×kod-nivå är NORMALTILLSTÅNDET, inte ett fel. Vår modell beter sig exakt som deras.
- **618/1276 (48,4%) är `Significant ?=1`** — den flaggan = "signifikant ELLER fallback-räddad".
- Fallback-nivåer bekräftade: `New_cluster ∈ {Clinics, Clinics_CH, Hospital_CH, Hospital}`, `big_cluster ∈ {Clinics, Hospital}`.

**Vad det betyder:** det vi länge tolkade som svaga elasticiteter var TROGEN REPLIKERING. BCG får samma
svaga tal på samma koder. PoC-2:s bevisbörda är därmed lyft. Resten är skalning + nedströmssteg, inte bevis.

**Export-rekonciliering (med FTE inne):** 1151 koder (exakt facit), 4930 KEY (−0,38% vs 4949, D-B6-effekt),
brutto 6,502 mdr (−0,06% vs facit), `Sum_FTE_Interpolated NULL: 0`. Trogen nog — diffar flippar inget top-line-beslut.

---

## VAR VI STÅR (korrekt bild efter denna session)

**Pipelinen (folder 2, Cluster) kör verbatim BCG-kod på vår DW-data, end-to-end, validerad mot facit.**
Allt utom två kirurgiska, dokumenterade ändringar är BCG:s kod orörd:
1. **VIF-guard** (`utils.py` rad ~399, try/except runt `variance_inflation_factor`) — latent BCG-bugg
   (VIF körs på params-skalad `X_temp`, singulär på vår data → "zero-size array"). VIF är efterdiagnostik;
   elasticiteten beräknas i `df_coef` FÖRE VIF. Backup: `utils_BCG_verbatim.py.bak` (OBS: överskriven med
   fixad version — verbatim original finns i git/OneDrive). NaN på fel, körningen lever.
2. **`config.yml` cols_needed** — `Sum_FTE_Interpolated` åter inlagd (var borttagen för FTE-lös PoC).

**FTE byggd via Väg 1 (BCG:s färdiga interpolerade fil):** `export_b4b_for_model.py` läser
`Sweden__Interpolated_Productivity_time_date_june25.xlsx`, summerar `FTE_Interpolated` per Cluster×vecka
→ `Sum_FTE_Interpolated` (01_process.sql rad 289-logik), joinar på Cluster+vecka. Transform: RÅ (ej log),
matchar BCG:s `transform_control_TT.csv` (FTE har Transform=NaN). `cols_needed` tvingar in FTE i varje
grupp (`feature_selection.py` rad 310: `features = cols_needed + list(subset)`) — som BCG:s control-fil
(FTE=1 överallt). FTE flyttade INTE signifikansnålen — väntat, eftersom OVR0001 är oelastisk även hos BCG.

**Den verkliga "saknade" biten är inte FTE — det är fallback-logiken** (steg 3/4 nedan), som hanterar de
~82% som inte blir rått signifikanta genom omklustring till Clinics/Hospital-nivå.

---

## DET ENDA SOM ÅTERSTÅR (kritisk väg → affärsmål)

Affärsmålet: köra den (nu facit-validerade) modellen på FÄRSK data, med diffar små nog att inte flippa
top-line-beslut. PoC-2-beviset är klart; återstoden är nedströmssteg + skalning.

| # | Steg | Status | Not |
|---|---|---|---|
| 1 | **PoC-2: b4b (DW) → modell → facit-validera** | ✅ **KLAR** | Bevisad mot Model_output denna session |
| 2 | **Output-rimlighetsgrind** (negativ elasticitet, band, "flippar diffen ett beslut?") | 🔴 nästa | Ersätter facit på färsk data. Bygg FÖRE färsk-körning |
| 3 | Steg 5 — `data_prep_after_model_output.py` (xlwings/Excel, Windows) | 🔴 | **Här bor fallback-logiken.** Slår ihop svaga fina grupper → Clinics/Hospital. Körbar nu |
| 4 | Steg 6 — Fall Back Logic (blend, fixa hårdkodade sökvägar, R6) | 🔴 | Nära kopplad till steg 3. Kräver site/bundle-familjer för full blend |
| 5 | Site (folder 3) + Bundle (folder 5) familjer | 🔴 | För Fall Back-blend |
| 6 | Full körning 1311 grupper på VM | 🔴 | Lokalt = rökstest (10 KEY). Full = VM (CZ.2). feature_selection Ray-parallell |
| 7 | Färsk data: parametrisera datumfönster (G7) + FTE Väg 2 (DW-native) | 🔴 | START_DATE/END_DATE hårdkodat i constants.py |

**Rekommenderad ordning:** output-rimlighetsgrind (steg 2) → fallback/steg 5 (där OVR0001 blir användbar via
omklustring) → familjer → full VM-körning → färsk data. Affärsvärdet sitter i rimlighetsgrind + fallback + färsk data.

---

## FALLBACK — vad nästa session ska göra (steg 3/4)

**Problemet fallback löser:** 82% av grupperna är inte rått signifikanta på fin Cluster×ItemCode-nivå (BCG
själva: 18% rått signifikanta). Fallback slår ihop svaga grupper till grövre nivå där mer data ger signal.

**Bekräftat ur facit (`Model_output`):**
- `New_cluster ∈ {Clinics, Clinics_CH, Hospital_CH, Hospital}` — fyra fallback-nivåer.
- `big_cluster ∈ {Clinics, Hospital}` — grövsta nivån.
- `Significant ?` = signifikant rått ELLER räddad via fallback (618 vs 227).
- `Check`, `Weighted elasticity/rsq/Pvalue`-kolumner = fallback-mekanikens beräkningar.

**Första steg nästa session (LÄS FACIT FÖRST, A.9):**
1. Läs `data_prep_after_model_output.py` i sin helhet (steg 5 i BCG:s flöde, Readme bekräftar ordningen).
2. Läs exakt hur `Significant ?` / `New_cluster` / `Check` beräknas i dashboarden (Jens kör på Windows mot
   OneDrive-filen — Claude når den inte). Det definierar fallback-regeln.
3. Verifiera om fallback ligger i Python (`data_prep_after_model_output.py`) eller i Excel/dashboarden (xlwings).
   Readme antyder Python-steg; dashboardens Weighted-kolumner antyder Excel-lager. Läs båda före bygge.

---

## MODELLKONTRAKTET (oförändrat, nu uppfyllt med FTE)

`KEY = Cluster + '-' + ItemCode`, `dep_var = QuantitySold(SalesTotal>0)`, `PRICE = TotalNet/UNIT`, log-log.
b4b levererar nu ALLA kontraktets kolumner inkl `Sum_FTE_Interpolated`. Kontraktet är uppfyllt.

---

## NYCKELARTEFAKTER DENNA SESSION (i /outputs, dra in i repona)

| Fil | Mål-sökväg | Roll |
|---|---|---|
| `export_b4b_for_model.py` | `C:\Projekt\Business_Analytics\` | DW + BCG-seed + BCG-kodurval + **FTE-join** (Väg 1) |
| `make_smoke_control.py` | `C:\Projekt\BCG\` | v3: väljer KEY på **pris-CV** (ej veckoantal), aktiverar features =1 |
| `fix_config_encoding.py` | `C:\Projekt\BCG\` | Strippar BOM från config.yml (PS-redigerings-fälla) |
| `utils.py` (VIF-guard) | pipeline `code/` | Kirurgisk try/except rad ~399. Backup: `utils_BCG_verbatim.py.bak` |
| `config.yml` (cols_needed) | pipeline `code/src/` | `Sum_FTE_Interpolated` åter i cols_needed |

---

## ÖPPNA BESLUT / TECH DEBT

- **`output_summary`-krasch (model.py rad ~508):** `ELASTICITY_COL` används FÖRE `get_elasticity` skapar
  den (BCG ordningsbugg). OFARLIG — `model_summary.xlsx` sparas rad ~507 (före kraschen). Elasticiteterna
  läses därifrån. Fixas om polerad `output_summary.xlsx` behövs (flytta `get_elasticity` före rad 508).
- **D-B6:** PoC på BCG-kodurval via `Dim_Item_Extended`; KEY −0,38% / brutto −0,06% mot facit = dimensionseffekt, ej fel.
- **G7:** Datumfönster hårdkodat (`constants.py`: START_DATE 2022-07-01, END_DATE 2025-06-29). Vår export
  använder 2025-06-28 = samma vecka, ofarligt. Parametrisera före färsk data.
- **FTE Väg 2 (DW-native):** aggregera `Manual.Fact_Quinyx_DayClinic` (validerad 0% diff) — INTE replikera
  BCG:s Quinyx-rådata-pipeline (Quinyx_h.txt:s 200-raders cost-center-CASE). Skalningssteg för färsk data.
- **Discount-exkludering:** BCG:s assumptions säger "Models built excluding Discount ProductCategoryL4Name".
  Vi exkluderade den INTE. Påverkade troligen inte OVR0001-resultatet (BCG fick samma svaga tal), men
  verifiera vid Väg 2 hur rabatt markeras i vår data (`Master_Underkategori3`, halv-NULL, L.43).
- **Södran-OVR0001:** föll ur modellen genomgående ("Cant model", för få datapunkter efter split). Gränsfall.
- **`ProductGroupL4Name` halv-NULL** i vår data (`Master_Underkategori3`). Biter ej kärnelasticitet; relevant för Väg 2-gruppering.

---

## NYA LÄRDOMAR DENNA SESSION (lägg i MASTER_PYTHON / KÄRNPRINCIPER)

### A.9 (skärpt) — Läs facit-OUTPUT före hypotesdriven bygginsats
**Symptom:** Byggde hel FTE-pipeline + två smoke-omgångar på hypotesen att FTE var den saknade biten för
signifikans.
**Rotorsak:** BCG:s `Model_output` + assumptions-flik visade på 30 sek att BCG också är icke-sig på OVR0001
och att bara 18% är rått signifikanta — vilket hade omdirigerat från "jaga signifikans" till "förstå
fallback" innan FTE byggdes.
**Regel:** När egna resultat är svaga — jämför mot BCG:s FAKTISKA OUTPUT för samma grupper FÖRE nya features
byggs på en hypotes. Dashboardens output ÄR källa (= facit), precis som koden. (FTE behövdes för trogen
replikering oavsett, så ej spillt — men sekvensen var fel.)

### Elasticitet svag ≠ pipeline trasig
**Symptom:** 0 signifikanta på smoke-grupper tolkades först som fel.
**Rotorsak:** OVR0001 ("Other sales, store only") är oelastisk samlingskod; BCG fick samma. Rå signifikans
är 18% även hos BCG. Fallback (omklustring) är hur de når 48%.
**Regel:** Bedöm egna elasticiteter mot BCG:s output PÅ SAMMA KOD, inte mot en absolut "borde vara
signifikant"-förväntan. Icke-signifikans på fin nivå är normaltillstånd; fallback hanterar det.

### Smoke-KEY väljs på pris-CV, inte veckoantal
**Symptom:** Veckoantal-urval gav prisstabila serier (CV 0,0004) → absurd +15,0 elasticitet.
**Rotorsak:** Elasticitet kräver prisVARIATION, inte historik-längd. En kod såld 156 v till samma pris är värdelös.
**Regel:** Rökstest-urval = högst pris-CV bland full-historik-grupper. Veckoantal är fel optimeringsmål för elasticitet.

### Control-filens feature-kolumner är aktiveringsflaggor (VALUE==1)
**Symptom:** model_summary VARIABLE = bara CONST; intercept-only; VIF-krasch.
**Rotorsak:** Smoke-control satte features=NaN. `utils.py` rad 278 väljer features där VALUE==1; NaN≠1 → tom ind_var.
**Regel:** Control-filen BÄR feature_selection-output. Features = 1 för använda. `cols_needed` tvingas dock
in av koden oavsett control-fil (rad 310).

### feature_selection FÖRE model (pipeline-ordning)
**Symptom:** Svaga elasticiteter med fast 2-feature-set.
**Rotorsak:** Körde model.py direkt utan feature_selection. BCG:s control-fil visar per-grupp-features (olika per grupp).
**Regel:** Replikera ordningen: feature_selection (skriver control-filen med per-grupp-features) → model läser den.

### VIF är efterdiagnostik, ej elasticitet
**Symptom:** model.py kraschar i VIF ("zero-size array") trots korrekt OLS.
**Rotorsak:** `utils.py` återanvänder `X_temp` (params-skalad) för baseline → VIF körs på singulär matris.
**Regel:** Elasticiteten finns i `df_coef` FÖRE VIF. Skydda VIF-steget (NaN på fel); verbatim-kod får
kirurgisk PoC-fix, markerad + backup.

### Config-encoding: VS Code, aldrig PS Set-Content -Encoding UTF8
**Symptom:** config.yml kraschar PyYAML ("mapping values not allowed", line 2) efter PS-redigering.
**Rotorsak:** PowerShell 5.1 `Set-Content -Encoding UTF8` skriver UTF-8 BOM (EF BB BF); PyYAML tål ej ledande BOM.
**Regel:** Redigera YAML/config i VS Code (bevarar encoding). Om BOM ändå: strippa (läs bytes, ta bort EF BB BF).

### FTE Väg 2 = via validerad vy, ej rådata-rekonstruktion (bekräftar L.39)
**Symptom:** Stod i begrepp att replikera BCG:s Quinyx-rådata-pipeline (Quinyx_h.txt 200-raders cost-center-CASE).
**Rotorsak:** MASTER_SQL.md visar `Manual.Fact_Quinyx_DayClinic` (validerad 0% diff) som redan gör
mappningen + vets-filtret.
**Regel:** FTE Väg 2 = aggregera den validerade vyn, inte replikera Alteryx-flödet. Läs MASTER-filerna
(facit) före nytt dataflöde — de listar validerade vyer som ofta löser uppströmssteget.

### venv-disciplin (återkommande)
**Regel:** Verifiera ALLTID `sys.executable` FÖRE pipelinekörning. `cd` byter inte venv. Pipeline-venv:
`C:\Projekt\BCG\Pipeline\02. Elasticity\.venv`. DW-script (data_access): `C:\Projekt\Business_Analytics\.venv`.
Ge full aktiveringssökväg överst i varje körblock (Jens uttryckliga önskan).

---

## STANDARDER SÄRSKILT RELEVANTA NU

- **Läs källan/facit, gissa inte ens kvalificerat** (A.9) — varje inklistrad originalfil/output löste steget
  direkt; varje egen-hypotes kostade en runda. Default = begär källfil/output.
- **Tee + Select-String/grep** strukturella rader (Shape/Unique/KEY/Saved/Error/Traceback) — aldrig rådata.
- **Full venv-sökväg överst i varje körblock.** Verifiera sys.executable.
- **Ett steg i taget, verifiera mellan steg.** FTE-kolumnen följdes genom varje pipelinesteg innan nästa.
- **Kirurgisk str_replace + backup** för verbatim BCG-kod (ej hel fil).

*Uppdaterad 2026-05-25 vid PoC-2-milstolpe (modellen facit-validerad på DW-data, FTE Väg 1 inne, fallback identifierad som nästa steg).*

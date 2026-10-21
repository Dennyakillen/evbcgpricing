# DATA_PLACERING — var BCG-repots data ligger, vad den används till och hur den återställs

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB). Läge 2026-10-21. Byggd ur mätning, inte ur minnet:
spegelmanifestet 2026-10-20 (22 040 rader), Blob-listning 2026-10-21 och kodsökning (`git grep`). Filnamn som bär klinik-/siteidentitet
visas bara på mappnivå — fullständiga namn finns i manifestet i Blob (`spegel/bcg_2026-10-20/_spegel/`).*

## 1. Grundregeln

**Git bär metoden, Blob bär datan.** Repot innehåller kod, SQL, konfiguration, dokumentation och ett fåtal små datafiler som
spårats med beslut (styrfiler, kvitton). Allt annat — indata, mellanresultat, modellutdata, facit — ligger i Azure Blob
(lagringskonto `evbcgpricinginput`). En ny dator får koden ur git och datan ur Blob:

```powershell
py -3.11 install.py                                              # miljön (.venv, beroenden, mappar)
.\.venv\Scripts\python.exe tools\spegel\spegel_fran_blob.py --kor  # facit + indata ur Blob (~2 GB, sha256-verifierat)
.\.venv\Scripts\python.exe verify_setup.py                         # kontroll: 0 [FEL]
```

## 2. Blob — tre lager

| Lager | Var | Vad | Vem använder det |
|---|---|---|---|
| **Kanoniskt** | containrarna `input`, `output`, `pipeline`, `receipts`, `runstatus`, `quarantine` | det kedjan kör på: bränsleparquet (`input/parquet/`), modellindata per fönster (`input/data_prep/<fönster>/`), fryst facit som steg 6 behöver (`pipeline/00_frozen_facit/`), modellutdata per familj och fönster (`output/<familj>/<fönster>/`, `output/final/<fönster>/`), kvitton, körstatus | runners (`orchestration/runners/`), dashboarden, `run_after.py`. Struktur: `BLOB_MALSTRUKTUR.md` |
| **Facit ur BCG-originalet** | `pipeline/00_frozen_facit/bcg_original/02. Elasticity/…` | nio filer ur BCG:s leverans, **byte-exakta** (sha256 i blob-metadata), i originalets mappstruktur | validatorerna (`proof_chain`, `output_rationality`, `provenance`) via `BCG_FACIT_DIR`. Se `docs/BCG_ORIGINAL_REFERENSER.md` |
| **Spegel** | `spegel/bcg_2026-10-20/<repo-relativ sökväg>` | ögonblicksbild 2026-10-20 av **allt** på utvecklarens dator som inte var git: 22 009 filer, 22,6 GB, sha256 per fil. Självbeskrivning (manifest, karta, kvitton) i `_spegel/` | återställaren; säkerhetsnätet om något saknas i det kanoniska lagret |

Storlek (mätt 2026-10-21): `input` 5 blobbar / 2,3 GB · `output` 14 552 / 6,5 GB · `pipeline` ~100 / 0,3 GB · `receipts` 255 ·
`runstatus` 3 · `quarantine` 9 · `spegel` 22 019 / 22,6 GB. Spegeln ligger i Cool-nivå (sällan läst).
Senare samma dag: `spegel/historik/` (git-historiken, 1 blob) och `pipeline/00_frozen_facit/bcg_original/_kvitto/` (1 blob).

> **Skydd mot radering (mätt 2026-10-21).** Mjuk borttagning (soft delete) för blobbar och containrar och versionshantering är
> **avstängda**: en blob som raderas eller skrivs över är borta direkt. Uppladdarna skriver aldrig över (`--overwrite false`) och
> återställaren läser bara, men kedjans körningar skriver över utdata. Offentlig åtkomst är avstängd på kontot och alla containrar;
> kontot tar emot anslutningar från alla nät och tillåter kontonyckel (som koden använder). Beslut: IT — `docs/ops/OFFBOARDING_KRITISKT.md` rad 10.

> **Kanoniskt facit vs originalet (mätt 2026-10-21).** `pipeline/00_frozen_facit/` är det steg 6 *kör* på. Tre av dess filer är inte
> byte-identiska med BCG-originalet (`final_model_cluster_granularity_Ivce` 17 567 B mot originalets 14 959 B; `Complete_Product_Data`
> 7,0 MB mot 5,5 MB; steg 6:s `output_summary_bundle` skiljer 4 byte). Därför ligger originalet separat i `bcg_original/` — validatorerna
> jämför mot det, inte mot driftkopiorna.

## 3. Kedjan — vad varje steg läser och skriver

Roller: **INPUT** läses · **OUTPUT** skrivs · **BÅDE** skrivs av ett steg och läses av nästa · **MALL** Excel som modifieras på plats ·
**FACIT** referens att jämföra mot · **ARKIV** kopia/backup. Lokalt = på arbetsdatorn; VM = Azure-VM:en (MOTOR).

| Kedja | Steg | Läser (INPUT) | Skriver (OUTPUT / BÅDE) | Data i Blob |
|---|---|---|---|---|
| FÖRE (lokalt) | **REGEN** DW → parquet (`tools/dw/`) | DW (AAD + VPN, `tools/dw/.env`) | `Sweden_Elasticity_Data_Prep_SQL/parquet/transaction_data.parquet` | kanoniskt `input/parquet/` + spegel |
| FÖRE (lokalt) | **PREP** parquet → modell-CSV (`tools/replicate_dataprep.py`, `scripts/00_read.sql`) | parquet + DW-dimensioner `input/loc.Dim_Item 20250627.csv`, `input/loc.Dim_Department.csv` | `output/Sweden_weekly_model_data_P_C/P_CH/site_level.csv`, `Sweden_masterdata.csv` (7,3 GB) | kanoniskt `input/data_prep/<fönster>/` (site-level) + spegel |
| FÖRE (lokalt) | **Klustring** (`01. Clustering/Sweden_clustering_SQL/`) | `input/*` (NPS, konkurrenter, geodata, FTE-KPI — spårade i git), `Input/Clustering_Raw_Data_new.xlsx` | `parquet/sweden_master_data.parquet` | spegel |
| FÖRE (lokalt) | **Bundle-prep** (`4. Bundle Clinic Data Prep/`) | `1.Data_Pre_Processing/data/`: `0826_bundle_data.csv`, `0826_raw_data_basket_analysis_Clinic_Hospital.csv` (166 MB), `0825_…Productivity…june25.xlsx` (FTE, fryst LF.6); `Sweden_Bundling_Data_Prep/input/` (`sweden_bundle_analysis.csv` m.fl.) | `Raw_Data_Clinic_Hospital.csv`, `bundlegroup_bundle_mapping.csv`, `bundle_weekly_model_data_clinic_hospital.xlsx` | spegel |
| MOTOR (VM) | **Klusterfamiljen** | `2. …/data/0828_Sweden_weekly_model_data_P_C.csv` (kopia av PREP-utdata) | `2. …/output/` (~10 700 filer, 2,5 GB) | kanoniskt `output/cluster/<fönster>/` + spegel |
| MOTOR (VM) | **Sitefamiljen** | `3. …/data/0902_…site_level.csv` (kopia av PREP-utdata; LB.44: den växande versionen) | `3. …/output*/` (~6 700 filer, 2,4 GB — filnamn per site) | kanoniskt `output/site/<fönster>/` + spegel |
| MOTOR (VM) | **Bundlefamiljen** | bundle-prepens utdata | `5. …/output*/` (140 filer) | kanoniskt `output/bundle/<fönster>/` + spegel |
| EFTER (lokalt) | **Steg 5** site-Excel (xlwings) | MALL `Excel_Outputs/Sweden_Sitecode_level_elasticity_summary.xlsx` (85 MB, BCG-leverans) | samma fil (modifieras på plats) | spegel |
| EFTER (lokalt) | **Steg 6** Fall Back Logic (`verify_tool/run/run_step6.py`) | `6. …/input_data/`: `Complete_Product_Data.xlsx` (väv-vikter), `output_summary_bundle.xlsx`, `final_model_cluster_granularity_Ivce.xlsx`, `0808_Sweden_Clinic_Cluster_Mapping.xlsx`; MALL `Excel_Outputs/Sweden_Fallback.xlsx` | `6. …/output_data/Final_Fallback_Data_<tid>.xlsx` | kanoniskt `pipeline/00_frozen_facit/` (indata) + `output/final/` (utdata) + spegel |
| EFTER (lokalt) | **R12 / Model Feed** (`verify_tool/run/build_r12_for_model.py`) | steg 6-utdata + site-level-CSV | `output_model_feed/Model_Feed_<datum>.xlsx` | kanoniskt `output/final/` + spegel |
| VALIDERING | `proof_chain`, `output_rationality`, `provenance`, `extraction_validation` | facit (§2) + kedjans utdata | kvitton `verify_tool/receipts/<datum>/` | kanoniskt `receipts/` + spegel |

## 4. Handgjord indata — inget skript skapar den (bara i Blob och, för vissa, i git)

Beslut 2026-10-21 (Jens): filerna stannar i Blob (inte git); återställaren hämtar dem. Klass = förslag i känslighetsregistret.

| Fil (repo-relativ, under `Pipeline/`) | Steg | Läses av | Klass | Var |
|---|---|---|---|---|
| `01. Clustering/Input/Clustering_Raw_Data_new.xlsx` | Klustring | omätt (ingen kodreferens hittad) | ? | spegel |
| `01. Clustering/Sweden_clustering_SQL/input/*` (6 CSV) | Klustring | `00_read.sql` | RÖD-arv; mappningsfilen RÖD (anställdas arbetskontakter, se `docs/ops/KANSLIGHETSREGISTER.md` G3) | **git** |
| `02. Elasticity/Sweden_Elasticity_Data_Prep_SQL/input/loc.Dim_Item 20250627.csv` | PREP | `00_read.sql` | GUL | spegel |
| `…/Sweden_Elasticity_Data_Prep_SQL/input/loc.Dim_Department.csv` (+ kopia i klustringens input) | PREP, klustring | `00_read.sql` | RÖD (samma chefskolumner som mappningsfilen) | spegel |
| `…/Sweden_Elasticity_Data_Prep_SQL/input/` `Sweden_Clinic_Cluster_Mapping.csv`, `Sweden_Interpolated_Productivity_time.csv`, `Updated_site_cluster.csv` | PREP | PREP-skripten (omätt vilket) | AVTAL / RÖD-arv | **git** |
| `…/Sweden_Elasticity_Data_Prep_SQL/input/loc.DIM_Customer 20250627.csv`, `loc.DIM_Patient.csv` | — | **ingen** (bara bortkommenterat i `01_process.sql`) | RÖD | spegel (beslut 2026-10-20) |
| `…/Sweden_Elasticity_Data_Prep_SQL/parquet/transaction_data_frozen_facit_2025-06.parquet` (968 MB) | REGEN-facit | replikering mot BCG:s fönster | RÖD (pseudonymiserade kund-, patient- och användar-id) | spegel |
| `02. Elasticity/4. Bundle Clinic Data Prep/1.Data_Pre_Processing/data/0826_bundle_data.csv`, `0826_raw_data_basket_analysis_Clinic_Hospital.csv`, `0825_…Productivity…june25.xlsx` | Bundle-prep | bundle-prepen | AVTAL | spegel |
| `…/1.Data_Pre_Processing/data/Sweden_Clinic_Hospital_FTE_Data.csv` | Bundle-prep | bundle-prepen | RÖD-arv | spegel (*rättat 2026-10-21: filen spåras inte i git — mätt med `git ls-files`*) |
| `…/Sweden_Bundling_Data_Prep/input/` (`sweden_bundle_analysis.csv` m.fl., 3 filer) | Bundle-prep | `Sweden_Bundling_Data_Prep/scripts` | AVTAL | spegel |
| `02. Elasticity/Excel_Outputs/Sweden_Sitecode_level_elasticity_summary.xlsx` (85 MB) | Steg 5 (MALL) | `data_prep_after_model_output.py` (site) | AVTAL | spegel |
| `02. Elasticity/Excel_Outputs/Sweden_Fallback.xlsx` | Steg 6 (MALL) | `Fall_Back_Logic.py` | GRÖN | spegel |
| `02. Elasticity/6. Fall Back Logic/input_data/0808_Sweden_Clinic_Cluster_Mapping.xlsx` | Steg 6 | `Fall_Back_Logic.py`, validatorer | AVTAL + RÖD-arv | spegel |
| `02. Elasticity/6. Fall Back Logic/input_data/0901_…blended Final Model.xlsx` (27 MB) | Steg 6? | **ingen kod nämner den** (läses via glob eller är död — omätt) | AVTAL | spegel |
| `02. Elasticity/6. Fall Back Logic/output_data/Final_Fallback_Data_20260622_125206.xlsx` | facit | `verify_tool/frozen_facit_reference.json` (profilen) | GUL | spegel |

## 5. Regenererbart — speglat ändå, men återskapas av kedjan

`Sweden_masterdata.csv` (7,3 GB), `sweden_master_data.parquet` (klustring och bundle), `Raw_Data_Clinic_Hospital.csv`, PREP:s
modell-CSV:er, modellutdata, steg 6-utdata, `control_file*.xlsx` (feature selection pass 1, LB.40/41), `holiday_check0820.xlsx`
(skapas av `data_prepration.py`). Arkiv och backuper (`_ATT_RADERA/`, `_archive*/`, `_backup*/`, `*.bak*`, `*.SURVIVALTEST`)
finns bara i spegeln och behövs inte för drift.

> **Två versioner av bränslet (mätt).** Lokal `transaction_data.parquet` var 1 262 MB 2026-10-20; kanoniska `input/parquet/` har
> 1 091 MB (2026-07-03). Kör alltid REGEN (`run_data.py`) för ett nytt fönster i stället för att välja mellan dem.

## 6. Återställning — tre profiler

| Profil | Hämtar | Till | Storlek |
|---|---|---|---|
| `facit` | `pipeline/00_frozen_facit/bcg_original/` + spegelns `_extern/bcg_inputs/` (BCG-leveranserna 0828/0808/FTE) | `verify_tool/facit/…` (gitignorerad) | ~145 MB |
| `indata` | manifestrader med roll INPUT/MALL/FACIT utanför arkiv (§4 + modellindata) | samma repo-sökväg | ~1,9 GB |
| `allt` | hela spegeln | samma repo-sökväg | ~22 GB |

Standard är `facit` + `indata`. Torrkörning först (visar planen), `--kor` hämtar. Befintlig fil med annat innehåll rörs aldrig
(KONFLIKT); `--skriv-over` flyttar undan den till `<fil>.fore-aterstallning-<tid>`. Kvitto i `workspace/aterstallning/`.

## 7. Medvetet utanför git och Blob

| Vad | Varför | Ersätts av |
|---|---|---|
| `tools/dw/.env` (DW-server, databas) | konfiguration med anslutningsuppgifter — speglas aldrig | `tools/dw/.env.example` + värden från DW-förvaltaren (IT) |
| BCG-originalet i övrigt (`Datastrategi\BCG`, 59 973 filer, 81 GB) | beslut 2026-10-21: applikationens funktion ska återskapas, inte varje utvecklingssteg | de nio facit-filerna i `bcg_original/` + namnlistan i `docs/BCG_ORIGINAL_REFERENSER.md` |
| Git-historiken (174 commits) i DevOps | DevOps-importen är kurerad utan historik | `spegel/historik/evbcgpricing_2026-10-21.bundle` (återläst och klonad 2026-10-21) — se `docs/ops/OFFBOARDING_KRITISKT.md` rad 4 |

## Ändringar

| Datum | Ändring |
|---|---|
| 2026-10-21 | Första versionen. |
| 2026-10-21 | §2: skydd mot radering mätt, `historik/` och `_kvitto/`. §4: FTE-filen ligger i spegeln, inte i git (mätt). §7: historiken uppladdad. |
| 2026-10-21 | §4: klasser ur kolumnmätningen (klustringens indata, `loc.Dim_Department`, fryst bränsle). Se `docs/ops/KANSLIGHETSREGISTER.md`. |

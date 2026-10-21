# BCG_ORIGINAL_REFERENSER — vilka filer ur BCG:s originalleverans validatorerna jämför mot

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB). Läge 2026-10-21 — byggt ur kodsökning (`git grep`) och
sha256-mätning, inte ur minnet. Fyll i det som är markerat **[Jens]**.*

## Varför den här filen finns

Under utvecklingen jämfördes replikeringen mot BCG:s originalleverans (`BCG_orginal_V2_New`, BCG-konsulterna 2025-07). Originalet
följer **inte** med till DevOps och speglas inte i sin helhet till Azure — beslut 2026-10-21 (Jens): det är applikationens slutliga
funktion som ska kunna återskapas, inte varje utvecklingssteg. Utvecklingsjämförelsen är stängd och dokumenterad i kod, kvitton och loggar.

De **nio filer** validatorerna läser ligger däremot byte-exakt i Azure, så att validatorerna fungerar hos en förvaltare. Den här
filen bevarar namnen, användningen och kontrollsummorna.

## Var originalet ligger

| | |
|---|---|
| Arkivplats | **[Jens]** — under utvecklingen: utvecklarens OneDrive, `OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New\` |
| Omfång | hela `Datastrategi\BCG`: 59 973 filer, 81 GB (mätt 2026-10-21) |
| Klass | AVTAL (BCG:s konsultmaterial) — se känslighetsregistret |

## De nio filerna (sökvägar under `BCG_orginal_V2_New\02. Elasticity\`)

Alla nio finns i Blob under `pipeline/00_frozen_facit/bcg_original/02. Elasticity/<samma sökväg>` (uppladdade och verifierade
2026-10-21, sha256 i blob-metadata) och återställs till `verify_tool/facit/BCG_orginal_V2_New/02. Elasticity/` av
`tools/spegel/spegel_fran_blob.py --profil facit --kor`.

| # | Fil | Vad den är | Används av | Bytes | sha256 (16 första) |
|---|---|---|---|---:|---|
| 1 | `2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv` | BCG:s modellindata, kluster | `proof_chain/verify_dataprep.py`, `verify_infra.py`; extraction_validation (samma fil som `bcg_inputs`-kopian, sha256 lika) | 53 804 156 | `34AA61555AC6D41A` |
| 2 | `2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_CH.csv` | BCG:s modellindata, kluster (CH) | `verify_dataprep.py`, `verify_infra.py` | 21 620 061 | `7419D447EF74178B` |
| 3 | `2. Product Cluster Level Models\output\model\output_summary.xlsx` | BCG:s modellutdata, kluster | `verify_model.py`, `verify_infra.py`, `output_rationality/_rationality_helpers.py` (drift mot BCG) | 338 118 | `06C29EE05F63C1D3` |
| 4 | `2. Product Cluster Level Models\output\final_model_cluster_granularity.xlsx` | BCG:s steg-5-routning (43 representanter) | `verify_blend.py`, `verify_infra.py` | 14 959 | `10ACA47C3BE85367` |
| 5 | `3. Product Site Level Models\output\model\output_summary.xlsx` | BCG:s modellutdata, site | `verify_model.py`, `verify_infra.py` | 410 512 | `430035B6DEBCF331` |
| 6 | `5. Bundle Clinic Models\output\model\output_summary.xlsx` | BCG:s modellutdata, bundle | `verify_model.py`, `verify_infra.py` | 27 236 | `1B1756DF024AC4BD` |
| 7 | `6. Fall Back Logic\input_data\Complete_Product_Data.xlsx` | väv-vikter (Service/Rank/Description) | `verify_blend.py`, `verify_infra.py`, `provenance/_provenance_helpers.py` | 5 541 307 | `0A5B0A785A33ADEB` |
| 8 | `6. Fall Back Logic\input_data\output_summary_bundle.xlsx` | bundle-sammanfattning in i steg 6 | `provenance/_provenance_helpers.py` | 27 232 | `5675CCB9E5C1B8D0` |
| 9 | `6. Fall Back Logic\output_data\Final_Fallback_Data_20250930_091648.xlsx` | **BCG:s slutresultat** (fallback-tabellen, 108 979 rader) | `verify_fallback.py`, `verify_infra.py`, `provenance/validate_fallback_freshness.py` | 7 872 584 | `353CFA2E869AB38B` |

Fullständiga sha256 och blob-namn: blob-metadata (`sha256`) på varje blob, och uppladdningskvittot i Blob
`pipeline/00_frozen_facit/bcg_original/_kvitto/BCG_ORIGINAL_UPLOAD_2026-10-21.csv` (2 373 B, sha256 i blob-metadata; ligger
utanför mappen som återställaren hämtar).

## Mätt 2026-10-21: driftkopiorna är inte originalet

Steg 6 kör på kopiorna i `pipeline/00_frozen_facit/` (`cluster_step5/`, `weave_weights/`, `bundle/`), inte på originalet.
Tre av dem är **inte** byte-identiska med originalet: rad 4 (driftkopian `_Ivce` är 17 567 B), rad 7 (driftkopian 7 007 694 B)
och rad 8 (driftkopian 27 236 B = rad 6). Därför jämför validatorerna mot `bcg_original/`, aldrig mot driftkopiorna
(`proof_chain/README.md`: *validate against the frozen original, never a working-folder copy*). Kommentaren i `verify_blend.py`
som påstod "byte-identical" är rättad med mätningen.

## Bevis för att Azure-kopian är originalet

`verify_tool/proof_chain/run_all.py` kördes tre gånger 2026-10-21 med samma sammanställning (6/6 rader identiska):
1. före ompekningen, mot OneDrive-originalet;
2. efter ompekningen, med `BCG_FACIT_DIR` = OneDrive-originalet;
3. efter ompekningen, utan `BCG_FACIT_DIR` = kopian återställd ur Azure.

## Vad validatorerna visar i dag

Kedjans utdata kommer nu från det **växande** fönstret, inte från BCG:s fönster 2022-07-01..2025-06-28. `proof_chain` mäter därför
**drift mot BCG 2025**, inte replikering (2026-10-21: kluster rank-korr 0,69; steg 6 korr 0,92 och 90,7 % samma fallback-nivå).
Replikeringsbeviset bit-för-bit (kluster 3812/3812, korr 1,0) är kvittot `verify_tool/receipts/verify_receipt_2026-05-28.xlsx`
(spårat i git, länkas från dashboarden). Att upprepa det kräver en körning på det frysta fönstret
(`transaction_data_frozen_facit_2025-06.parquet` i spegeln).

## Det här ligger inte i Azure (medvetet)

Resten av originalet (modellkod, mellanresultat, BCG:s dokumentation). Undantag i koden: `proof_chain/compare_features_to_facit.py`
(valfri fördjupning, FR-2) pekar på en arkiverad kopia (`_ATT_RADERA/Elasticity_duplicate_from_2025-10/`) som bara finns i spegeln. Verktyg som bara fungerade mot originalet (`upload_frozen_facit.py`, `analysis/analys_bcg_freshness.py`,
`analysis/xlsx_export_bcg_freshness.py`, `analysis/compare_elasticity_runs.py`, `tools/measure_facit_window.py`) undantas i exportens beslutsfil.

## Öppet

- **[Jens]** arkivplats för hela originalet (tabellen ovan).

## Ändringar

| Datum | Ändring |
|---|---|
| 2026-10-21 | Första versionen. |
| 2026-10-21 | Uppladdningskvittot ligger nu i Blob (`_kvitto/`); pekaren pekade tidigare på utvecklarens lokala mapp. |

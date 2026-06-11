# Bundle SQL data-prep — input/ (recept, inte data)

De tre CSV-filerna som Bundle-SQL-dataprep (`scripts/00_read.sql`) läser är **BCG-original
rådata** och ligger medvetet INTE i Git (se repots `.gitignore`-princip: tunga binärer/rådata
bor i källan, recept i Git). Den här filen är receptet för att återskapa `input/` på en ny
maskin eller i en framtida körning.

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB).

---

## De tre filerna och var de hämtas

| Fil | Storlek | Källa att kopiera FRÅN |
|---|---|---|
| `sweden_bundle_analysis.csv` | ~18,67 MB | OneDrive: `...\BCG_orginal_V2_New\02. Elasticity\4. Bundle Clinic Data Prep\Sweden_Bundling_Data_Prep\input\` |
| `Sweden_Clinic_Cluster_Mapping.csv` | 1 382 B (3 kol: `ID_Department,Cluster,New_Cluster`) | Repo: `Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\input\` |
| `Sweden_Interpolated_Productivity_time.csv` | ~0,34 MB | Repo: `Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\input\` |

> ⚠️ **Varning — cluster-mapping-fällan:** OneDrive-versionen av
> `Sweden_Clinic_Cluster_Mapping.csv` (i Bundle:s egen input-mapp) är **0 byte** och saknar
> dessutom `New_Cluster`-kolumnen. Använd ALLTID Elasticity-mappens version (1 382 B, tre
> kolumner) — det är den Cluster/Site validerades på. XLSX-källan
> (`0808_Sweden_Clinic_Cluster_Mapping.xlsx` i Fall Back Logic) har bara två kolumner och
> duger inte rakt av. (Spårning gjord 2026-06-11.)

## sweden_master_data.parquet (separat, byggs — inte kopieras)

`scripts/00_read.sql` läser även `parquet/sweden_master_data.parquet`. Den **kopieras inte** —
den byggs växande av `convert_masterdata_to_parquet.py` (repo-roten) från
`Sweden_masterdata.csv` som `replicate_dataprep.py` producerar med `BCG_END_DATE` satt. Se
`F9_BUNDLE_INVENTORY.md` för den kedjan.

## Återställ input/ (PowerShell)

```powershell
cd "C:\Projekt\BCG"
$bundleInput = "Pipeline\02. Elasticity\4. Bundle Clinic Data Prep\Sweden_Bundling_Data_Prep\input"
$elasticityInput = "Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\input"
$oneDriveBundleInput = "C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New\02. Elasticity\4. Bundle Clinic Data Prep\Sweden_Bundling_Data_Prep\input"

Copy-Item "$oneDriveBundleInput\sweden_bundle_analysis.csv" "$bundleInput\sweden_bundle_analysis.csv" -Force
Copy-Item "$elasticityInput\Sweden_Interpolated_Productivity_time.csv" "$bundleInput\Sweden_Interpolated_Productivity_time.csv" -Force
Copy-Item "$elasticityInput\Sweden_Clinic_Cluster_Mapping.csv" "$bundleInput\Sweden_Clinic_Cluster_Mapping.csv" -Force

# Verifiera storlekar (cluster-mapping MÅSTE vara 1382 B, inte 0):
Get-ChildItem $bundleInput | Select-Object Name, @{N='Bytes';E={$_.Length}}
```

Kör därefter `run_bundle_dataprep.py` (repo-roten) som har inbyggd preflight som fångar
saknade/tomma inputs innan SQL körs.

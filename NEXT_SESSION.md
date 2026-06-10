# NEXT_SESSION — F.9 Bundle på växande data (datakedja första gången)

**Projekt:** evbcgpricing (BCG priselasticitet, växande data)
**Branch:** `fas-f-fresh-data`
**Utvecklare:** Jens Palmö
**Beräknad tid:** 2.5-4 timmar (premiärkörning — felsökningsmarginal inräknad)

> Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst
> på Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md` samt relevanta MASTER_*.md.
>
> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant master-fil vid sessionsslut.

---

## SESSIONEN I EN MENING

Bygg och kör Bundle-datakedjan (mapp 4 + mapp 5) på växande data för **första gången** —
från `sweden_master_data.parquet` via Bundle-SQL-dataprep och Ray-varukorgsbygge till
Bundle-modellen på VM, sedan steg 5 lokalt. Detta är det sista modellsteget innan F.10 (Step 6)
kan köras.

---

## STATUS VID SESSIONSSTART

**2 av 3 modellfamiljer klara på växande data:**
- ✅ **F.7 Cluster** — step 5 fallback-blend körd (4180 KEY, 33.4%→45.2% signifikans).
- ✅ **F.8 Site** — KLAR 2026-06-10. Steg 1-4 på VM (~70 min, 6624 KEY), steg 5 lokalt på Windows.
  Slutleverans `Excel_Outputs/Sweden_Sitecode_level_elasticity_summary.xlsx` (83 MB).
- 🟡 **F.9 Bundle** — KARTLAGD, ej körd. **Denna sessions uppgift.**

**Datafundament klart och bevisat:**
- `transaction_data.parquet` regenererad till 2026-04-30 (27,4M rader).
- G7-parametrisering komplett (SQL-dataprep + VM constants.py per familj).
- `Sweden_masterdata.csv` (~7,6 GB) producerad växande — Bundle hänger på denna.

---

## F.9 BUNDLE — KARTLAGD KEDJA (se LESSONS_BCG, INSIGHTS, minnet)

Bundle-SQL-dataprep (`4. Bundle Clinic Data Prep/Sweden_Bundling_Data_Prep/scripts/00_read.sql`)
läser **`sweden_master_data.parquet`** — INTE `transaction_data.parquet` direkt. Och
`sweden_master_data` = **samma fil cluster/site-SQL-dataprep producerar** (`Sweden_masterdata.csv`),
som redan är växande. Det gör F.9 mindre arbete än befarat.

**Statiska inputs (i BCG-original `4. Bundle Clinic Data Prep`, återanvänds som de är):**
- `sweden_bundle_analysis.csv` (18,67 MB) — varukorgsdefinition (`sweden_bundles`).
- `Sweden_Clinic_Cluster_Mapping.csv` — cluster-mappning.
- FTE (`Sweden_Interpolated_Productivity_time.csv`, tak 2025-06 → väntad NULL i nyaste månaderna).

**Kedja att köra:**
1. Konvertera växande `Sweden_masterdata.csv` → `sweden_master_data.parquet` (Bundle-format).
2. Lägg statiska filer i Bundle-SQL-dataprep `input/`.
3. Kör Bundle-SQL-dataprep (egen `duckdb.exe` + `run.ps1` i `Sweden_Bundling_Data_Prep/scripts/`).
4. Kör Ray-varukorgsbygge (`2.Sweden_Bundle_Clinic_Model_Data_Creation.py` + `bundle_utils.py`).
5. Kör Bundle-modell (mapp 5) på VM — egna kolumnnamn (`basket_price`/`Bundle_code`/`Clusters`, LB.28).
6. Kör Bundle steg 5 lokalt (samma xlwings-mönster som Site, LB.44-45).

**Att vara medveten om (premiärkörning):**
- Bundle har egna kolumnnamn — kopiera ALDRIG constants/config rakt från Cluster (LB.28).
- feature_selection tvåpass-control_file gäller även Bundle (LB.40) — radera stale, kör två pass.
- VM constants.py för Bundle måste vara G7-patchad innan körning.
- Excel-steget (5) körs lokalt, inte på VM (LB.44).

---

## PRE-FLIGHT (VM)

```powershell
# KRITISKT: rätt subscription först (LB.46)
az account show --query "{user:user.name, subscription:name}" -o table
az account set --subscription "ev-lz3-ai (SE)"

az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
Start-Sleep -Seconds 90; ssh azureuser@172.18.148.4 "hostname && uptime"
```

VM pipeline-Python: `~/bcg/cluster/.venv/bin/python` (delas av alla familjer, se UBUNTU §18).
**Deallocera VM när klart** (LB-påminnelse): `az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm`.

---

## EFTER F.9

- **F.10 Step 6** (`Fall_Back_Logic.py`) — multi-modell-blend, kräver alla tre familjers
  output_summary. Körs lokalt (Windows/xlwings, som steg 5).
- **Output-rimlighetsgrind** — MBAS0703-outlier (−320) + de 7 REVIEW-utfallen från
  rationality-suiten (verify_tool/output_rationality/) att utreda. Efter F.10.
- **Drift-visualisering** fruset facit vs växande, alla familjer.
- **Fas Z** produktionalisering (FD.1-4) + projektavslut (FD.10).

---

## VID SESSIONSSLUT

1. Committa Bundle-arbetet (dataprep-config, ev. patchar, output-referenser).
2. Flytta dagens lärdomar till master-filerna INNAN sessionen stängs (LESSONS_BCG / UBUNTU / KÄRNPRINCIPER).
3. Uppdatera denna NEXT_SESSION.md med Bundle-utfall och nästa steg (F.10).
4. Deallocera VM. Bekräfta `VM deallocated`.

---

*Uppdaterad 2026-06-10 efter F.8 Site klar + F.9 Bundle kartlagd. Ersätter föregående
NEXT_SESSION (output rationality-detaljgranskning) — den uppgiften flyttad till efter F.10,
eftersom F.8/F.9/F.10 prioriterades (bygg klart alla familjer först, validera rimlighet sen).*

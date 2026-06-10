# F.9 BUNDLE — Inventering & startunderlag

**Syfte:** Ge nästa session allt den behöver för att köra F.9 Bundle UTAN att utreda om från noll.
Sammanställd 2026-06-10 efter kartläggning + djupinventering. Läs denna FÖRE VM-start.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB), assisterad av Claude.

> **Princip:** §6.4 — inventera en gång, dokumentera, återanvänd. Denna fil ersätter att gräva i
> Bundle-strukturen varje session. Tre fält märkta `[VERIFIERA]` återstår att bekräfta med billiga
> läs-kommandon innan VM startas — de är listade sist.

---

## 1. STATUS: var F.9 står

2 av 3 modellfamiljer klara på växande data (F.7 Cluster, F.8 Site). Bundle är **premiärkörning** —
datakedjan har aldrig körts på din sida. Det är INTE en Site-tvilling: egen dataprep (Ray-varukorgar),
egna kolumnnamn, egen Ray-init utanför config.

---

## 2. BEKRÄFTAD KEDJA

```
sweden_master_data.parquet  (källa Bundle-SQL-dataprep läser — 00_read.sql)
   = samma fil Cluster-SQL-dataprep producerar
   ⚠️ Nuvarande fil är BCG-original/oförändrad (2025-12-08), måste regenereras växande först
        ↓
Bundle-SQL-dataprep (Sweden_Bundling_Data_Prep/scripts/ — 00_read, 01_process, 02_export)
   egen duckdb.exe + run.ps1  (⚠️ AppLocker LB.2 + execution policy LB.21 → kör via Python-wrapper)
        ↓
Ray-varukorgsbygge (1.Data_Pre_Processing/code/2.Sweden_Bundle_Clinic_Model_Data_Creation.py + bundle_utils.py)
        ↓
Bundle-modell (5. Bundle Clinic Models, steg 1-4 på VM)
        ↓
Bundle steg 5 lokalt (xlwings, som Site — LB.44-45)
```

**Statiska inputs (BCG-original, återanvänds som de är):**
- `sweden_bundle_analysis.csv` (18,67 MB) — varukorgsdefinition (`sweden_bundles`)
- `Sweden_Clinic_Cluster_Mapping.csv` — cluster-mappning
- `Sweden_Interpolated_Productivity_time.csv` — FTE (tak 2025-06)

---

## 3. TRE BLOCKARE SOM MÅSTE LÖSAS FÖRE/UNDER KÖRNING

> **LÖST UNDER KARTLÄGGNING 2026-06-10 — Blockare 1 och 2 var överskattade.** Den faktiska
> masterdata-kedjan hittades och bevisades enklare än inventeringen antog. Se nedan. Endast
> Blockare 3 (Ray-patchar, VM-sidan) återstår som verkligt arbete.

### Blockare 1 — sweden_master_data.parquet regenereras via BEVISAD G7-runner (inte Clustering-wrapper)

**Den verkliga kedjan (kartlagd 2026-06-10):**

```
transaction_data.parquet  (1091 MB, REDAN växande 2026-06-09)
   ligger i Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\parquet\
   (frusen facit-version: transaction_data_frozen_facit_2025-06.parquet, 968 MB — LB.24 redan tillämpad)
        ↓
replicate_dataprep.py  (C:\Projekt\BCG\, repo-roten — DEN BEVISADE RUNNERN)
   kör Sweden_Elasticity_Data_Prep_SQL\scripts\ 00→01→02 via duckdb-Python (AppLocker-rent, LB.2)
   _inject_dates() (rad 130) skriver G7-fönstret in-memory på YearFlag-filtren (LB.22)
        ↓
output\Sweden_masterdata.csv  (komma-separerad, växande)
        ↓
convert_masterdata_to_parquet.py  (NY, C:\Projekt\BCG\ — CSV→parquet, schemaverifierad)
   skriver sweden_master_data.parquet till BÅDE Bundle- och Clustering-parquet\
        ↓
Bundle/Clustering 00_read.sql  read_parquet(...)
```

**Varför detta är enklare än inventeringen sa:** `replicate_dataprep.py` är samma runner som redan
producerade växande P_C/site-data för F.7 Cluster och F.8 Site. Den har en komplett G7-injektor
(`_inject_dates` + `_fiscal_year_flags`, byggd av Jens under FAS F) som vid `BCG_END_DATE`-override
skriver om YearFlag-whitelisten in-memory. Ingen SQL-patch behövs (se Blockare 2). Den frusna 536 MB
`sweden_master_data.parquet` i Clustering-mappen är BCG-original — men den är en KOPIA av runnerns
CSV-output, inte en oberoende artefakt. Vi regenererar den, vi patchar ingen wrapper.

**LB.24/LF.3-skydd FÖRST:** backup + skrivskydd på den frusna parqueten innan den skrivs över. Den
ligger i Clustering-mappen; Bundle-mappens parquet finns inte än (skapas av konverteringsscriptet).

```powershell
$src = "C:\Projekt\BCG\Pipeline\01. Clustering\Sweden_clustering_SQL\parquet\sweden_master_data.parquet"
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"
$bak = "$src.frozen-bak-$ts"
Copy-Item $src $bak
Set-ItemProperty $bak -Name IsReadOnly -Value $true
Get-ChildItem $bak | Select-Object FullName, Length, IsReadOnly
```

Verifiera 536 MB + IsReadOnly=True INNAN regenerering. Förlust av frusen baseline är inte
återställbar utan OneDrive-originalet.

**Regenerering (kör från SQL prep-mappen så input/ parquet/ output/ resolverar):**

```powershell
cd "C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL"
$env:BCG_END_DATE = "2026-04-30"
py -3.11 "C:\Projekt\BCG\replicate_dataprep.py" --base-dir "C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL"
Remove-Item Env:BCG_END_DATE
```

Runnern loggar `VERIFY output/Sweden_masterdata.csv ... bytes -> OK` (R7, rad 185) vid lyckad körning.

**Konvertera CSV → parquet (NY fil, levererad denna session):**

```powershell
cd "C:\Projekt\BCG"
py -3.11 convert_masterdata_to_parquet.py --dry-run
```

Dry-run rapporterar schema + YearFlag-population utan att skriva. Bekräfta att utskriften visar
`G7: '12M ending Jun 26' PRESENT`. Sedan skarp körning utan flagga:

```powershell
cd "C:\Projekt\BCG"
py -3.11 convert_masterdata_to_parquet.py
```

Scriptet skriver `sweden_master_data.parquet` växande till både Bundle- och Clustering-parquet\.

### Blockare 2 — LÖST: G7-injektorn i replicate_dataprep.py täcker YearFlag-filtren

**Bekräftat 2026-06-10:** Bundle/Clustering-SQL filtrerar på YearFlag, men den filtreringen sker
i `Sweden_Elasticity_Data_Prep_SQL\scripts\01_process.sql` (rad 138 + 377), och `replicate_dataprep.py`
har en regex i `_inject_dates()` (rad 163) som fångar och skriver om BÅDA `YearFlag IN (...)`-ställena
till den datumhärledda FY-listan. YearFlag-GENERATORN (01_process.sql rad 22-33) är dessutom redan
dynamisk — den producerar `'12M ending Jun 26'` automatiskt för 2025-07..2026-04-rader.

Patchväg (b) från tidigare resonemang är alltså redan implementerad i runnern. **Ingen SQL-patch
behövs.** Bundle:s eget `01_process.sql` (rad 20) ärver bara redan-filtrerad data via masterdata-
parqueten, så dess YearFlag-villkor blir verkningslöst (datan är redan inom fönstret).

> **Restpunkt att verifiera empiriskt efter körning, ej blockerande:** `01_process.sql` rad 465
> (`WHERE YearFlag = '12M ending Jun 25'`) fångas INTE av injektor-regexen (matchar bara `IN (...)`).
> Logiskt är det korrekt — den bygger `SalesTotal_YearEnding25`, en fast referenskolumn för
> fallback-rankning som SKA peka på ett fast år. Verifiera att den kolumnen ser rimlig ut i
> fallback-output, men patcha den inte utan skäl (LF-stabilitet).

### Blockare 3 — Ray-init hårdkodad i bundle_utils.py (utanför config)

Två separata Ray-konfigurationsställen:

- `feature_selection.py` rad 39: `directory_path: "C:\\ray_spill"` → kraschar på Linux-VM (LB.34,
  /tmp/ray_spill). Samma patch som Cluster/Site fått på VM (CZ.5).
- `bundle_utils.py` rad 14: `object_store_memory=2 * 1024**3` (HÅRDKODAD 2 GB, ej config-styrd).
  På 128 GB-VM kvävs Bundle:s feature_selection-kombinatorik av 2 GB.

**Beslut: hårdpatcha bundle_utils.py rad 14 till 8 GB** (matchar Cluster:s `config.yml: ray: memory: 8`
från LB.4, bevisat tillräckligt). Premiärkörningens mål är "Bundle kör växande end-to-end" —
config-driven Ray-init är legitim teknisk skuld men *inte* premiär-arbete. Att bygga om till
config-läsning mitt i premiären är scope-glidning (KÄRNPRINCIPER 2026-06-07-lärdomen).

**Lägg som FD-post** (`FD.11 — Bundle Ray-init till config-driven mönster (matcha Cluster/Site)`) i
`FUTURE_DEVELOPMENT.md` så skulden är spårad utan att stoppa F.9.

**LB.35:** verifiera med `python -c "from bundle_utils import *"` efter patch — annars upptäcks felet
60 min in i körningen.

---

## 4. BEKRÄFTAT KLART (inget att göra)

- **Bundle-modellens `constants.py`** (`5. Bundle Clinic Models\code\constants.py` — OBS en nivå upp,
  INTE `code/src/` som Cluster/Site) är G7-patchad: env-pattern + END_DATE2-derivering + SPECIAL_WEEKS.
  `regular_price.py` rad 187 filtrerar via START_DATE/END_DATE → följer med automatiskt.
- **Bundle har egna kolumnnamn** (`basket_price`/`Bundle_code`/`Clusters` plural — LB.28). Ligger längre
  ner i samma constants.py. `[VERIFIERA]` intakta efter G7-patch (billig, under VM-prep).

---

## 5. KÖR DESSA FÖRE VM-START (billig läs-inventering, avgör arbetsmängd)

```powershell
cd "C:\Projekt\BCG"

# Git-orientering + rätt subscription (LB.46)
git log --oneline -5
git status
git branch --show-current
az account show --query "{user:user.name, subscription:name}" -o table
# vid behov: az account set --subscription "ev-lz3-ai (SE)"
```

```powershell
# A) [UTFÖRT 2026-06-10] YearFlag-population i FRUSEN masterdata
# Utfall: '12M ending Jun 17'..'25', INGEN Jun 26 → frusen bekräftad. check_yearflag_population.py
# levererad som .py-fallback (oneliner funkade men scriptet är robustare för upprepning).
py -3.11 "C:\Projekt\BCG\check_yearflag_population.py"
```

```powershell
# B) [UTFÖRT 2026-06-10] Var byggs masterdata? Clustering-SQL bygger den INTE — den konsumerar.
# Byggaren = Sweden_Elasticity_Data_Prep_SQL\scripts\01_process.sql, körd av replicate_dataprep.py
# (repo-roten, bevisad G7-runner). Se Blockare 1.
Get-ChildItem "Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL" -Recurse -Include "*.py","*.sql","*.ps1" | Select-Object @{N='RelPath';E={$_.FullName.Replace("$PWD\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\",'')}}, @{N='KB';E={[math]::Round($_.Length/1KB,1)}}, LastWriteTime | Sort-Object RelPath | Format-Table -AutoSize -Wrap
```

```powershell
# C) [UTFÖRT 2026-06-10] Bundle Ray-init + ray_spill — patchställen bekräftade
# feature_selection.py rad 39: "C:\ray_spill"; bundle_utils.py rad 14: object_store_memory=2*1024**3
Select-String -Path "Pipeline\02. Elasticity\4. Bundle Clinic Data Prep\1.Data_Pre_Processing\code\*.py" -Pattern "ray_spill|object_store_memory|directory_path|C:\\\\" | Select-Object @{N='File';E={Split-Path $_.Path -Leaf}}, LineNumber, Line
```

---

## 6. REVIDERAD TIDSUPPSKATTNING (premiär hela kedjan)

| Steg | Tid | Risk |
|---|---|---|
| Backup + read-only på frusen masterdata (Blockare 1) | 1 min | Låg |
| Regenerera Sweden_masterdata.csv växande (replicate_dataprep.py, bevisad G7-runner) | 30-60 min | Låg (etablerat mönster) |
| Konvertera CSV → parquet (convert_masterdata_to_parquet.py, dry-run + skarp) | 5 min | Låg |
| ~~Patcha 01_process.sql YearFlag~~ — UTGÅR, G7-injektorn täcker det | — | — |
| Patcha feature_selection.py ray_spill (VM) | 5 min | Låg (= Cluster) |
| Hårdpatcha bundle_utils.py object_store_memory till 8 GB | 5 min | Låg (beslutat) |
| Bundle SQL-dataprep-körning (Python-wrapper, ej run.ps1/duckdb.exe — LB.2) | 30-60 min | Medel (premiär lokalt) |
| Ray-varukorgsbygge | 30-60 min | Medel (premiär) |
| Bundle-modell VM (steg 1-4) | 60-90 min | Medel (Site tog ~70 min) |
| Bundle steg 5 lokalt (xlwings) | 30-45 min | Låg (beprövat) |

**Realistiskt: 3-4.5h för clean körning.** Premiär över hela kedjan → räkna med felsökning ovanpå.
(Nedreviderad efter kartläggning 2026-06-10: SQL-G7-patchen utgick — `replicate_dataprep.py`:s
befintliga `_inject_dates()` täcker YearFlag-filtren. Dataprep-sidan kräver noll nya patchar; kvar
är konvertering + Ray-patcharna på VM-sidan.)

---

## 7. RELEVANTA LÄRDOMAR (slå upp vid behov)

- **LB.2** AppLocker blockerar .exe → `python -m` / Python-wrapper (gäller Bundle:s duckdb.exe + run.ps1)
- **LB.4** Ray-memory 8 GB löste Stage 2-krasch för Cluster — samma värde valt för bundle_utils.py
- **LB.21** PowerShell execution policy + .ps1 ASCII-krav
- **LB.24** Validera mot fryst original, ej arbetskopia — drev backup-steget i Blockare 1
- **LB.28** Bundle har egna kolumnnamn — kopiera ALDRIG constants/config från Cluster
- **LB.34** ray_spill /tmp på Linux, inte C:\
- **LB.35** verifiera importer efter kod-patch (`python -c "from X import *"`)
- **LB.40/41** feature_selection tvåpass-control_file (radera stale → pass 1 kraschar → pass 2 funkar)
- **LB.44-45** Excel-steg (5) körs lokalt, com_error-fix i write_df_preserve_named_range
- **LB.46** Azure subscription cachas → `az account show` + sätt ev-lz3-ai FÖRE VM
- **LF.3** BCG-original/verifierad baseline skrivskyddas — mönstret som backup-steget följer
- **G7** datumfönster env-överstyrbart — `replicate_dataprep.py._inject_dates()` (rad 130) skriver om
  YearFlag-filtren in-memory (LB.22); Bundle-modellens constants.py separat G7-patchad. SQL-skulden
  visade sig redan löst i runnern, inte en kvarvarande patch.
- **LB.22** replicate_dataprep injicerar datum in-memory — grunden till att ingen SQL-patch behövs

---

*Sammanställd 2026-06-10. Reviderad samma dag i två omgångar.*
*Omgång 1 (senior review): backup + IsReadOnly före regenerering (LB.24/LF.3); Blockare 3 beslutat —
hårdpatch 8 GB, config-driven → FD.11; §5 kommando A .py-fallback (LB.21).*
*Omgång 2 (full kedje-kartläggning): Blockare 1 + 2 LÖSTA innan VM. Verklig masterdata-byggare hittad
(`Sweden_Elasticity_Data_Prep_SQL\01_process.sql`, körd av `replicate_dataprep.py` från repo-roten —
bevisad G7-runner, ej Clustering-wrapper som antogs). YearFlag-genereringen redan dynamisk; G7-injektorn
täcker filtren → ingen SQL-patch. Nytt steg: `convert_masterdata_to_parquet.py` (CSV→parquet, levererad).
Kvar som verkligt arbete före VM: regenerera + konvertera. På VM: Ray-patcharna (Blockare 3).*

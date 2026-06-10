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

### Blockare 1 — sweden_master_data.parquet måste regenereras växande

Ligger i `Pipeline\01. Clustering\Sweden_clustering_SQL\parquet\sweden_master_data.parquet` (~536 MB).
Datumstämpel 2025-12-08 indikerar att den är BCG-original/oförändrad sedan leverans — inte uppdaterad
sedan din `transaction_data.parquet`-regenerering till 2026-04-30.

**OBS — LB.24/LF.3-skydd FÖRST:** att regenerera = att skriva över. Den nuvarande filen är den enda
fysiska kopian av BCG-original i din miljö (OneDrive-originalet ligger separat men ska aldrig röras
direkt). Backup + skrivskydd före regenerering:

```powershell
$src = "C:\Projekt\BCG\Pipeline\01. Clustering\Sweden_clustering_SQL\parquet\sweden_master_data.parquet"
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"
$bak = "$src.frozen-bak-$ts"
Copy-Item $src $bak
Set-ItemProperty $bak -Name IsReadOnly -Value $true
Get-ChildItem $bak | Select-Object FullName, Length, IsReadOnly
```

Verifiera att backup-filen finns, är 536 MB, och har IsReadOnly=True INNAN
regenererings-kommandot körs. Backup är billig (~30 sek lokal kopia); förlust av frusen baseline
är inte återställbar utan att gå till OneDrive-originalet.

**Regenerering:** kör Clustering-SQL-dataprepens wrapper med `BCG_END_DATE=2026-04-30` (samma mönster
som Cluster/Site — etablerat). `[VERIFIERA]` att wrappern finns och har G7-stöd (§5 block B).

### Blockare 2 — YearFlag-filter i Bundle-SQL (G7-skuld i SQL, inte constants)

`Sweden_Bundling_Data_Prep/scripts/01_process.sql` rad 20 + 105 + 116:
`WHERE YearFlag IN ('12M ending Jun 23','12M ending Jun 24','12M ending Jun 25')`

Med växande data filtreras allt efter juni 2025 TYST bort (samma fälla som G7 löste i Cluster/Site,
fast i SQL här). Två lösningar beror på om växande masterdata har `'12M ending Jun 26'`-flaggan:

- (a) flaggan finns → patcha SQL att inkludera den
- (b) saknas → skriv om datumbaserat (`InvoiceDate >= START_DATE AND < END_DATE2`) via
  `_inject_dates`-mönster

**`[VERIFIERA]`** YearFlag-population i regenererad parquet (§5 block A) → avgör (a) vs (b).

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
# A) YearFlag-population i FRUSEN masterdata (avgör SQL-patch a vs b)
# Primärt: oneliner. Om PS bryter på citat-escape (LB.21/KÄRNPRINCIPER §5) — kör script-versionen.
py -3.11 -c "import duckdb; print(duckdb.connect().execute(\"SELECT YearFlag, COUNT(*) n FROM read_parquet('C:/Projekt/BCG/Pipeline/01. Clustering/Sweden_clustering_SQL/parquet/sweden_master_data.parquet') GROUP BY YearFlag ORDER BY YearFlag\").df())"
```

```powershell
# A-fallback om oneliner bryts:
py -3.11 "C:\Projekt\BCG\check_yearflag_population.py"
```

```powershell
# B) Clustering-SQL-dataprepens kodbas (finns regenererings-wrapper med G7-stöd?)
Get-ChildItem "Pipeline\01. Clustering\Sweden_clustering_SQL" -Recurse -Include "*.py","*.sql","*.ps1" | Select-Object @{N='RelPath';E={$_.FullName.Replace("$PWD\Pipeline\01. Clustering\Sweden_clustering_SQL\",'')}}, @{N='KB';E={[math]::Round($_.Length/1KB,1)}}, LastWriteTime | Sort-Object RelPath | Format-Table -AutoSize -Wrap
```

```powershell
# C) Bundle Ray-init + ray_spill (bekräfta patchställen)
Select-String -Path "Pipeline\02. Elasticity\4. Bundle Clinic Data Prep\1.Data_Pre_Processing\code\*.py" -Pattern "ray_spill|object_store_memory|directory_path|C:\\\\" | Select-Object @{N='File';E={Split-Path $_.Path -Leaf}}, LineNumber, Line
```

---

## 6. REVIDERAD TIDSUPPSKATTNING (premiär hela kedjan)

| Steg | Tid | Risk |
|---|---|---|
| Backup + read-only på frusen masterdata (Blockare 1) | 1 min | Låg |
| Regenerera sweden_master_data.parquet växande | 30-60 min | Låg (etablerat mönster) |
| Verifiera YearFlag + besluta SQL-patch (a/b) | 5-15 min | Låg |
| Patcha 01_process.sql (YearFlag/datumfilter) | 15-30 min | Medel (premiär) |
| Patcha feature_selection.py ray_spill (VM) | 5 min | Låg (= Cluster) |
| Hårdpatcha bundle_utils.py object_store_memory till 8 GB | 5 min | Låg (beslutat) |
| Bundle SQL-dataprep-körning (Python-wrapper) | 30-60 min | Medel (premiär lokalt) |
| Ray-varukorgsbygge | 30-60 min | Medel (premiär) |
| Bundle-modell VM (steg 1-4) | 60-90 min | Medel (Site tog ~70 min) |
| Bundle steg 5 lokalt (xlwings) | 30-45 min | Låg (beprövat) |

**Realistiskt: 3.5-5.5h för clean körning.** Premiär över hela kedjan → räkna med felsökning ovanpå.
(NEXT_SESSION:s 2.5-4h antog "regenerera + kör"; den underskattade SQL-G7 + Ray-patcharna.)

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
- **G7** datumfönster env-överstyrbart (constants klart för Bundle-modell; SQL-dataprep är skulden)

---

*Sammanställd 2026-06-10. Reviderad samma dag efter senior review: (1) backup + IsReadOnly före
regenerering tillagt i Blockare 1 (LB.24/LF.3); (2) Blockare 3 design-val beslutat — hårdpatch 8 GB,
config-driven flyttad till FD.11; (3) §5 kommando A kompletterat med .py-fallback för LB.21-säkerhet.
De tre `[VERIFIERA]`-fälten (YearFlag-population, Clustering-wrapper-recept, Ray-patchställen)
bekräftas med §5-kommandona i början av nästa session — billiga läs-operationer som avgör exakt
arbetsmängd innan VM:en tickar.*

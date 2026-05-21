# TECHNICAL_PREREQUISITES — SQL data prep (Spår B): tekniska förutsättningar & kravlista

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_SQL.md`,
`MASTER_AZURE.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md.

**Syfte:** Lägga fram de tekniska förutsättningarna för att drifta BCG:s SQL-prep själva —
vad vi *har*, vad vi *saknar*, vad som är teknisk skuld, var det ska köra — och en **komplett,
proaktiv kravlista till IT/dataplattform** så att vi frågar en gång med full bild, inte reaktivt.

**Avgränsning (viktig):** Detta är en **PoC**. Målet är att bevisa att Evidensia kan reproducera och
sedan drifta flödet — inte att leverera en enterprise-härdad lösning i fas 1. Linux/Ubuntu-genvägar
är tillåtna för att komma vidare (D8/D13). Det som inte är PoC-klart loggas här som skuld.

**Senast uppdaterad:** 2026-05-21 (efter B.1, bit-för-bit-validering av SQL-prepen).

---

## 1. Vad B.1 bevisade — baslinjen allt vilar på

DuckDB-Python-replikatet (`replicate_dataprep.py`) kör BCG:s tre SQL-filer **verbatim** genom
duckdb-paketet (D4, ingen `.exe`, noll SQL-redigeringar) och validerades mot BCG:s frusna `0828`-facit
i fyra lager. Utfall: **bit-för-bit på radnivå.**

| Output | Rader | Distinkta `ItemCode` | Grupper (`PG4 × kluster`) | Σ `TotalNet` | Row-level |
|---|---:|---:|---:|---:|---|
| `weekly_cluster` (P_C) | 485 248 | 1 151 | 155 | 6,506 mdr | matchat 485 248/485 248, korr 1,0, max diff 0 |
| `weekly_ch` (P_CH) | 196 464 | 1 151 | 45 | 6,506 mdr | matchat 196 464/196 464, korr 1,0, max diff 0 |

**Vad det betyder, konkret:** logiken är korrekt portad, **och** `0828`-facit kom från exakt denna
SQL-version. Replikatet är nu **golden reference** — den regressions-orakel som de framtida T-SQL-vyerna
stäms av mot. Detta var det enda tillfället en bit-för-bit-grind var möjlig (BCG:s egen input, vår motor);
allt nedströms kan bara *avstämmas*, inte *matchas*, eftersom levande DW-data driver isär.

🟢 **Bra praxis fastlagd:** rökstest → full körning → validera mot facit i lager (population → kolumner
→ KPI → row-level) → dokumentera. Samma mönster som bar modell-sidan.

---

## 2. Datatillgång — gap mot datavaruhuset

De sex faktiskt använda inputs (kodverifierat — `DIM_Customer` 161 MB och `DIM_Patient` 577 MB ligger i
`input/` men **läses aldrig**; deras CTE:er är bortkommenterade. 738 MB död input, migreras ej).

| BCG-input | Vad SQL:en drar | I DW (`MASTER_SQL`)? | Verdikt |
|---|---|---|---|
| `transaction_data.parquet` (1,0 GB) | Faktan: `SalesTotal`, `SoldQuantity`, `NoofUnits`, `InvoiceDate`, ID:n, `PercentageChange` | Råmaterial: ja (`Manual.Fact_Sales_RowLevel`). Filen är **Alteryx-derivat** med odokumenterad netto/retur-logik | Rekonstruerbar — men **G1**: lineage saknas. Största arbetet vid källbyte |
| `loc.Dim_Item 20250627.csv` (288 MB) | `ProductGroupL1–4Name` (= grupperingsnyckeln), `ItemCode`, `ItemType` | `Manual.Dim_Item_Extended` finns — men **PG-L4 syns inte i spegellistan** | 🔴 **G2 / jokern.** Måste verifieras (§6). Saknas PG-L4 = enda äkta blockeraren |
| `loc.Dim_Department.csv` | `Group`, `CostCenterCode`, `DepartmentType`, `BusinessArea` | `dbo.Dim_Department` (har BusinessArea, Region) | Sannolikt reproducerbar; verifiera kolumnnamn (L.22) |
| `Sweden_Clinic_Cluster_Mapping.csv` | `ID_Department → Cluster` | **Nej** — BCG:s clustringsoutput (mapp 01) | **G3: unik seed-data** |
| `Updated_site_cluster.csv` | Fallback-klustermappning | **Nej** — samma härkomst | **G3: unik seed-data** |
| `Sweden_Interpolated_Productivity_time.csv` | FTE/vecka/klinik | Källa (Quinyx) ja: `Fact_Quinyx_DayClinic`. **Interpolationen** är separat Python | **G4**: råmaterial finns, härledningen är egen artefakt |

**Svar på "vad är unik data vi inte har i DW":** endast (a) de två klustermappningarna (seed från
clustringssteget) och (b) FTE-*interpolationen* (en härledning, inte en tabell). Allt annat finns eller
är rekonstruerbart — **med PG-L4-jokern (G2) som enda öppna blockerare.** Den kolumnen styr modellens
hela gruppindelning; finns den inte i DW vill vi veta det nu, inte i vy-byggesfasen.

---

## 3. Compute-verdikt — var körs vad

Tre fakta som löser upp en vanlig hopblandning (PoC-motor ≠ prod-datalager):

1. **DuckDB är ett Python-paket, inte en `.exe`.** `python -m pip install duckdb` är AppLocker-rent (D4).
   `duckdb.exe` (det `PLACE_DuckDB_here.txt` ber om) är dött, rörs aldrig.
2. **PoC-compute kräver inte Azure.** Bevisat lokalt: hela prepen på 1,0 GB parquet körde på din maskin
   (`00_read` 6 s, `01_process` 524 s, `02_export` 171 s, ~12 min totalt). Inget OOM — detta är
   relationella ops, inte Ray-brute-force. Det som pegade RAM på modellsidan var feature_selection, ej detta.
3. **DuckDB ska aldrig "produktionssättas".** Det är harness + golden reference. Det långsiktiga
   datalagret är `Manual`-vyer i Fabric/DW (T-SQL).

| | PoC-motor | Långsiktigt datalager |
|---|---|---|
| Verktyg | DuckDB-Python (lokalt; ev. VM för konsolidering) | T-SQL-vyer i `Manual`-schemat (Fabric F64) |
| Roll | Reproducera + golden reference | Drift, matar prismodellen |
| Kostnad | ~0 lokalt; VM ~8–10 kr/h igång (deallokera!) | Befintlig DW-licens |

🟢 **Rekommendation:** utveckla och validera lokalt (snabbast, ~0 kr, AppLocker-rent). Bekräfta sedan
**en** körning på `bcg-poc-vm` som portabilitets-/konsolideringsbevis (löser samtidigt den Azure-validering
du efterfrågade) — men iterera inte på VM:en, det bränner tid och pengar i onödan.
⚠️ **Innan VM-körning:** G11 (nedan) måste hanteras — `02_export`:s backslash-sökvägar bryter på Linux.

---

## 4. Teknisk skuld & spec-register (PoC vs hållbart)

Allt nedan replikeras **as-is** i fas 1 och loggas; inget åtgärdas nu (verbatim-principen, D7).
"Mot vem" = vem som äger frågan på sikt.

| ID | Skuld / lucka | PoC-hantering | Krav för hållbar drift | Mot vem |
|---|---|---|---|---|
| **G1** 🔴 | `transaction_data.parquet` — Alteryx-derivat, odokumenterad netto/retur/moms-logik | Behåll parquet som input | Mappa mot `Fact_Sales_RowLevel`; dokumentera transaktionstyper | Konsult + oss |
| **G2** 🔴 | `ProductGroupL4Name` styr grupperingen; oklart om DW har den | Använd BCG:s `Dim_Item`-snapshot | Verifiera PG-hierarki i DW; point-in-time eller current? | Dataplattform |
| **G3** 🟡 | Klustermappningar = seed-data, ej DW | Ladda som fasta referenstabeller | Clustringen (mapp 01) körbar/underhållen, eller mappning som DW-tabell | Oss + konsult |
| **G4** 🟡 | FTE-interpolation = separat Python-artefakt | Ladda CSV:n | Reproducera från `Fact_Quinyx_DayClinic` (eget delprojekt) | Oss |
| **G5** 🟡 | `Sum_FTE_Interpolated` summeras på item-granularitet → samma kliniks FTE dubbelräknas över items | Replikera as-is | Sannolikt oavsiktligt — fråga konsult om avsikt | Konsult |
| **G6** 🔵 | Kolumn `QuantitySold(SalesTotal>0)` men CASE använder `>= 0` | Replikera as-is | Moot inom filtret (allt `>0`); namn≠logik. Logga | Konsult |
| **G7** 🔴 | Hårdkodade fiskalår (`'...23/24/25'`) + veckofönster `2022-07-01..2025-06-28` | Replikera as-is | **Parametrisera innan färsk data** — annars filtreras 2026 tyst bort (samma klass som `constants.py`) | Oss |
| **G8** 🔵 | Tre olika juni-slutdatum i kedjan: YearFlag t.o.m. 30/6, `weekly_base` kapar 28/6, `constants.py` 29/6 | Replikera as-is | Stäm av gränsveckan; ev. harmonisera | Konsult + oss |
| **G9** 🔵 | DuckDB-syntax som ej överlever till T-SQL: `read_csv(columns=)`, `read_parquet`, `MACRO`, `date_trunc('week')`, `strftime`, `* REPLACE`, `USING`-join, `COPY` | — | Medveten T-SQL-översättning per konstruktion. **Särskilt `date_trunc('week')`: tvinga måndag explicit** (T-SQL `DATETRUNC` beror på `DATEFIRST` → annars tyst dagförskjutning av varje veckobucket) | Oss |
| **G10** 🔵 | Top80-tröskel blandar `<= 0.81` och `<= 0.80` (asymmetriskt) | Replikera as-is | Fråga konsult om avsikt | Konsult |
| **G11** 🟡 | `02_export` skriver `output/\name.csv`; Linux skapar filer som faktiskt heter `\name.csv` | Windows normaliserar bort; runnern hittar dem ändå | Städa sökvägar (forward slash, ingen ledande separator) inför VM/Linux + T-SQL | Oss |
| **G12** 🔵 | Kolumn-namndrift aug→dec: `No of Sites`↔`No_of_Sites`; P_CH `Cluster`↔`New_Cluster` | Alias i validatorn | Bestäm kanoniska namn för DW-vyerna | Oss |
| **G13** 🟡 | V2-SQL producerar **inte** två härledda kolumner som aug-facit hade: `TotalNetXVat`, `Productive_time_per_site` | Noteras | **Klargör om modellens `data_prepration` / prismodellen behöver dem.** Om ja: rekonstruera (`TotalNetXVat = TotalNet*(1+moms)`; `Productive_time_per_site` ≈ `Sum_FTE_Interpolated / No_of_Sites`) | Konsult + oss |
| **TD5** 🔵 | DuckDB som runtime | OK (Python-lib) | Arkitekturbeslut: behåll DuckDB-på-Fabric eller ren T-SQL-vy? | Dataplattform |
| **TD7** 🔵 | `02_export` skriver `Sweden_masterdata.csv` = **6,8 GB** varje körning, konsumeras ej av cluster/CH-valideringen | Acceptera (faithful) | Gör masterdata-exporten valbar i drift/iteration | Oss |

**Enda substansfrågan kvar i själva prepen är G13** — två härledda kolumner som föll bort mellan
versionerna. Allt annat matchar exakt eller är ren replikerings-hygien.

---

## 5. Komplett IT-/dataplattform-kravlista (proaktiv)

### 5.1 🟢 Vad vi redan verifierat att vi har (ingen IT-fråga behövs)
- **DuckDB via pip** — AppLocker-rent, ingen `.exe`. Bevisat kört på 1,0 GB lokalt.
- **Lokal compute räcker** för SQL-prepen (~12 min, inget OOM).
- **BCG:s sex källfiler finns** lokalt för replikering.
- **DW-access finns** (`se-az-we-bi-dw-sqldb-01`, AAD-token) — räcker för att bygga `Manual`-vyer.
- **PIM Contributor** på `ev-openai-swce-rg-test` + `bcg-poc-vm` för ev. VM-konsolidering.

### 5.2 🔴 Vad vi behöver svar/leverans på (samlad fråga, inte styckevis)
1. **PG-hierarki i DW (G2 — kritiskt):** Bär `dbo.Dim_Item` / `Manual.Dim_Item_Extended`
   `ProductGroupL1–4Name`? Är de **current** eller **point-in-time**? (Avgör om gruppindelningen kan
   reproduceras stabilt för historiska *och* färska perioder.)
2. **Klustermappningarnas hemvist (G3):** Var lever clustringsoutputen, och hur underhålls/körs den om?
   Ska mappningen bli en DW-tabell i `Manual`?
3. **Produktiv tid (G4):** Bekräfta `Fact_Quinyx_DayClinic` som källa; FTE-interpolationen är vår att
   reproducera — flaggas som eget delprojekt, ej blockerare nu.
4. **Runtime-arkitektur (TD5):** Stödjer dataplattformen DuckDB-på-Fabric, eller ska prepen vara ren
   T-SQL-vy i `Manual`? Arkitekturbeslut innan B.4 låses.
5. **(Endast om drift) Skrivmål för modell-input (O4):** Blob input-folder eller DW-tabell där den
   färdiga veckodatan landar för prismodellen. Inte PoC-blockerare.

🟢 **Notera:** punkt 1 är den enda som kan blockera vy-bygget. Resten är arkitektur/underhåll som kan
avgöras parallellt. Inget kräver att vi *väntar* på IT för att fortsätta replikeringen.

---

## 6. Öppna verifieringsuppgifter — `inspect_schema` (kör med DW-token)

🔵 **Bra praxis (L.16/L.22/L.30):** verifiera kolumnnamn innan en rad SQL skrivs. Kör detta **först**,
det löser PG-L4-jokern (G2) på 5 sekunder. Kräver `az login --scope https://database.windows.net/.default`.

```sql
-- G2: finns produktgruppshierarkin i DW, och under vilka namn?
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME LIKE '%ProductGroup%' OR COLUMN_NAME LIKE '%PG%L4%'
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
```

```sql
-- Department-kolumner som dept_sel drar (Group, CostCenterCode, DepartmentType, BusinessArea)
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Dim_Department' ORDER BY ORDINAL_POSITION;
```

```sql
-- Fact_Sales_RowLevel: bär den fälten vi behöver för G1 (SalesTotal, SoldQuantity, NoofUnits, datum, ID:n)?
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'Manual' AND TABLE_NAME = 'Fact_Sales_RowLevel' ORDER BY ORDINAL_POSITION;
```

Utfallet styr B.4: finns PG-L4 → vy-bygget är rakt. Saknas → G2 blir en dataplattform-fråga (5.2.1) och
T-SQL-vägen pausar på den punkten, men replikatet (B.1) står oberörd.

---

## 7. Nästa steg

| Etapp | Innehåll | Kräver | Validering |
|---|---|---|---|
| ✅ B.1 | DuckDB-replikat + facit-validator | — | **Bit-för-bit (klart)** |
| **B.2** | `inspect_schema` mot DW (§6), PG-L4-jokern först | DW-token | Kolumn-täckning |
| B.3 | *Detta dokument* | — | — |
| B.4 | T-SQL `Manual`-vyer, medveten G9-hantering | B.2 grön (G2 löst) | Strukturell + KPI-avstämning mot golden reference |
| B.5 | Parametrisera datum (G7), G13-beslut, dokumentera | — | — |

**Rekommendation:** B.2 (`inspect_schema`) är minst och löser den enda blockeraren (G2) innan vy-bygget.
Den behöver bara DW-token och ett kort godkännande att leverera inspect-scriptet. G13-frågan (behövs de
två härledda kolumnerna?) bör ställas till konsult parallellt — den avgör vy-byggets kolumnomfång.

---

*Skapad av Jens Palmö (utvecklare) med AI-rådgivaren, 2026-05-21, efter B.1:s bit-för-bit-validering.*

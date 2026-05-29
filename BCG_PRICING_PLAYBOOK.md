# BCG_PRICING_PLAYBOOK — Operationell playbook

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lokal sökväg:** `C:\Projekt\BCG`
**Developer:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB), with AI advisor.
**Senast uppdaterad:** 2026-05-29

---

## Riktningsblock (läs först)

**Dagens läge (2026-05-29):**

Spår B är **operationaliserat och validerat** på två fönster:

| Mått | Frusen BCG-fönster (2022-07..2025-06) | Växande fönster (2022-07..2026-04) |
|---|---|---|
| Rader | 484,827 (vs facit 485,248 = -0.09%) | 610,039 (+25.8% data) |
| TotalNet | 6.50 mdr (vs facit 6.51 mdr = -0.057%) | 8.27 mdr (+27.2%) |
| ItemCodes | 1,151 (samma) | 1,151 (samma facit-urval) |
| KEY | 4,930 (vs facit 4,949) | 4,930 |
| FTE NULL | 0 | 122,214 (20.03%, veckor 2025-07-07..2026-04-27) |

`export_b4b_for_model.py` reproducerar BCG:s frusna facit med 0.057% snapshot-drift på revenue (väntat
band) och producerar en växande-fönster-CSV som ligger på plats i Pipeline\data\. Nästa steg:
pipelinekörning lokalt på cluster-familjen — se `NEXT_SESSION.md`.

**G7 (datumfönster) är klart:** `BCG_END_DATE` env-vars styr pipelinens och export_b4b:s datumfönster.
Default = BCG:s frusna fönster (bevisat bit-identiskt). Override aktiverar växande fönster.
Konsoliderad i denna playbook (avsnitt 6); ingen separat FAS_F_G7.md behövs.

---

## 1. Projektets syfte och narrativ

BCG (Boston Consulting Group) levererade i 2025-07 en Python-baserad priselasticitetspipeline till
Evidensia. Pipelinen producerar elasticitets-KPI:er per produkt × kluster (och finare nivåer) via
OLS-regression med kombinatorisk feature-selektion, Ray-parallelliserad. Output går in i ett
Excel-baserat prisbeslutsverktyg.

Evidensias mål: **internalisera modellen.** Köra den på färsk data månadsvis, kunna förvalta den utan
BCG-konsulter, och så småningom automatisera den i Azure.

Projektets fasstruktur:

| Fas | Mål | Status |
|---|---|---|
| **V** — Validate | Bevisa att vi reproducerar BCG:s tal bit-för-bit på BCG:s data | KLAR (commit `824c265` på main, 2026-05-26) |
| **T** — Tech debt | Pinnad miljö, sökvägs-hygien, dokumentation, runbooks | Pågående parallellt, inte blockerande |
| **F** — Fresh data | Köra modellen på dagens DW, inte BCG:s 2025-07-snapshot | **Pågår 2026-05** — Spår B operationaliserat, pipelinekörning återstår |
| **A** — Azure automation | Schemalagd månatlig körning utan Jens dator | Framtid; kräver Blob-roll först |

---

## 2. Arkitekturöversikt

```
                                    +----------------------------+
                                    | Business_Analytics          |
                                    | (DW-extraktion + validering) |
                                    +----------------------------+
                                              |
                                              v
                                  export_b4b_for_model.py
                                  (DW + cluster seed + facit-pairs + FTE)
                                              |
                                              v
                              0828_Sweden_weekly_model_data_P_C.csv
                                              |
                                              v
                                  +-------------------------+
                                  | C:\Projekt\BCG\Pipeline |
                                  | (BCG:s ursprungspipeline)|
                                  +-------------------------+
                                              |
              +---------------+---------------+---------------+
              v               v               v               v
        01_clean.sql    feature_selection   model         output_summary.xlsx
        (DuckDB)        (Ray, OLS)          (OLS per KEY)
                                                                |
                                                                v
                                                         verify_tool
                                                         (proves vs BCG facit)
```

**Tre modellfamiljer** (alla körs separat med varsin pipeline-katalog):

| Familj | Grain | Grupper | Pipeline-katalog |
|---|---|---|---|
| Cluster | ItemCode × Cluster (7 kluster) | 3,812 | `2. Product Cluster Level Models` |
| Site | ItemCode × Department | 4,673 | `3. Product Site Level Models` |
| Bundle | Varukorgar × Hospital/Clinics | 125 | `5. Bundle Clinic Models` |

**Fallback-väv (steg 6, FR-7):** F1-F7-logik blandar alla tre familjers utdata till slutgiltig
elasticitet per ProductKey. Hanterar svaga grupper genom representant-arv (IB.2).

---

## 3. Pipeline-steg och deras placering

Pipelinen finns i `C:\Projekt\BCG\Pipeline\02. Elasticity\`. Tre huvudsteg per modellfamilj:

### Steg 0: Dataprep (gemensam)
- `Sweden_Elasticity_Data_Prep_SQL\scripts\00_read.sql` — läser parquet (eller CSV i Spår B)
- `Sweden_Elasticity_Data_Prep_SQL\scripts\01_process.sql` — DuckDB-process till veckograin
- `replicate_dataprep.py` — orkestrerar SQL-stegen, validerar mot facit

### Steg 1-3: Per modellfamilj
1. `01_clean.sql` (DuckDB) — läser `0828_..._P_C.csv` → renad parquet
2. `feature_selection` (Python, Ray-parallelliserad OLS) — kombinatorisk feature-val per grupp
3. `model` (Python, OLS per KEY) — slutgiltig elasticitet → `output_summary.xlsx`

### Steg 4: Cluster-blend (FR-3)
- Cluster-familjen → `fallback_blend.py` → `final_model_cluster_granularity.xlsx`

### Steg 5: Bundle-blend
- Bundle-familjen → bundle-output

### Steg 6: Fall_Back_Logic (FR-7)
- `6. Fall Back Logic\Fall_Back_Logic.py` — F1-F7-väv över alla tre familjer
- Output: `Final_Fallback_Data_<timestamp>.xlsx` med slutgiltig elasticitet per ProductKey

---

## 4. Python-miljöer (KÄNN DEM)

Tre olika Python-miljöer med olika paket. Använd rätt för rätt jobb (LB.26/LB.27/LB.30).

| Miljö | Sökväg | Har | Används till |
|---|---|---|---|
| Global 3.11 | `C:\Users\jepa02\AppData\Local\Programs\Python\Python311\` | duckdb, pandas, openpyxl, numpy, pyyaml | verify_tool, dataprep-validering |
| Business_Analytics | `C:\Projekt\Business_Analytics\.venv` | pyodbc, pandas | DW-extraktion (export_b4b_for_model.py, compare_to_0828_facit.py) |
| Pipeline | `C:\Projekt\BCG\Pipeline\02. Elasticity\.venv` | duckdb, Ray, statsmodels | Pipelinens beräkningar (feature_selection, model) |

**Inga installationer "för säkerhets skull"** — använd den venv som redan har paketet. Om en venv
saknar ett paket: byt venv, installera inte.

---

## 5. Köra hela kedjan (FAS V — replikering mot BCG facit)

För att bevisa att replikeringen fortfarande håller:

```powershell
cd "C:\Projekt\BCG\verify_tool"
py -3.11 verify_infra.py        # miljö-check
py -3.11 run_all.py             # full kedja, FR-1..7
py -3.11 run_all.py --excel     # +daterat Excel-kvitto i receipts\
```

Förväntat utfall (FAS V validerad 2026-05-26):
- FR-1 (dataprep): 485,248 + 196,464 rader, corr 1.000000, diff 0
- FR-4 (cluster): 3812/3812 grupper, median |diff| 0, rank-corr 1.000
- FR-5 (site): 4673/4673, median |diff| 0, rank-corr ~0.91
- FR-6 (bundle): 125/125, median |diff| 0, rank-corr ~0.93
- FR-3 (blend): 43/43 representanter, signifikans 43/43
- FR-7 (fallback): corr 1.000000, |diff| 0, 100% nivåmatch, 108,979 rader / 15,128 ProductKeys

---

## 6. G7 — Datumfönster-parametrisering (FAS F första milstolpe)

### 6.1 Vad G7 löser

BCG:s pipeline hårdkodade datumfönstret (`2022-07-01..2025-06-29`) i flera filer. Med fresh data
2026 skulle detta **tyst filtrera bort allt efter juni 2025** — ingen krasch, bara fel (gamla)
resultat. G7 gör fönstret env-overridable: en färsk körning kräver **ingen kodändring**.

### 6.2 Designprincip — default reproducerar gammalt facit exakt

Med inga env-vars satta beter sig varje ändrad fil bit-för-bit som tidigare. Bevisat:
`verify_dataprep.py` utan env → `overall=PASS`, corr 1.000000, 485,248 + 196,464 rader, diff 0.000% — FR-1
oberörd. Vägen tillbaka till BCG:s frusna fönster är att köra utan env-vars (eller `git checkout main`).

### 6.3 Körning av färskt fönster

```powershell
$env:BCG_END_DATE = '2026-04-30'   # sista datum att inkludera
# optional:
# $env:BCG_START_DATE = '2022-07-01'   # fast ankare (default redan detta)
# $env:BCG_SPECIAL_WEEKS = '...'        # comma-separated media weeks; default = BCG:s
```

`END_DATE2` (exklusiv övre gräns i modell-filter) **härleds automatiskt** som `END_DATE + 1 dag` —
sätt aldrig manuellt.

**Fönstertyp:** växande fönster med fast ankare (alltid 2022-07-01, växer när månader läggs till).
Rullande fönster (t.ex. senaste 36 månader) är ett medvetet senare analytiskt steg — inte byggt här.

Tillbaka till frusen: `Remove-Item Env:BCG_END_DATE`.

### 6.4 Vad ändrades (allt på branch `fas-f-fresh-data`)

| Fil | Ändring |
|---|---|
| `constants.py` (cluster) | Datumblock → env-overridable; `END_DATE2` derived; `SPECIAL_WEEKS` env-overridable |
| `constants.py` (site, bundle) | Samma datumblock, kirurgiskt (granularitet bevarad) |
| `data_prepration.py` (cluster) | Hårdkodad `'2025-06-23'` → `END_DATE` (W-MON-rundning gör dem ekvivalenta) |
| `data_prepration.py` (site, bundle) | Ingen ändring — använde redan `END_DATE` |
| `replicate_dataprep.py` | `_inject_dates()`: env-gated in-memory rewrite av SQL-fönstret. SQL-filen på disk oförändrad |
| `01_process.sql` | Ingen ändring — datumfönster injiceras in-memory av Python ovan |
| `export_b4b_for_model.py` (2026-05-29) | Env-overridable `BCG_START_DATE`/`BCG_END_DATE`, FY-filter borttaget, FTE NULL-rapportering |

---

## 7. Output-separation (FAS F prerequisite 1 — DONE 2026-05-28)

Facit-isolering, löst Jens väg: BCG-originalet ligger orört i OneDrive (det ÄR det frusna facit; vi
skriver aldrig dit). Vår **bevisade baslinje** — VM-körningens utdata som verify_tool visade matcha
BCG bit-för-bit — ligger kvar och är nu **read-only** så en felriktad färsk körning inte kan skriva
över beviset:

| Bevisad baslinje (read-only) | Storlek |
|---|---|
| `2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx` | 326,890 |
| `3. Product Site Level Models\output\azure_run_model\output_summary.xlsx` | 398,885 |
| `5. Bundle Clinic Models\output\azure_run_model\output_summary.xlsx` | 15,921 |
| `_step6_run\...\Final_Fallback_Data_20260527_085906.xlsx` | step 6 |

**Konvention för färska körningar:** skriv till en parallell, daterad systermapp — aldrig in i
`azure_run_model`:

```
...\<model>\output\azure_run_model\       <- bevisad baslinje (read-only, rör aldrig)
...\<model>\output\fresh_run_2026-05\     <- färsk körnings output (ny plats)
```

Detta håller bevisad och färsk sida vid sida: verify_tool / rimlighetskontroller kan peka på endera
via sina `--args`, och den daterade mappen självdokumenterar vilken körning som är vilken. Den färska
mappen skapas **när körningen sker** (inte förbyggd). Steg 6 följer samma mönster
(`_step6_run` → `_step6_run_fresh_<date>`).

För att åter-aktivera skrivning till en baslinje-fil (t.ex. för att medvetet regenerera):
`Set-ItemProperty <file> -Name IsReadOnly -Value $false`.

---

## 8. Vad återstår före en riktig färsk körning

G7 gör fönstret *settbart*. Det räcker inte för giltiga färska resultat — tre prerequisites kvarstår:

1. **Facit-isolering** — KLAR (avsnitt 7 ovan).

2. **Färsk källa, inte bara färskt fönster (Spår B)** — KLAR 2026-05-29.
   `export_b4b_for_model.py` läser nu från DW direkt, inte BCG:s frusen parquet. Validerat mot facit
   med 0.057% snapshot-drift.

3. **Datafullständighets-grind (Nivå 1-säkerhet)** — ÅTERSTÅR.
   Innan auto-körning av "senaste stängda månad": verifiera att DW faktiskt har komplett data för hela
   fönstret. Att köra en ofullständig senaste månad = tyst fel. Detta är grinden som gör månatliga
   auto-körningar säkra. (Auto-beräkning av "senaste stängda månad" är ett steg bortom env-override —
   bygg grinden först, auto-beräkningen sen.)

Efter dessa tre: kontrollerad färsk körning, följd av rimlighetsvalidering mot det isolerade facit
(IB.6 — diffar små nog att inte flippa ett top-line-prisbeslut).

---

## 9. Vision (förvaltning framåt)

Slutmålet: modellen kör senaste stängda månads data automatiskt; månadsuppdatering = bara kör skriptet,
inga filändringar; på sikt i Azure utan Jens dator, körbart av kollegor utan Python-kunskap. Sekvens:
env-override (KLAR) → auto-beräkna senaste månad + datagrind (NÄSTA) → Azure-automation (FAS A, långt
senare). Växande fönster med fast ankare 2022-07-01 (rullande trender = medvetet senare analytiskt
steg, inte nu).

---

## 10. FAS T (tech-debt — kräver ingen kod, kräver IT)

Strukturera skuldregistret till IT så miljön inte bara bor i repot:

- **Miljö i global Python 3.11**, inte isolerad venv — ej reproducerbar (nu även pyyaml där). Pinnad
  venv + requirements.txt behövs (förutsättning för FAS A).
- **Relativa sökvägar i site/bundle `constants.py`** (`.\code\src\config.yml`) — körning platsberoende,
  kraschar från fel katalog.
- **Frusna externa beroenden** (FTE-XLSX täcker till 2025-06, facit-pairs frusna till BCG:s urval,
  cluster-seed frusen till 58 kliniker). Tre olika filer, frusna vid olika tidpunkter, läses av olika
  pipeline-steg — kan inte uppdatera *en* utan att tänka på de andra två.
- **Inget run_all-script för pipelinen** — manuell orkestrering, glöm-faktor.
- **Två oberoende output-vägar (Spår A vs Spår B)** med samma filnamn — riskerar tyst förorening
  (L.43/LB.29).
- AppLocker (.exe/pip.exe), execution policy (LB.21), blob-roll-blockering (Storage Blob Data
  Contributor, kräver Owner), lokal OOM på Stage 2 (varför VM behövs).

---

## 11. Decision log (utvalda beslut)

### D-B1 (2026-05-22): BCG:s transaction_data-källa = dbo.Fact_BillingInvoiceRows
Bekräftat via PBI-datasetets M-query. Stänger källtvetydigheten.

### D-B2 (2026-05-22): Cluster-seed-frågan
Beslut: använd BCG:s 0808-seed som-is för Spår B-replikering. Färska kluster är ett senare analytiskt
steg, inte ett extraktions-spår.

### D-B3 (2026-05-22): Net/brutto = brutto
Bekräftat empiriskt via median-kvot 1.0000 mellan SalesTotal och SalesExVAT × 1.25. SalesTotal är
modellens omsättning, brutto inkl 25% moms.

### D-B6 (2026-05-22): Dim_Item_Extended kontra dbo.Dim_Item
Beslut: använd Manual.Dim_Item_Extended för rikare hierarki, men kör coverage check innan deployment
(noterad i `b4b_dw_weekly_elasticity.sql`).

### D-F-G7 (2026-05-28): Datumfönster-parametrisering via env-vars
Beslut: G7-mönster (env-vars med defaults = BCG:s gamla fönster) över hela pipelinen. Default
bit-identiskt med tidigare — ingen risk att glömma och därför inte revertera.

### D-F-output-separation (2026-05-28): Read-only baslinje + daterade systermappar
Beslut: bevarad baslinje skrivskyddad, fresh-körningar skriver till `fresh_run_<datum>\` parallellt.
Ingen robocopy-dubblering behövs.

### D-F-29 (2026-05-29): export_b4b som operationaliserad DW-källa
Beslut: använd `export_b4b_for_model.py` som permanent DW-källa för Spår B (ersätter frusen parquet).
Validerad mot facit. Cluster-seed och FTE-XLSX kvarstår frusna (tech-debt, inte blockerande).

---

## Hur listan växer

Nytt beslut → ny D-rad. Nytt steg i pipelinen → nytt avsnitt under §3 eller §5. Status uppdateras i
riktningsblocket vid sessionsslut.

Vid sessionsstart: läs riktningsblocket. Vid sessionsslut: uppdatera riktningsblocket och avsnitt 8
("Vad återstår").

---

*Skapad 2026-05-26 som operativ playbook ovanpå pipelinens fysiska struktur. Uppdaterad löpande;
G7-innehållet (tidigare FAS_F_G7.md) konsoliderat in 2026-05-29 — egen fas-fil avskaffad till förmån
för NEXT_SESSION + denna playbook.*

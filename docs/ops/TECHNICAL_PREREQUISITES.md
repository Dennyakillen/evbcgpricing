# TECHNICAL_PREREQUISITES — SQL data prep (Spår B): förutsättningar, omsvängning & valideringsgrind

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_SQL.md`,
`MASTER_AZURE.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md` + `ROADMAP.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md.

**Syfte:** Fastställa de tekniska förutsättningarna för att drifta priselasticitets-prepen själva, och
dokumentera den **strategiska omsvängningen**: från att *replikera BCG troget* (nu klar, FR-1..7) till att
*köra BCG:s metod på Evidensias datavaruhus, med våra dimensioner och namn*, validerat på **kodnivå mot
golden reference**. Detta är ROADMAP FAS F (DW-native / SQL_data_prep).

**Senast uppdaterad:** 2026-05-27 (D-B4 korrigerad på plats; inaktuell roadmap i §8 borttagen; FR-7 reflekterad).

---

## 1. Strategisk omsvängning (läs först — den ändrar målet)

Bit-för-bit-grinden (B.1) bevisade att vi behärskar BCG:s logik fullt ut. Därmed är trogen replikering
**inte längre rätt mål** — den har gjort sitt jobb och blir härifrån ett **referenslager**, inte leveransen.

| | Före (replikering, FR-1..7 — KLAR) | Nu (DW-native bygge, FAS F) |
|---|---|---|
| Mål | Återskapa BCG:s output exakt | Köra BCG:s **metod** på vår DW-fakta + DW-dimensioner |
| Dimensioner | BCG:s `Dim_Item`-snapshot, BCG:s gruppering | **Vår DW-hierarki** (finare än BCG:s) |
| Namn | BCG:s (`SalesTotal`, `NoofUnits`, ...) | Våra kanoniska |
| BCG:s artefakter | Facit | **Metod + golden reference** |
| Valideringsnivå | Grupp, bit-för-bit mot `0828` | **Kod (`ItemCode`), Σ mot golden reference** |

**Varför:** BCG:s artikelgruppering är grövre än vår interna; deras `Dim_Item`-mappning är deras egen
tolkning av data **vi** matade dem från DW. Källan har hela tiden varit vår. Det enda som måste hålla är
samma **omsättning och volym per enskild kod** — inte att koderna grupperas likadant. `Manual.Elasticitet`
och `MASTER_SQL`-miljön är **inte facit** — de är vår interna målbild och tekniska förutsättning, byggd av
Jens ovanpå BCG:s slutsatser. De ska byggas ihop med BCG:s metod, inte replikeras.

---

## 2. Vad B.1 + B.2 fastställde

**B.1 — golden reference (klar):** `replicate_dataprep.py` kör BCG:s SQL verbatim genom duckdb-Python
och validerades bit-för-bit mot `0828`-facit. Baslinje (referensvärden, invarianta under omgruppering):

| KPI | P_C | P_CH |
|---|---:|---:|
| Distinkta `ItemCode` | 1 151 | 1 151 |
| Σ `TotalNet` | 6,506 mdr | 6,506 mdr |
| Σ `SoldQuantity` | 6,44 M | 6,44 M |

**B.3.5 — kodnivå-baslinje (klar):** `code_level_baseline.csv` (pre-Top80, per `ItemCode`) — den
grupperingsinvarianta grinden B.4 valideras mot.

| Kodnivå-baslinje (pre-Top80) | Värde |
|---|---:|
| Distinkta `ItemCode` | **13 223** |
| Σ `SalesExVAT` | 7,985 mdr |
| Σ `SoldQuantity` | 8,61 M |

🔵 **Top80-avvägning (informerar B.4b-beslut):** Top80 behåller 1 151 / 13 223 koder (**8,7 %**) men
6,506 / 7,985 mdr omsättning (**81,5 %**). Renodlad Pareto: svansen på 91 % av koderna = ~18 % av
omsättningen. Beslut i B.4b: behåll Top80 (få kronor, många koder bort) eller modellera hela svansen.

**B.2 — DW-schemakontroll (klar):** alla nödvändiga fält finns i DW. Inget externt beroende.

| BCG-fält | DW-källa | Status |
|---|---|---|
| `SalesTotal` (brutto, inkl moms) | härleds: `SalesExVAT × 1,25` | ✅ se IB.5 / D-B4 |
| `TotalNetXVat` (netto) | `SalesExVAT` | ✅ |
| `NoofUnits` | separat kolumn (≠ `SoldQuantity`, ~16× isär) | ✅ |
| `SoldQuantity` (modellens volym) | `SoldQuantity` | ✅ |
| `InvoiceDate` | `SalesDate` (date) | ✅ |
| Returer/netto-logik | `IsCreditNote` (bit) | ✅ byggsten finns |
| ID_Customer/Department/Item/Patient | finns alla | ✅ |
| `ProductGroupL4Name` | **DW-hierarki** (ej BCG:s) | ✅ beslut: gå på DW (D-B1) |
| Dept-fält (Group, CostCenter, BusinessArea ...) | `dbo.dim_department` | ✅ alla finns |
| Kluster | `dbo.dim_department.Priskluster` + BCG-seed | ✅ dubbelspår (D-B2) |

🟢 **Slutsats:** allt är 100 % reproducerbart från DW. Spår B är inte längre en datafråga — det är att
**renodla namn och mappning** och köra BCG:s logik på vår fakta.

---

## 3. Beslut (decision log)

| # | Beslut | Motivering |
|---|---|---|
| D-B1 | **DW-native dimensionsmappning, inte BCG:s gruppering.** BCG = metod + golden reference | BCG:s gruppering grövre än vår; logiken redan bevisad replikerbar (B.1) |
| D-B2 | **Klustermappning dubbelspårig:** bär *både* intern `Priskluster` *och* BCG:s föreslagna kluster (seed) | Jens jämför BCG:s förslag mot intern + egen analys, hoppas konvergera. Båda behövs som referens |
| D-B3 | **Valideringsgrind = kodnivå mot golden reference**, mätt **före** Top80-filtret (se §5) | Omgruppering gör gruppnivå ojämförbar; kodnivå är invariant; Top80 är gruppberoende |
| D-B4 | **Namnskuggor (korrigerade, se §6):** källa = `dbo.Fact_BillingInvoiceRows` JOIN `dbo.Dim_Item`. `SalesTotal` = brutto (`SalesExVAT × 1,25`); `TotalNetXVat` = `SalesExVAT`; `NoofUnits ≠ SoldQuantity` | B.2 + databekräftat. *Ursprunglig D-B4 (`SalesTotal=SalesExVAT`, källa `Fact_Sales_RowLevel`) var fel — se §6.* |
| D-B5 | **Repo-uppdelning:** golden reference + baslinje + replikering i `evbcgpricing`; DW-native arbetet (harness, vyer, drift) i **Business_Analytics** (där `data_access`/`.env`/DW-infran bor) | DW-pratande kod hör hemma där DW-infran lever; undviker hårdkodad sys.path-skuld (R6-klass) |
| D-B6 | PoC replikerar på `dbo.Dim_Item`; `Manual.Dim_Item_Extended` (finare) = dokumenterat skalningssteg efter att struktur bevisats körande + validerad + förvaltningsbar | Skala efter bevisad struktur (KÄRNPRINCIPER: PoC mot replikering, skala efteråt) |

**Repo-karta:**
- `evbcgpricing`: `replicate_dataprep.py` (golden reference), `code_level_baseline.csv`, all dokumentation,
  `verify_tool\` (FAS V).
- `Business_Analytics`: `validate_dw_codelevel.py` (B.4a) och kommande DW-native artefakter (B.4b vy-DDL m.m.), via `data_access`.

---

## 4. Teknisk skuld & spec-register

| ID | Punkt | Status nu |
|---|---|---|
| ~~G1~~ | `transaction_data`-härkomst, netto/`NoofUnits` | ✅ **Stängd.** Källa = `Fact_BillingInvoiceRows` JOIN `Dim_Item`; ekvivalent per kod (median-kvot 1,0000, korr 0,989) |
| ~~G2~~ | PG-L4-jokern | ✅ **Avförd.** Vi tar DW-hierarkin (D-B1), inte BCG:s L4 |
| ~~G12/G13~~ | Namndrift, `TotalNetXVat`/`Productive_time_per_site` | ✅ **Avförda mot DW** — vi sätter egna kanoniska namn/kolumner |
| **G7** 🔴 | Hårdkodade fiskalår + veckofönster (`START_DATE 2022-07-01`, `END_DATE 2025-06-29`, `SPECIAL_WEEKS`) | **Kvar — gäller även DW-bygget.** Parametrisera, annars filtreras färsk 2026-data **tyst** bort. ROADMAP FAS F-blockerare |
| **G9** 🔴 | DuckDB→T-SQL-dialekt. Särskilt `date_trunc('week')` | **Kvar — central i B.4.** Tvinga måndag explicit (T-SQL `DATETRUNC` beror på `DATEFIRST` → annars tyst dagförskjutning) |
| **G5** 🟡 | `Sum_FTE_Interpolated` summeras på item-granularitet → dubbelräkning | **Kvar (metod).** Fråga: behåll BCG:s beteende eller korrigera i DW-bygget? |
| **G4** 🟡 | FTE-interpolation = egen Python-härledning | **Kvar.** Reproducera från `Fact_Quinyx_DayClinic` (FTE Väg 2, IB.3) — eget delprojekt, ej blockerare |
| **Top80-beroende** 🔴 | Top80-filtret är **gruppberoende** (topp-80 % per PG4) → byter grupp = byter urval av koder | **Kvar.** Styr valideringsgrinden (§5). Beslut i B.4: behåll Top80, och i så fall per vilken grupp? |
| ~~G11/TD7~~ | Backslash-export, 6,8 GB masterdata | ⚪ Endast relevant för DuckDB-runnern (golden reference), ej DW-bygget |

**De enda substansfrågorna kvar för DW-bygget är metodval:** datumparametrisering (G7), korrekt
veckotrunkering (G9), Top80-beslut, FTE-hantering (G4/G5). Allt är vårt att avgöra — inget kräver konsult.
*(OBS: compute-/miljöskulder som tvingade fram VM-körning — OOM, AppLocker, blob-roller — hör till ROADMAP
FAS T, inte hit. Denna tabell gäller datapreppens metodskuld.)*

---

## 5. Den nya valideringsgrinden (kritiskt — säg det innan vi bygger)

Konsekvensen av D-B1 måste vara explicit: **i samma sekund grupperingen byter från BCG:s L4 till DW-hierarkin
kan grupp-KPI:er (antal grupper, elasticitet per grupp) inte längre stämmas mot `0828`-facit.** Väntat och
accepterat. Den nya grinden:

> **Per `ItemCode`: samma Σ `SalesExVAT` (omsättning) och Σ `SoldQuantity` (volym) som golden reference.**

🔴 **Men en fälla:** BCG:s **Top80-filter är gruppberoende** (behåll topp-80 % av omsättningen *per PG4*).
Byter vi grupp byter Pareto-snittet vilka koder som överlever → kodurvalet *ska* skilja efter Top80. Därför
mäts kodnivå-grinden **före Top80** — på den filtrerade populationen (fiskalår + `SalesExVAT>0`), där
grupperingen är irrelevant och BCG-vs-DW måste matcha per kod.

| Lager | Jämför | Förväntan |
|---|---|---|
| Pre-Top80, per `ItemCode` | Σ `SalesExVAT`, Σ `SoldQuantity` vs golden reference | **Matcha** (grupperingsoberoende) — den skarpa grinden |
| Post-Top80 / per grupp | Kodurval, gruppantal, elasticitet | **Skiljer** by design — stäms ej |

🟢 **Förberedelse för B.4:** golden reference (`replicate_dataprep.py`) producerar idag post-Top80-output.
Den behöver en liten utökning: exportera en **pre-Top80 per-`ItemCode`-total** (Σ `SalesExVAT`, Σ `SoldQuantity`)
från `filtered_master_2` — det blir kodnivå-baslinjen B.4 valideras mot. Liten, isolerad ändring.

---

## 6. Bekräftade fakta & korrigeringar (databekräftade)

Detta avsnitt **ersätter** tidigare preliminära antaganden där de krockar.

**D-B4 korrigerad på två punkter (databekräftat):**
- `SalesTotal` ≠ `SalesExVAT`. `SalesTotal` är **BRUTTO inkl 25 % moms** (= `SalesExVAT × 1,25`). Modellens
  omsättning (`TotalNet`/`DOLLAR`) = `SalesTotal` (brutto); `TotalNetXVat` = `SalesExVAT` (netto). (IB.5)
- `NoofUnits` ≠ `SoldQuantity` — separata kolumner (~16× isär). Modellens volym = `SoldQuantity`.
- **Källa:** `transaction_data` kommer från `dbo.Fact_BillingInvoiceRows` JOIN `dbo.Dim_Item`
  (ej `Manual.Fact_Sales_RowLevel`). Provenans: PBI-dataset 2025-07-08, M-query `InvoiceDate >= 2020-01-01`.
- **G1/TD4 STÄNGD.** Källan bevisad ekvivalent per kod (median-kvot 1,0000, korr 0,989).

*(Princip: data avgjorde, inte kolumnnamn — "mät, gissa inte". Claudes egna tidiga gissningar om net/brutto
och NoofUnits var fel; KÄRNPRINCIPER.)*

**Modellsidan kartlagd (config.yml + constants.py + pipeline-Python) — bekräftat i replikeringsfasen:**
- **Elasticitet = log-log** → koefficienten ÄR elasticiteten direkt (IB.7).
- **Modellens KEY = `Cluster × ItemCode`** (IB.8). L4 påverkar inte kärnelasticiteten.
- **"Externa källor" mestadels inte externa** (IB.3): enda genuina uppströms-input = `Sum_FTE_Interpolated`.
- **Modellen validerad bit-för-bit** (3812 grupper, korr 1,0). Compute-risken stängd (`ray: memory:8, cpus:12`).

**Modellkontraktet (b4b → modell):** b4b ska leverera: `ItemCode, ItemDescription, week_starting_monday,
Cluster, SoldQuantity, NoofUnits, TotalNet (brutto), QuantitySold(SalesTotal>0), No of Sites,
TotalNetXVat (=SalesExVAT), Sum_FTE_Interpolated, service(=ProductGroupL4Name)`. Resten härleds i pipelinen.
För PoC: FTE droppbar ur `cols_needed` (config); `service`/L4 ej kritisk; `Cluster` = BCG-seed (jämförbar) /
Priskluster (skalning).

---

## 7. Compute & infrastruktur (Spår B / DW-bygget — PoC-mindset)

- **DuckDB-Python** (golden reference) körs lokalt, AppLocker-rent, bevisat på 1,0 GB (~12 min, inget OOM).
- **DW-bygget (B.4)** är T-SQL i `Manual`-schemat — körs där DW:t bor (Fabric F64), ingen ny infra.
- **Azure-VM** behövs inte för Spår B (den är till för modellstegens tunga körningar — se ROADMAP FAS T/A).
- **Inga externa beroenden, inga IT-asks kvar för själva Spår B-datapreppen** — allt finns i DW och är
  vårt att bygga. Det enda som inte är ren teknik är klustrings-*metoden* (D-B2), och den är
  din/verksamhetens, ej IT:s.

---

## 8. Nästa steg (Spår B / FAS F-etapper)

| Etapp | Innehåll | Validering |
|---|---|---|
| ✅ B.1 | DuckDB golden reference | Bit-för-bit (klart) |
| ✅ B.2 | DW-schemakontroll (fakta + artikeldimension) | Allt reproducerbart (klart) |
| ✅ B.3 | Detta dokument | — |
| ✅ B.3.5 | Golden reference: pre-Top80 per-`ItemCode`-baslinje (`code_level_baseline.csv`, 13 223 koder) | — |
| ✅ B.4a | `validate_dw_codelevel.py` — DW per-kod vs baslinje (Business_Analytics) | **Kodnivå-rekonciliering** |
| **B.4b** | `Manual`-vy (T-SQL): BCG:s metod på DW-fakta + DW-hierarki-grain (`Master_*`), dubbla kluster, explicit måndagstrunkering, **parametriserade datum (G7)** | **Kodnivå (pre-Top80) mot baslinje** |
| B.5 | Top80/FTE-/grupp-grain-metodbeslut, dokumentera, committa | — |

**Rekommendation:** kör B.4a → låt deltat avslöja rabatt/kredit-mappningen → fastställ filtret →
B.4b (DW-vyn). Gruppgrain-valet (`Master_Underkategori3`/`Subgrupp` ≈ BCG:s nivå, eller finare) och
Top80-beslutet (§2: 8,7 % koder / 81,5 % omsättning) tas i B.4b. Klustringsanalysen (D-B2) är ett eget
parallellt spår mot golden reference — berikar, blockerar ej.

> **Var Spår B möter resten:** B.4b producerar modellkontraktet (§6) → matas till samma BCG-modell vi
> redan replikerat (FR-1..7) → validerad output går genom `verify_tool` (FAS V) och output-rimlighetsgrinden
> (FAS F). Detta är vägen från "egen SQL-data" till "färska elasticiteter". Se ROADMAP.

---

*Skapad av Jens Palmö (utvecklare) med AI-rådgivaren, 2026-05-21. Reviderad efter B.2 + strategisk omsvängning.
Omstrukturerad 2026-05-27: D-B4 korrigerad på plats i decision log (ingen §3-vs-§8-motsägelse kvar); inaktuell
"reviderad roadmap" i gamla §8 borttagen (ersatt av ROADMAP.md:s V→T→F→A); FR-7-stängning och fas-koppling
reflekterad.*

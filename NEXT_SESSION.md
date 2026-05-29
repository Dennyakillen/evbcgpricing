# NEXT_SESSION — FAS F: pipelinekörning med växande fönster (cluster-familj först)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på Evidensia
Djursjukvård AB. Följ `KÄRNPRINCIPER.md` (inkl. nya §4.6 dokumentation, §6.4 iterativ sökning),
`MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md`, `MASTER_PYTHON.md` (inkl. §7.2 iterativ sökningsteknik,
L.42-L.43). Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`
(läs riktningsblocket överst). Lärdomar: `LESSONS_BCG.md` (`LB.N`). Insikter: `INSIGHTS_BCG.md` (`IB.N`).
Fasöversikt: `ROADMAP.md` (V→T→F→A). G7-fixen: `FAS_F_G7.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel) i
> `LESSONS_BCG.md`, eller ny insikt i `INSIGHTS_BCG.md`. Befordra till MASTER_* om generell.

> **Sessionsstart §6.4:** Innan något nytt designas eller byggs — sök iterativt i Jens arbetsmiljö
> efter befintliga artefakter som löser frågan. Se MASTER_PYTHON §7.2 för sökmönster.

> **Miljödisciplin:**
> - `export_b4b_for_model.py` körs från `C:\Projekt\Business_Analytics\.venv` (har pyodbc).
> - `verify_tool` körs med `py -3.11` (global, har duckdb/pandas/openpyxl/numpy/yaml).
> - Pipelinen (Pipeline\02. Elasticity\.venv) körs från sin egen venv (har duckdb).
> - Inga installationer av paket — använd befintliga miljöer (LB.26/LB.27).

---

## Aktuellt projekt

- **Repo (BCG):** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Repo (Business_Analytics):** https://github.com/Dennyakillen/Business_Analytics.git — `C:\Projekt\Business_Analytics`
- **BCG-branch:** `fas-f-fresh-data` @ `<SHA efter dagens commits>` — Spår B operationaliserat
- **Business_Analytics main:** `bac4af6` — Fas 10 + BCG inspection utilities committat 2026-05-29

---

## Status vid sessionsstart (2026-05-29)

**Spår B är operationaliserat och validerat.** Vi har bevisat trogen DW-extraktion mot BCG:s frusna
facit på två fönster:

| Mått | Frusen BCG-fönster (2022-07..2025-06) | Växande fönster (2022-07..2026-04) |
|---|---|---|
| Rader | 484,827 (vs facit 485,248 = -0.09%) | 610,039 (+25.8% data) |
| TotalNet | 6.50 mdr (vs facit 6.51 mdr = -0.057%) | 8.27 mdr (+27.2%) |
| ItemCodes | 1,151 (samma) | 1,151 (samma facit-urval) |
| KEY | 4,930 (vs facit 4,949) | 4,930 |
| FTE NULL | 0 | 122,214 (20.03%, veckor 2025-07-07..2026-04-27) |

Snapshot-drift på frusen fönstret = 0.057% på revenue — inom snapshot-drift, inte fel.
`compare_to_0828_facit.py` bekräftade per-kluster-uppdelning: 6 av 7 kluster inom ±0.5%,
två (Clinics 2 +1.19%, Sjukhus Södran -1.41%) lite högre men inte alarmerande.

**Patch som ligger i `export_b4b_for_model.py`:** Env-overridable `BCG_START_DATE` / `BCG_END_DATE`
(G7-mönster), FY-filtret borttaget (silent date-window-risk eliminerad), FTE NULL-rapportering
tillagd (loggrad med antal, procent, vecka-range).

**Växande-fönster-CSV:n ligger på plats i Pipeline\data\.** Säkerhetskopia av frusen-fönster-CSV:n
finns med tidsstämpel.

---

## Mål för denna session: testkörning av pipelinen på växande fönster, cluster-familjen först

Vi vill se hur elasticiteten rör sig på 10 extra månaders data. Inte färdig produktion — testet är
till för att Jens ska få en känsla för effekterna och tolkningarna. Resultatet är *empiriskt* — vi
vet inte vad pipelinen gör med 20% NULL-FTE förrän vi kört.

### Etapp 1: Lokal körning av cluster-familjen (45-90 min)

Cluster-modellen är BCG:s huvudfamilj (3812 product×cluster groups). Den ska köras lokalt först:
mindre data än stage 2 OOM-:ade på, facit-pairs filtrerar till 1151 koder × 4930 KEY × 610k rader.
Min gissning: går lokalt. Om OOM → backa till VM.

**Pipeline-steg (cluster-familjen):**

1. `01_clean.sql` (DuckDB) — läs `0828_..._P_C.csv` → renad parquet
2. `feature_selection` (Python, Ray-parallelliserad OLS) — kombinatorisk feature-val per grupp
3. `model` (Python, OLS-regression per KEY) — slutgiltig elasticitet → `output_summary.xlsx`

**Vad vi tittar efter när det körts:**

- Pipelinen kraschar inte (eller kraschar med läsbart fel som vi kan diagnostisera).
- `output_summary.xlsx` produceras med rätt grain (KEY-nivå, ELASTICITY_Regular_Price_fwbw_max_6).
- Antal KEYs med utdata, antal som droppat pga NULL/insufficient data.
- Förändring i elasticitet vs BCG:s frusen facit — per KEY-jämförelse med verify_model.py.

### Etapp 2: Tolkning av elasticitetsförändringar (om Etapp 1 går igenom)

- Hur många KEYs sign-flippade (positiv på BCG-fönster, negativ på växande, eller tvärtom)?
- Median förändring per kluster.
- Decision-relevant-grupper (IB.2-gate: RSQ≥0.5, p≤0.20, −10<elasticity<0) — hur många finns kvar?
- Top-line-effekt: skulle ändrade elasticiteter flippa ett prisbeslut?

### Etapp 3 (om tid): Bundle-familjen lokalt (125 grupper, snabbare)

Endast om Etapp 1+2 går smidigt. Site-familjen (4673 grupper) sparas till egen session.

---

## Förutsättningar och frågor som måste lösas i sessionen

1. **Vilket steg läser CSV:n först?** `00_read.sql` läser parquet, inte CSV. Måste verifiera om
   det är `00_read.sql` eller `01_clean.sql` som börjar från CSV:n vi just skrev. Kör iterativ
   sökning efter "0828_Sweden_weekly_model_data_P_C" i Pipeline-katalogen.

2. **Pipelinens venv:** vilken Python? Kommandot `Pipeline\02. Elasticity\.venv\Scripts\python.exe`
   är vad export-headern hänvisar till — verifiera att den har Ray, duckdb, statsmodels innan
   stage 2 körs.

3. **FTE-NULL-beteende:** vad gör `feature_selection` med NULL i `Sum_FTE_Interpolated`? Det är en
   empirisk fråga. Hypoteser: (a) droppar rader → effektivt fönster blir BCG:s gamla, (b) accepterar
   NULL → mindre tillförlitliga koefficienter, (c) kraschar med NaN-fel. Sök i pipelinens kod efter
   `Sum_FTE_Interpolated.fillna|.dropna|.notna` innan körning.

---

## Standarder särskilt relevanta nu

- **KÄRNPRINCIPER §6.4 + MASTER_PYTHON §7.2** — iterativ sökning innan design. Sessionen börjar med
  att söka efter befintliga svar på de tre frågorna ovan.
- **LB.24** — validera mot fryst original, aldrig arbetskopia.
- **LB.25** — misstänk corr 1,0 tills källoberoende bekräftat.
- **L.43** — två parallella spår kan skriva filer med samma namn i olika kataloger. Verifiera
  validatorns sökväg före tolkning av PASS/FAIL.
- **L.39** — läs vad koden GÖR, inte vad configen PÅSTÅR (gäller särskilt pipelinens `config.yml`).

---

## FAS T (tech-debt — fortfarande relevant)

- **Miljö i global Python 3.11** — ej reproducerbar (pinnad venv + requirements.txt behövs för FAS A).
- **Relativa sökvägar i `constants.py`** (`.\code\src\config.yml`) — körning platsberoende.
- **Frusna externa beroenden** (FTE-XLSX, facit-pairs, cluster-seed) — tre olika filer, frusna vid
  olika tidpunkter, läses av olika pipeline-steg.
- **Inget run_all-script för pipelinen** — manuell orkestrering, glöm-faktor.
- **Två oberoende output-vägar (Spår A vs Spår B)** med samma filnamn — riskerar tyst förorening
  (L.43).
- **Blob Storage-roll fortfarande blockerad** (Storage Blob Data Contributor, kräver Owner).

---

## Vid sessionsslut

1. Committa på `fas-f-fresh-data` (inte main förrän hela pipelinen är validerad färskt end-to-end).
2. `git status` — rent.
3. Uppdatera denna fil: ny SHA + nästa mål (förmodligen bundle eller site, eller felsökning av
   cluster om den inte gick igenom).
4. Nya lärdomar → `LESSONS_BCG.md`; insikter → `INSIGHTS_BCG.md`.
5. Om elasticitet-förändringar är intressanta — dokumentera observationer i `INSIGHTS_BCG.md` som
   förberedelse till framtida samtal med beslutsfattare.

---

*Skapad 2026-05-29 vid avslut av session där Spår B operationaliserades: export_b4b validerat mot
frusen facit (0.057% drift), växande-fönster-CSV producerad (2022-07..2026-04, +27% data, 20% NULL-FTE).
KÄRNPRINCIPER och MASTER_PYTHON uppdaterade med §4.6 (dokumentation som sök-yta) och §6.4 (iterativ
filsökning), plus L.42-L.43. Nästa: pipelinekörning lokalt på cluster-familjen.*

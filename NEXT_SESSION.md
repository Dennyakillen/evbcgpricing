# NEXT_SESSION — Steg 6-validering (Fall Back Logic, F1–F7) mot BCG:s facit

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på Evidensia
Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md`,
`MASTER_PYTHON.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`
(läs riktningsblocket överst först). Lärdomar: `LESSONS_BCG.md` (`LB.N`). Insikter: `INSIGHTS_BCG.md` (`IB.N`).

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel) i
> `LESSONS_BCG.md`, eller ny insikt i `INSIGHTS_BCG.md`. Befordra till MASTER_* om generell.

> **Miljödisciplin (skärpt 2026-05-26):** Varje kommandoblock SKA etiketteras med miljö + hur den nås.
> **PowerShell** (`PS C:\`, kör `ssh`/`scp`/`az`/lokala script) — kontrollera att prompten visar `PS`,
> inte bara `C:\` (cmd, där `&&` och cmdlets failar). **bash på VM** (`azureuser@bcg-poc-vm`, nås via
> `ssh azureuser@172.18.148.4`). Kolla prompten före varje kommando. Kopiera kommandon från kodblock,
> inte genom att markera i terminalen (drar med prompttext → blandas in i kommandot).

> **Princip inlärd 2026-05-26: "Facit finns en prompt bort."** När en fråga om format, sökväg, kolumner
> eller förväntat resultat uppstår — be om källfilen/koden ur originalmappen istället för att gissa eller
> tvinga fram ett vägval (A/B). Originalet (`BCG_orginal_V2_New`) HAR svaret. Detta upprepar LB.1.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Senaste commit på origin/main:** `6dcbea1` — *Document VM run pass: Cluster/Site/Bundle complete
  (FR-4..6), add LB.17-20, IB.9*
- **Branch:** `main`
- **Originalmapp (facit):** `C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New`
  — OBS: strukturen där är `...\BCG_orginal_V2_New\02. Elasticity\...` (INGET `Pipeline\`-led, till
  skillnad från repot som har `...\BCG\Pipeline\02. Elasticity\...`).
- **Azure-VM:** `bcg-poc-vm`, deallocated. Behövs INTE för steg 6 (pandas/openpyxl-väv, lätt, körs
  LOKALT på Windows — xlwings hör hemma där).

---

## Status vid sessionsstart

**Full replikering är klar t.o.m. FR-6. Alla tre modellfamiljer körda + verifierade + hemtagna +
dokumenterade + pushade (commit `6dcbea1`). Det enda kvarvarande för full replikering är steg 6
(FR-7) — F1–F7-vävningen, validerad mot BCG:s facit.**

**Referensvärden (våra VM-outputs, verifierade 2026-05-26, `IB.9`):**

| Familj | Grupper | Median elast. | Neg-andel | p<0,05 | Hemtagen till |
|---|---:|---:|---:|---:|---|
| Cluster | 3812 | −0,138 | 76,5% | 18,0% | `2. ...\output\azure_run_model\output_summary.xlsx` |
| Site | 4673 | −0,054 | 62,4% | 9,3% | `3. ...\output\azure_run_model\output_summary.xlsx` |
| Bundle | 125 | −0,211 | 85,6% | 22,4% | `5. ...\output\azure_run_model\output_summary.xlsx` |

Cluster 18,0% ≈ BCG:s frusna 17,8% (`IB.1`) — trogen replikering bekräftad.

---

## Mål för denna session

### Primärt: Validera steg 6 (F1–F7-väv) mot BCG:s facit

**Strategi (ren logik-grind, LB.2 — INGET A/B-val):** Kör `Fall_Back_Logic.py` på **BCG:s egna
input_data-filer** och matcha vår slutoutput (`dv8`) mot BCG:s facit-slutfil, per `ProductKey` på
`final_elasticity` + `elasticity_level`. Bevisar att vi äger F1–F7-vävlogiken end-to-end. (Att köra
steg 6 på VÅRA färska VM-outputs är en SEPARAT, senare integrationsfråga — inte det som stänger FR-7.)

**FACIT (i originalets `02. Elasticity\6. Fall Back Logic\output_data\`):**
- `Final_Fallback_Data_20250930_091648.xlsx` (7,9 MB) — **slutfilen vi validerar mot** (= `dv8`).
- `Complete_Product_Data_Blended.xlsx` (3,9 MB) — mellanfil som main genererar (kan korsvalideras).
- `Product_site_check_20250930_091648.csv` (6 KB) — site-diagnostik.

**BCG:s INPUT (i originalets `02. Elasticity\6. Fall Back Logic\input_data\`):**
- `Complete_Product_Data.xlsx` (7 MB) — produkt×klinik-bas (från Alteryx, `df_all_product_path`)
- `output_summary_site.xlsx` (410 KB) — site-modellens output
- `output_summary_bundle.xlsx` (27 KB) — bundle-output
- `final_model_cluster_granularity_Ivce.xlsx` (17 KB) — steg 5:s cluster-blended-output
- `0901_Sweden_code_level_elasticity_regular_price_blended Final Model.xlsx` (28 MB) — blended-modell
- `0808_Sweden_Clinic_Cluster_Mapping.xlsx` (27 KB) — klustermappning

**Leveranser:**
1. Läs KLART de tre olästa vävfunktionerna i `Fall_Back_Logic.py` (i repots `6. Fall Back Logic\`):
   `aggregate_sales_by_granularity` (rad 116–221), `read_blended_model_data` (222),
   `significant_cluster_summary`/`significant_bundle_summary` (387–472, bygger F4–F7-nivåerna).
   `creating_one_df` (473–551) är REDAN läst — F1–F7 via `combine_first`-prioritet, `elasticity_level`
   via `np.select`. (Se "Vad steg 6 gör" nedan.)
2. Lös path-frågan (se KÄRNPROBLEM nedan) — peka `Constant.py` mot BCG:s input_data, eller kör från en
   plats där de relativa sökvägarna löses rätt.
3. Hantera `import xlwings as xw` (rad 10). Lokalt på Windows med Excel fungerar det troligen; verifiera
   att det är installerat i venv:en, annars `python -m pip install xlwings` (lokalt OK — Windows har
   Excel). Main använder `to_excel(engine="openpyxl")`, så xlwings kan vara död import — men importen
   körs vid filstart, så den måste lösas.
4. Bygg `verify_fallback.py` (som `verify_output.py`): jämför vår `dv8` mot facit per `ProductKey` —
   `final_elasticity` (numerisk diff/korr) + `elasticity_level` (F1–F7-fördelning matchar?).
5. Kör + validera. PASS = elasticity_level-fördelning matchar facit, final_elasticity korr ~1,0.

**Datakälla:** BCG:s `input_data\` (facit-input). Lokalt, Windows. Ingen VM.

---

## KÄRNPROBLEM att lösa FÖRST (path-mismatch)

`Constant.py` läser site/bundle/cluster från sökvägar som INTE matchar var filerna ligger:
- `prod_site_level_path = "3. Product Site Level Models\output\model\output_summary.xlsx"`
- `bundle_cluster_level_path = "5. Bundle Clinic Models\output\model\output_summary.xlsx"`
- `blended_output_path = "2. ...\output\final_model_cluster_granularity.xlsx"`
- `blended_model_path = "2. ...\output\output_summary_ready.xlsx"`

…lösta via `base_dir = Path(__file__).resolve().parent.parent` (= `02. Elasticity`-roten).
**MEN** BCG:s faktiska input ligger i `6. Fall Back Logic\input_data\` (verifierat 2026-05-26) — INTE
i modellmapparnas `output\model\`. Så antingen (a) kördes steg 6 historiskt med en annan path-config,
eller (b) `Constant.py` i repot är en annan version. **Beslut nästa pass:** enklast att peka
`Constant.py`:s fyra modell-sökvägar till `input_data\`-filerna (kopiera BCG:s input dit `Constant`
läser, ELLER ändra `Constant`-sökvägarna). Verifiera mot facit oavsett väg. Det här är inte en
logikfråga — bara att få filerna dit koden letar. (Jfr LB.19: path-mismatch är förväntat i orörd kod.)

---

## Vad steg 6 gör (redan kartlagt 2026-05-26, för snabb återstart)

`creating_one_df` väver ihop alla nivåer och väljer `final_elasticity` via `combine_first`-PRIORITET
(första tillgängliga i ordningen vinner):
1. **F1 site_level** — om `significant_SiteCode==1`
2. **F2 bundle_level**
3. **F3 cluster_level** — om `significant_Clusters==1`
4. **F4 bundle_across_clusters** → 5. **F5 product_across_clusters** → 6. **F6 service_within_cluster**
   → 7. **F7 service_across_clusters**

`elasticity_level` taggar vinnande nivå (`np.select` över samma villkor). Signifikans-def (rad 377):
`significant_<level> = (round(RSQ,2)>=0.5) & (round(PVALUE_PRICE,2)<=0.20)` — samma som steg 5 (`IB.2`).
Site-skärpning (rad 658): `significant_SiteCode` nollställs om `SigSites_Sum < 10` (kräver ≥10 sig.
sites per produkt). Slutfil `dv8`: `ProductKey, ProductDescription, service, Clusters, SiteCode,
TotalNet, year ending 2025 revenue, PVALUE_PRICE, RSQ, final_elasticity, elasticity_level,
Product Granularity, site Granularity, Weighted Elasticity`.

**Fortfarande oläst (läs först nästa pass):** hur F2/F4–F7 (de viktade `wt_elas_*`-nivåerna) faktiskt
BERÄKNAS — det sker i `significant_cluster_summary` / `significant_bundle_summary` /
`aggregate_sales_by_granularity` (rad 116–472). `creating_one_df` konsumerar bara deras resultat.

---

## Steg (ett i taget, verifiera mellan steg)

### Steg 0 — Pre-flight (PowerShell, Windows)
```powershell
cd "C:\Projekt\BCG"
```
```powershell
git log --oneline -5
git status
```
Förväntat: senaste commit `6dcbea1`, working tree clean.

### Steg 1 — Läs klart vävfunktionerna (LB.1, FÖRE körning)
Läs `Fall_Back_Logic.py` rad 116–472 (`aggregate_sales_by_granularity`, `read_blended_model_data`,
`significant_cluster_summary`, `significant_bundle_summary`, `reading_site_level_data`,
`reading_bundle_cluster_level_data`). Förstå hur F2/F4–F7 viktas innan körning.

### Steg 2 — Lös path + xlwings (KÄRNPROBLEM ovan)
Peka `Constant.py`-sökvägar mot BCG:s `input_data\`-filer (eller kopiera dit koden läser). Verifiera
xlwings-import (installera lokalt vid behov).

### Steg 3 — Kör Fall_Back_Logic.py på BCG:s input
Lokalt, venv aktiv (`python -m`, AppLocker-rent). Tee + grep strukturella rader (LB.14).
Producerar `dv8` → `Final_Fallback_Data.xlsx` + tidsstämplad kopia i `output_data\`.

### Steg 4 — Validera mot facit (verify_fallback.py)
Jämför vår `dv8` mot `Final_Fallback_Data_20250930_091648.xlsx` per `ProductKey`:
- `elasticity_level`-fördelning (F1–F7 antal) matchar facit?
- `final_elasticity` korr/diff mot facit ~1,0?
- Radantal / ProductKey-population matchar?
PASS-kriterium: fördelning + korr matchar (bit-för-bit-anda som steg 5, 43/43).

---

## Standarder särskilt relevanta nu

- **LB.1 / "facit en prompt bort"** — be om originalfiler ur `BCG_orginal_V2_New` när format/förväntat
  resultat är oklart; gissa aldrig, tvinga inte fram A/B.
- **LB.2** — kör vår kod på KONSULTENS input, matcha facit. Billig logik-grind, ingen VM behövs.
- **LB.4** — `creating_one_df` (konsumenten) definierar vad de tre summary-funktionerna måste leverera.
- **LB.19** — path-mismatch i `Constant.py` är förväntad orörd-kod-rest; fixa paths, inte logik.
- **LB.20** — xlwings: på Linux dödligt, på Windows OK (Excel finns). Steg 6 körs lokalt just därför.
- **LB.14** — tee + grep strukturella rader.

---

## Efter detta pass (förberedelse, ej denna session)

Med steg 6 validerat är HELA replikeringen (FR-1..7) stängd. Då återstår **färsk-data-fasen** mot
affärsmålet (`IB.6`): output-rimlighetsgrind + G7-datumparametrisering (hårdkodat `START_DATE
2022-07-01 / END_DATE 2025-06-30` filtrerar annars bort färsk 2026-data tyst) + FTE Väg 2 (Quinyx).
Parallellt: DW-native bygget (Spår B, `TECHNICAL_PREREQUISITES.md`). Samt: integration av VÅRA
VM-outputs genom steg 6 (separat från facit-valideringen).

---

## Vid sessionsslut

1. Committa ev. ändrade verktyg/dokumentation (`verify_fallback.py`, ev. path-fixad `Constant.py`) +
   pusha. Excel-output går INTE in (`.gitignore`).
2. `git status` — ska vara rent.
3. Uppdatera denna fil: ny SHA + nästa mål (färsk-data-fasen / DW-bygget).
4. Nya lärdomar → `LESSONS_BCG.md`; nya insikter → `INSIGHTS_BCG.md`; befordra till MASTER_* om generella.
5. Uppdatera playbookens riktningsblock (FR-7 → ✅) och README:s roadmap.

---

*Skapad 2026-05-26 vid VM-passets slut (commit 6dcbea1). Riktad mot steg 6-validering mot facit
(`Final_Fallback_Data_20250930_091648.xlsx`). FR-4..6 stängda. Steg 6-koden kartlagd: `creating_one_df`
+ F1–F7-prioritet läst; tre summary-/aggregeringsfunktioner (rad 116–472) ska läsas klart först. Facit +
BCG:s input lokaliserade i originalets `input_data\`/`output_data\`. Path-mismatch i `Constant.py` är
det praktiska som ska lösas — inte logik.*

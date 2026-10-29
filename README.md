# evbcgpricing — Evidensia DJursjukvård AB BCG Pricing Replication

**Developer:** Jens Palmö (Senior Business Analyst).
**Purpose:** Replicate, validate, migrate, and operationalize BCG's price elasticity pipeline so
Evidensia owns the analytical model internally — independent of BCG's hardware, environment, and
delivery frequency.

---

## Kom igång för dagen

Venv:n och koden ligger i repo-roten. Aktivera och stå kvar i roten.

```powershell
cd "C:\Projekt\BCG"
.\.venv\Scripts\Activate.ps1
```

**PIM först.** Gå till Azure-portalen → PIM → *Mina roller* → *Azure-resurser* och aktivera **Deltagare** på
resursgruppen **`ev-openai-swce-rg-test`**. Vänta tills rollen står under *Aktiva tilldelningar*.
Rollen räcker för både Blob-nyckeln och VM:en. Prod-gruppen och Ägare-rollen behövs inte. Aktiveringen har en
tidsgräns, så gör om den när den löpt ut.

Logga sedan in mot Azure (gör det **efter** PIM). Inloggningen håller i 4 timmar:

```powershell
az login --scope https://management.core.windows.net//.default    # Azure: Blob-nyckeln och VM:en
az login --scope https://database.windows.net/.default            # datalagret (DW): månadskörningens FÖRE-steg
az account set --subscription "ev-lz3-ai (SE)"                    # alltid; andra projekt (t.ex. HUB) byter den
```

Testa att Blob nås, innan appen startas:

```powershell
az storage account keys list --account-name evbcgpricinginput --resource-group ev-openai-swce-rg-test -o none; if ($LASTEXITCODE -eq 0) { "OK - Blob nås" }
```

Inget `OK` betyder att felmeddelandet säger varför: `AuthorizationFailed` betyder att PIM inte är aktiv eller att fel subscription är vald.

Kontrollera setup. Ska ge 0 `[FEL]` (`[OBS]` är information):

```powershell
python verify_setup.py
```

Starta dashboarden:

```powershell
python orchestration\webapp\app.py
```

Öppna http://127.0.0.1:5000. Avsluta med `Ctrl+C`. Den visar bara data, den ändrar ingenting.
Molnversionen (`evbcg-dashboard`) är avstängd tills IT satt upp inloggningsskyddet. Starta den inte; läget står i `STATE.md`.

Stoppas `Activate.ps1` av policyn: skriv `.\.venv\Scripts\python.exe` i stället för `python` på raderna ovan.
Första gången på en ny dator: se *Ny dator — en gång* längre ner.

---

## Månadskörningen (när en ny månad stängt)

Kör en i taget. Tar flera timmar. Kräver VPN. Venv:n ska vara aktiv och du ska vara inloggad (se ovan). `<END>` är sista dagen i
senast stängda månad, t.ex. `2026-09-30`.

```powershell
python orchestration\runners\run_data.py --end <END>                # 1. FÖRE: DW -> parquet -> Blob
python orchestration\runners\run_site_model.py --keep-vm            # 2. MOTOR på VM:en, en familj i taget
python orchestration\runners\run_cluster_model.py --keep-vm
python orchestration\runners\run_bundle_model.py                    #    sista familjen stänger VM:en
python orchestration\runners\run_after.py --date-folder <YYYY-MM-DD> # 3. EFTER: steg 6 + R12 -> Blob
python verify_tool\probes\all_chain_validator.py                    # 4. Validera kedjan: FAIL=0
```

Sedan validering, Model Feed och inklistring i prismodell-Excelen: `DRIFT.md` §3.2–3.4. Varje runner tar `--dry-run`
om du vill se planen först. Tappar du anslutningen: `--attach` på samma runner (`DRIFT.md` §2.5).

---

## Avsluta dagen

Bara om du kört månadskörningen: kontrollera att VM:en är avstängd. Den kostar ~9 kr/h och stänger inte av sig själv.

```powershell
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[1].displayStatus" -o tsv
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm   # bara om svaret var "VM running"
```

`deallocate`, inte `stop`, eftersom `stop` låter debiteringen fortsätta.

**Felsökning:**
- `Could not authenticate to Blob` eller tomt efter några timmar: aktivera PIM, kör `az login` och `az account set`
  igen och kör Blob-testet. Starta sedan om appen med `Ctrl+C` och samma kommando igen.
- Blob-testet ger OK men appen klagar fortfarande: kör `$env:PRICINGMODEL_AUTH; $env:PRICINGMODEL_KEY.Length`. Om en
  gammal nyckel ligger kvar som miljövariabel (från autostart-uppsättningen i `DEPLOY_DASHBOARD.md` A) gäller den
  före az. Ta bort den: `Remove-Item Env:PRICINGMODEL_KEY`.
- `AuthorizationFailed`: aktivera PIM, sedan `az account set --subscription "ev-lz3-ai (SE)"`.
- `ModuleNotFoundError`: kör `py -3.11 install.py`.
- Timeout mot VM:en: anslut VPN.
- Övrigt: kör `python verify_setup.py` och läs raderna märkta `[FEL]`.

---


## Var dokumentationen bor

| Innehåll | Fil |
|---|---|
| Start-här: dagen, ny dator, var datan ligger (denna fil) | `README.md` |
| Ingångskarta: "vill du… → läs" | `START_HERE.md` |
| Kort översikt i tre bilder: data in → motor → resultat | `FUNKTIONSKARTA.md` |
| Samma flöde utförligt, utan kod | `SYSTEMGUIDE.md` |
| Körhandbok: månadskörning, validering, Model Feed | `DRIFT.md` |
| Nuläge: resurser, VM, öppna IT-ärenden (färskvara) | `STATE.md` |
| Nästa session: mål, kö, pre-flight | `NEXT_SESSION.md` |
| Beviset för replikeringen och kontrollen av färska resultat | `REPLIKERING_OCH_VALIDERING.md` |
| Vad som medvetet är fruset (2025-värden) | `docs/governance/LOCKED_ASSUMPTIONS.md` |
| Faser, planerat och uppskjutet | `docs/governance/ROADMAP.md`, `docs/governance/FUTURE_DEVELOPMENT.md` |
| Lärdomar (LB) och analytiska insikter (IB) | `docs/knowledge/LESSONS_BCG.md`, `docs/knowledge/INSIGHTS_BCG.md` |
| Var datan ligger, Blob-strukturen | `docs/ops/DATA_PLACERING.md`, `BLOB_MALSTRUKTUR.md` |
| Känslighet och BCG-originalets referensfiler | `docs/ops/KANSLIGHETSREGISTER.md`, `docs/BCG_ORIGINAL_REFERENSER.md` |
| Publicering av dashboarden (lokalt / Azure) | `DEPLOY_DASHBOARD.md` |
| Överlämning: det som inte följer med utvecklarens dator | `docs/ops/OFFBOARDING_KRITISKT.md` |
| Motorn (runners, statuskontrakt, webapp) | `orchestration/README.md` |

Fördelningen mellan filerna:
- README: hur man kommer igång.
- DRIFT: hur man gör.
- LESSONS: varför koden ser ut som den gör.
- STATE: vad som är sant nu.

Ny kunskap går till rätt fil, inte hit.

---

## What this project is (short in english)

BCG built a Python-based price elasticity pipeline using OLS regression per product group,
Ray-parallelized, with combinatorial feature selection. The pipeline produces elasticity KPIs that
feed BCG's Excel pricing model. The authoritative source is the folder `BCG_orginal_V2_New` delivered
by BCG consultants in 2025-07.

This repo (`evbcgpricing`) contains:

1. **Validated replication of BCG's pipeline** — proves on frozen data that we reproduce BCG's
   elasticity numbers bit-for-bit (FAS V complete, see `verify_tool/`).
2. **Fresh-data infrastructure** — the parametrizations and validators needed to run the model on
   live data, not just BCG's 2025-07 snapshot (FAS F **complete** — see `DRIFT.md`).
3. **Lessons + insights logbook** — accumulated technical learnings (`LESSONS_BCG.md`) and analytical
   insights (`INSIGHTS_BCG.md`) so this stays operable across sessions and across people.

A second repo (`Business_Analytics`) holds the DW-native extraction layer that feeds the pipeline
with current data:

- `export_b4b_for_model.py` — produces `0828_..._P_C.csv` directly from DW (replaces BCG's frozen
  parquet for fresh-data runs).
- `compare_to_0828_facit.py` — validates the export against BCG's frozen reference.
- `validate_dw_codelevel.py` — confirms source equivalence per ItemCode (B.4a).
- `b4b_dw_weekly_elasticity.sql` — design document for a DW-native view (B.4b, not yet promoted).

> **2026-10-20:** DW-steget ligger nu i detta repo (`tools/dw/`, kopior av Business_Analytics-originalen) och BCG-facit ur
> `bcg_inputs` i `verify_tool/facit/` — Business_Analytics behövs inte för att köra BCG. Listan ovan är historik (PoC-2).

---

## Current state (2026-06-25)

| Phase | Status |
|---|---|
| FAS V — Validate that we reproduce BCG | **DONE.** verify_tool proves FR-1 through FR-7. |
| FAS T — Tech debt to IT (reproducible env, pinned venv) | Open; not blocking experimental runs. |
| FAS F — Fresh-data prerequisites | **DONE.** All 3 model families run on growing data; Step 6 (fallback weave) run and validated; model can be fed via `build_r12_for_model.py`. Bundle parked on evidence (FD.11); 3 inputs intentionally frozen (LF.9). |
| FAS A — Azure automation | **In progress.** Five runners cover the full chain in three parts (FORE/MOTOR/EFTER): `run_data.py` (local fuel: DW→parquet→Blob), three family model runners (cluster/site/bundle) on the Azure VM auto-validating against frozen facit + uploading to Blob, and `run_after.py` (local Step 5/6/7 + push). A read-only Flask status dashboard (`orchestration/webapp/`) renders per-phase health. **Leverans 2 (2026-06-25):** `verify_tool/probes/all_chain_validator.py` validates the whole chain statically (runs on a fresh clone — no VM/azure/DW), derived from `run_status.default_pipeline` (FLOW out of sync with the contract = FAIL by design), doubling as a replication contract + a standalone flow map (AI-session context). It ran FAIL=0 and caught a real defect (cluster `EXPECTED_KEYS` was the step-5 blend count, wrong layer → set to None) plus the LB.79 automl-dir gap (now `mkdir -p` in `preflight_remote`, all three runners). Operational runbook: `DRIFT.md` §2.5. Remaining before full autonomy: account consolidation (FD.35), the read-side of purpose B (next family reads prior Blob output), sequencer, Blob data role (ABAC-blocked, FAS T). Local Excel steps (5/6/r12) stay local by necessity (xlwings/COM, LB.44). See `FUTURE_DEVELOPMENT.md` Phase Z + `NEXT_SESSION.md`. |

**Fresh-data result (2026-06-11):** the model now runs end-to-end on Evidensia's own growing data
through 2026-04. Step 6 produced 108,979 rows / 15,128 products (100% negative, 100% in band);
revenue-weighted core elasticity moved from BCG's 2025 baseline −0.532 to −0.512 — materially stable.
Full evidence in `REPLIKERING_OCH_VALIDERING.md`; operational runbook in `DRIFT.md`.

**Last validated state:** `export_b4b_for_model.py` produces the exact same aggregate as BCG's frozen
facit (0.057% revenue drift, within snapshot expectations) when run against the frozen window
(2022-07-01..2025-06-28). Run against a growing window (2022-07-01..2026-04-30, +10 months data) it
produces a CSV with 27% more revenue and 20% NULL-FTE in the new weeks — expected, now run through the
full pipeline (FAS F done).

---

## Ny dator — en gång (2026-10)

**Förutsättningar** (beställs av IT, se `docs/ops/OFFBOARDING_KRITISKT.md`): Windows 10/11 · Python 3.11 med `py`-startaren ·
Git · Azure CLI · Excel (steg 5/6 via xlwings) · ODBC Driver 17 for SQL Server (bara REGEN) · en roll på lagringskontot
`evbcgpricinginput` som får läsa kontonyckeln (PIM) · för REGEN: DW-läsning (AAD) + VPN · för MOTOR: åtkomst till VM:en.

```powershell
# 1. Klona till C:\Projekt\BCG (URL: Clone-knappen i Azure DevOps-repot)
git clone <URL> C:\Projekt\BCG
cd C:\Projekt\BCG
# 2. Miljön: .venv, pinnade beroenden (requirements-local.txt), .pth, körmappar, tools\dw\.env ur mallen
py -3.11 install.py
# 3. Datan: facit + handgjord indata ur Azure Blob (~2 GB, sha256-verifierat). Torrkörning först, sedan --kor.
az login --scope https://management.core.windows.net//.default
.\.venv\Scripts\python.exe tools\spegel\spegel_fran_blob.py
.\.venv\Scripts\python.exe tools\spegel\spegel_fran_blob.py --kor
# 4. Kontroll: ska ge 0 [FEL]
.\.venv\Scripts\python.exe verify_setup.py
```

*AVSIKT:* klona till `C:\Projekt\BCG` — flera verktyg och runners har repo-roten hårdkodad (känd skuld, FD.39). REGEN (DW → parquet)
kräver dessutom `tools\dw\.env` ifylld med värden från DW-förvaltaren; utan den körs kedjan från PREP på bränslet i Blob.
MOTOR (stegen på VM:en) kräver VPN och en egen SSH-nyckel som IT lagt in på VM:en — koden kör `ssh` utan lösenordsfråga
(`BatchMode=yes`); se `docs/ops/OFFBOARDING_KRITISKT.md` rad 6.
Daglig drift: `DRIFT.md`. Dagsrutinen: *Kom igång för dagen* överst i denna fil.

## Var datan ligger

Git bär metoden; Azure Blob (`evbcgpricinginput`) bär datan, i tre lager:
**kanoniskt** (`input/`, `output/<familj>/<fönster>/`, `pipeline/00_frozen_facit/`, `receipts/`, `runstatus/` — det kedjan kör på,
se `BLOB_MALSTRUKTUR.md`), **facit ur BCG-originalet** (`pipeline/00_frozen_facit/bcg_original/`, byte-exakt) och **spegeln**
(`spegel/bcg_2026-10-20/` — ögonblicksbild av utvecklarens dator 2026-10-20, inklusive den handgjorda indata som inget skript skapar).

- Vad varje fil används till och var i kedjan den sitter: **`docs/ops/DATA_PLACERING.md`**
- Vilka filer ur BCG-originalet validatorerna jämför mot: **`docs/BCG_ORIGINAL_REFERENSER.md`**
- Vad som kan vara känsligt (IT-säkerhet, dataskydd), var det ligger och vem som beslutar: **`docs/ops/KANSLIGHETSREGISTER.md`**
- Medvetet utanför git och Blob: `tools/dw/.env` (värden från IT) och BCG-originalet i övrigt

## Vad valideringen visar i dag (2026-10-21)

Validatorerna läser facit ur `BCG_FACIT_DIR` (standard `verify_tool\facit`, fylls av steg 3 ovan). Kedjans utdata kommer från det
**växande** fönstret, så `verify_tool\proof_chain\run_all.py` mäter **drift mot BCG 2025** — inte replikering:

| FR | Steg | 2026-10-21 |
|---|---|---|
| FR-1 | Dataprep | REVIEW (växande modell-CSV mot BCG:s fönster) |
| FR-4 / 5 / 6 | Kluster / site / bundle | rank-korr 0,69 / 0,65 / 0,89 |
| FR-3 | Steg 5 (43 representanter) | 31/43 lika |
| FR-7 | Steg 6 (F1–F7) | korr 0,92, 90,7 % samma fallback-nivå |

Replikeringsbeviset bit-för-bit (FAS V: kluster 3812/3812, korr 1,0) är kvittot `verify_tool/receipts/verify_receipt_2026-05-28.xlsx`
(länkas från dashboarden). Att upprepa det kräver en körning på det frysta fönstret.

---

## Quick start

> **Historik (2026-10-21):** avsnitten nedan beskriver utvecklarmiljön till och med 2026-07 (Business_Analytics-venv,
> `export_b4b_for_model.py`, tre venv). För en ny dator gäller *Ny dator — en gång* ovan och `DRIFT.md`. Behålls som spår.

### Prerequisites

- Python 3.11 with project-specific venvs:
  - `C:\Projekt\Business_Analytics\.venv` — has pyodbc; runs DW extraction
  - `C:\Projekt\BCG\Pipeline\02. Elasticity\.venv` — has duckdb/Ray; runs the pipeline
  - Global Python 3.11 — has duckdb/pandas/openpyxl/numpy; runs verify_tool
- Azure CLI logged in (`az login --scope https://database.windows.net/.default`)
- Access to Evidensia DW (`se-az-we-bi-dw-sqldb-01.database.windows.net`)

### Verify the replication is still trustworthy

```powershell
cd "C:\Projekt\BCG\verify_tool"
py -3.11 verify_infra.py        # environment check
py -3.11 run_all.py             # full chain: data prep -> model -> blend -> fallback
```

`run_all.py` runs the five validators in milestone order and prints a consolidated table.
`run_all.py --excel` writes a dated receipt to `receipts\`.

> **2026-10-21:** skripten ligger i `verify_tool\proof_chain\` — kör `py -3.11 verify_tool\proof_chain\run_all.py` från repo-roten.
> Vad de visar på dagens data: *Vad valideringen visar i dag* ovan.

### Run a fresh-data extraction (growing window to latest closed month)

```powershell
cd "C:\Projekt\Business_Analytics"
.\.venv\Scripts\Activate.ps1
az login --scope https://database.windows.net/.default

# Backup current CSV first
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"
$csv = "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv"
if (Test-Path $csv) { Copy-Item $csv "$csv.before-run-$ts.bak" }

# Override date window to latest closed month
$env:BCG_END_DATE = "2026-04-30"
python export_b4b_for_model.py

# Validate against frozen facit (will show drift, that's the point)
python compare_to_0828_facit.py
```

To return to BCG's frozen window, unset the env-var:
```powershell
Remove-Item Env:BCG_END_DATE
```

### Run the model on fresh data and feed the pricing workbook

Full operational runbook in **`DRIFT.md`**. In short:

```powershell
cd "C:\Projekt\BCG"
py -3.11 verify_tool\run\run_step6.py                      # 1. fallback weave (F1–F7)
py -3.11 verify_tool\run\build_r12_for_model.py `          # 2. R12 volume + elasticity per code×site
  --tx "Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output\Sweden_weekly_model_data_site_level.csv"
```

Step 1 produces the fresh blended elasticities; step 2 produces `output_model_feed\Model_Feed_<date>.xlsx`
— three sheets (FACT_CodeClinic, DIM_Code, DIM_Site) named exactly like the BCG workbook's blue input
tabs, hardcoded values ready to copy-paste. Enter a price assumption in the workbook and it computes the
revenue effect.

---

## Architecture

```
                                    +----------------------------+
                                    | C:\Projekt\Business_Analytics |
                                    +----------------------------+
                                              |
                                              v
                                  export_b4b_for_model.py
                                  (DW + cluster seed + FTE)
                                              |
                                              v
                              0828_Sweden_weekly_model_data_P_C.csv
                                              |
                                              v
                                  +-------------------------+
                                  | C:\Projekt\BCG\Pipeline |
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

**Date window control (G7):** `export_b4b_for_model.py` reads `BCG_START_DATE` / `BCG_END_DATE` env-
vars with defaults matching BCG's frozen window. Pipeline date filters also G7-parametrized (see
`FAS_F_G7.md`).

---

## Key documents in this repo

> Kort översikt för icke-tekniska läsare: *Var dokumentationen bor* överst i denna fil.

| File | Purpose |
|---|---|
| `DRIFT.md` | **Operational runbook** — how to run & maintain the model on fresh data, end-to-end |
| `REPLIKERING_OCH_VALIDERING.md` | **Full evidence record** — how replication was proven bit-for-bit and how fresh output is validated |
| `BCG_PRICING_PLAYBOOK.md` | Operational playbook — how to run the pipeline end-to-end |
| `LESSONS_BCG.md` | Technical lessons (LB.N) — what we learned the hard way |
| `INSIGHTS_BCG.md` | Analytical insights (IB.N) — observations about the model and data |
| `ROADMAP.md` | Phase overview: V → T → F → A (F done, A next) |
| `FUTURE_DEVELOPMENT.md` | Future tracks (FD.N), incl. Phase Z productionization (the next session's plan lives here now) |
| `verify_tool/probes/all_chain_validator.py` | **Allkedje-sond (Leverans 2)** - end-to-end statisk validering av hela kedjan (FORE->MOTOR->EFTER), harledd ur run_status.default_pipeline. Replikeringskontrakt (kor pa en frisk klon) + fristaende flodeskarta for AI-kontext. Skriver workspace/flow_map + Consolas Excel-receipt. |
| `orchestration/` | **Phase Z orchestrator** — three family runners (`runners/run_cluster_model.py`, `run_site_model.py`, `run_bundle_model.py`) run model steps 1-4 on the Azure VM, each auto-validating against frozen facit and uploading all output to Blob. `shared/run_status.py` (status contract, all phases incl. bundle), `infrastructure/azure_vm.py` + `blob.py`, `webapp/` (read-only status dashboard). See `orchestration/README.md`. |
| `FAS_F_G7.md` | Date window parametrization design |
| `UBUNTU_AZURE_VM.md` | Linux/bash specifics for Azure VM operations |
| `verify_tool/README.md` | Verification suite documentation |
| `LOCKED_ASSUMPTIONS.md` | Låsta förutsättningar (LF.N) — proaktiva designbeslut som inte revideras impulsivt, för stabil affärs-referensram |
| `docs/ops/DATA_PLACERING.md` | **Var datan ligger** (git/Blob), roll i kedjan, återställning |
| `docs/ops/OFFBOARDING_KRITISKT.md` | Det som inte följer med utvecklarens dator och konton, och vad som ersätter det |
| `docs/BCG_ORIGINAL_REFERENSER.md` | Filerna ur BCG-originalet som validatorerna jämför mot (namn, användning, sha256) |
| `docs/ops/KANSLIGHETSREGISTER.md` | Vad som kan vara känsligt, var det ligger och vem som beslutar — underlag för IT, inte juridisk bedömning |
| `install.py` · `verify_setup.py` · `tools/spegel/spegel_fran_blob.py` | Ny dator: miljö, kontroll, data ur Blob |

---


## Contact and ownership

**Project owner:** Jens Palmö 

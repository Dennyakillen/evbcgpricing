# evbcgpricing — Evidensia DJursjukvård AB BCG Pricing Replication

**Developer:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB), with AI advisor.
**Purpose:** Replicate, validate, migrate, and operationalize BCG's price elasticity pipeline so
Evidensia owns the analytical model internally — independent of BCG's hardware, environment, and
delivery frequency.

---

## What this project is

BCG built a Python-based price elasticity pipeline using OLS regression per product group,
Ray-parallelized, with combinatorial feature selection. The pipeline produces elasticity KPIs that
feed BCG's Excel pricing model. The authoritative source is the folder `BCG_orginal_V2_New` delivered
by BCG consultants in 2025-07.

This repo (`evbcgpricing`) contains:

1. **Validated replication of BCG's pipeline** — proves on frozen data that we reproduce BCG's
   elasticity numbers bit-for-bit (FAS V complete, see `verify_tool/`).
2. **Fresh-data infrastructure** — the parametrizations and validators needed to run the model on
   live data, not just BCG's 2025-07 snapshot (FAS F in progress).
3. **Lessons + insights logbook** — accumulated technical learnings (`LESSONS_BCG.md`) and analytical
   insights (`INSIGHTS_BCG.md`) so this stays operable across sessions and across people.

A second repo (`Business_Analytics`) holds the DW-native extraction layer that feeds the pipeline
with current data:

- `export_b4b_for_model.py` — produces `0828_..._P_C.csv` directly from DW (replaces BCG's frozen
  parquet for fresh-data runs).
- `compare_to_0828_facit.py` — validates the export against BCG's frozen reference.
- `validate_dw_codelevel.py` — confirms source equivalence per ItemCode (B.4a).
- `b4b_dw_weekly_elasticity.sql` — design document for a DW-native view (B.4b, not yet promoted).

---

## Current state (2026-05-29)

| Phase | Status |
|---|---|
| FAS V — Validate that we reproduce BCG | **DONE.** verify_tool proves FR-1 through FR-7. |
| FAS T — Tech debt to IT (reproducible env, pinned venv) | Open; not blocking experimental runs. |
| FAS F — Fresh-data prerequisites | **G7 done** (date window parametrized). DW extraction validated. Pipeline run on growing window pending. |
| FAS A — Azure automation | Future. Requires Blob Storage role (currently blocked by Owner permission). |

**Last validated state:** `export_b4b_for_model.py` produces the exact same aggregate as BCG's frozen
facit (0.057% revenue drift, within snapshot expectations) when run against the frozen window
(2022-07-01..2025-06-28). Run against a growing window (2022-07-01..2026-04-30, +10 months data) it
produces a CSV with 27% more revenue and 20% NULL-FTE in the new weeks — expected, awaiting pipeline
test.

---

## Quick start

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

| File | Purpose |
|---|---|
| `NEXT_SESSION.md` | Where the project is right now and what the next session should do |
| `BCG_PRICING_PLAYBOOK.md` | Operational playbook — how to run the pipeline end-to-end |
| `LESSONS_BCG.md` | Technical lessons (LB.N) — what we learned the hard way |
| `INSIGHTS_BCG.md` | Analytical insights (IB.N) — observations about the model and data |
| `ROADMAP.md` | Phase overview: V → T → F → A |
| `FAS_F_G7.md` | Date window parametrization design |
| `UBUNTU_AZURE_VM.md` | Linux/bash specifics for Azure VM operations |
| `verify_tool/README.md` | Verification suite documentation |

External standards governing this project:
- `KÄRNPRINCIPER.md` — universal principles (search-before-build, documentation-as-search-surface)
- `MASTER_PYTHON.md` — Python environment, lessons L.1–L.43
- `MASTER_SQL.md` — DW schema, Manual schema, SQL design principles

---

## Working principles (specific to this project)

1. **Validate against frozen original, never working copy** (LB.24). The OneDrive
   `BCG_orginal_V2_New` is the source of truth for facit; the `Pipeline\...\data` copies are
   overwritten by export runs and are not facit.

2. **Distrust corr 1.0 until source independence is confirmed** (LB.25). Our DW extraction reads
   raw transactions and aggregates independently — corr 1.0 against BCG is a genuine match. But
   any new validator should be examined for circular dependencies.

3. **Search before designing** (KÄRNPRINCIPER §6.4). Most artifacts you need probably exist already
   somewhere in `C:\Projekt\` or `OneDrive\...\Datastrategi`. Iterative search (MASTER_PYTHON §7.2)
   finds artifacts that don't match initial keywords by name.

4. **Document as you code** (KÄRNPRINCIPER §4.6). Every non-trivial file carries a header that says
   what it does, what it depends on, what depends on it, and what lessons motivate non-obvious
   choices. Future sessions (yours or someone else's) find the file by searching its header.

5. **Measure, don't guess** (Spår B principle). When a mapping or source is unclear, fetch all
   candidates and measure (median per-code ratio against facit). The one that clusters at 1.0 is
   the right answer. Saved us three times: source identity, net/gross, L4 mapping.

---

## Contact and ownership

**Project owner:** Jens Palmö (jepa02 / adm.jens.palmo@evidensia.se)
**Repo location:** https://github.com/Dennyakillen/evbcgpricing
**Companion repo:** https://github.com/Dennyakillen/Business_Analytics

This is an internal Evidensia analytics project. The code is owned by Evidensia; BCG's original
delivery is referenced but not redistributed.

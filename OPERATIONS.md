# OPERATIONS — Running & Maintaining the BCG Pricing Model

**Project:** `evbcgpricing` — replication, validation and ongoing operation of BCG's
price-elasticity pipeline on Evidensia's own growing data.
**Owner:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Scope of this document:** the *operational* runbook — how to run the model end to
end on fresh data, how to validate the result, and how to feed it into the BCG pricing
workbook. For *why* the model is built the way it is, see `README.md` (architecture)
and `docs/governance/` (decisions, locked assumptions, roadmap).

---

## 0. TL;DR — the production run, start to finish

```
1.  Refresh source data   →  Pipeline\01–02 data prep (DuckDB/Alteryx)
2.  Run elasticities       →  Cluster + Site models (growing window)
3.  Weave the levels        →  verify_tool\run\run_step6.py        (F1–F7 fallback)
4.  Validate the output     →  verify_tool\run_all_*  +  provenance / freshness
5.  Build the model feed    →  verify_tool\run\build_r12_for_model.py
6.  Paste into the model    →  Model_Feed_<date>.xlsx → BCG workbook blue tabs
7.  Set a price assumption  →  the workbook computes the revenue effect
```

Everything from step 3 onward runs locally with `py -3.11` (global Python 3.11, which
has duckdb / pandas / openpyxl / xlwings). The Azure VM is only needed for the heavy
model steps 1–4; step 6 and all validation run on the workstation.

---

## 1. Environment

- **Python:** use `py -3.11`. The global 3.11 has the required packages
  (duckdb, pandas, openpyxl, xlwings). 3.13 may lack pandas — do not use it for these
  scripts.
- **IT policy constraints:** install packages with `python -m pip` (not bare `pip`);
  `.ps1` scripts need `Unblock-File`; PyInstaller EXEs are blocked; Hyper-V is restricted
  by group policy. Always quote PowerShell paths that contain spaces.
- **PowerShell quirk:** do not embed long `python -c "..."` one-liners with nested
  quotes — they break. Write a `.py` file (or a here-string to `$env:TEMP\x.py`) and run
  that instead.
- **Azure VM** (`bcg-poc-vm`, subscription `ev-lz3-ai`, RG `ev-openai-swce-rg-test`,
  `ssh azureuser@172.18.148.4`): only for model steps 1–4. See `docs/ops/MASTER_AZURE.md`
  and `docs/ops/UBUNTU_AZURE_VM.md`.

---

## 2. The growing-data window (important)

BCG's original model ran on a fixed window ending **2025-06**. The growing pipeline runs
the **same 12-month (R12) length** but with the end date rolled forward to the latest
**complete** month in the data. The elasticity and the volumes must share that window —
they come from the same extract, so they do by construction.

`build_r12_for_model.py` picks the window automatically (latest complete month) unless
you pass `--end YYYY-MM`. The anchor for the growing elasticity window is fixed at
**2022-07-01** (see `docs/governance/LOCKED_ASSUMPTIONS.md`, LF.2).

---

## 3. Step-by-step

### 3.1 Run Step 6 — the fallback weave (F1–F7)

`verify_tool\run\run_step6.py` places the three inputs Step 6 expects, runs BCG's
`Fall_Back_Logic.py`, and verifies the output.

```powershell
cd "C:\Projekt\BCG"
py -3.11 verify_tool\run\run_step6.py
```

What it does:
- Places the **growing** Cluster model output (splitting `KEY → Cluster + ItemCode`,
  see LESSONS LB.52) and the **growing** Site model where `Constant.py` expects them.
- Places the **frozen** Cluster step-5 blend, weave weights, and bundle facit (the three
  locks — see LOCKED_ASSUMPTIONS LF.9).
- Runs the weave; tolerates the cosmetic xlwings named-range COM error on the template
  write (LB.53) — the data file is written *before* that step, so the run is treated as
  success and the F-level distribution is reported.

Output: `Pipeline\02. Elasticity\6. Fall Back Logic\output_data\Final_Fallback_Data_<ts>.xlsx`
— ~109k rows, ~15k products, one `final_elasticity` per ProductKey, plus `RSQ`,
`PVALUE_PRICE`, `elasticity_level` (which F-level sourced the value).

### 3.2 Validate

Run the validation suites (each writes an Excel receipt under `verify_tool\receipts\`):

```powershell
cd "C:\Projekt\BCG\verify_tool"
py -3.11 extraction_validation\run_all_validations.py     # DW extract vs facit
py -3.11 output_rationality\run_all_rationality.py        # fresh output sanity
py -3.11 provenance\run_all_provenance.py                 # fresh vs frozen + freshness
```

Read by the receipt, not the console (LESSONS R7 / trust-the-file). A `PASS` means the
check held; a `REVIEW` on provenance is **by design** — it flags the three frozen inputs,
it is not a defect.

Key things the suites confirm:
- Replication is bit-for-bit vs BCG on the old window (correlation 1.000000).
- Fresh output is 100% negative, 100% within the rational `(-10, 0)` band.
- Drift vs the 2025 baseline is ~95% under 0.5 (stable; within the snapshot-drift band).
- Bundle sources only ~2.2% of decisions (INSIGHTS IB.12).

### 3.3 Build the model feed

`verify_tool\run\build_r12_for_model.py` aggregates R12 volume + revenue per
ItemCode×Site and joins the fresh elasticity from Step 6, writing one workbook with three
sheets named exactly like the model's blue input tabs.

```powershell
cd "C:\Projekt\BCG"
py -3.11 verify_tool\run\build_r12_for_model.py `
  --tx "Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output\Sweden_weekly_model_data_site_level.csv"
```

Options: `--end 2026-04` (force window end), `--tx <path>` (transaction CSV),
`--fallback <path>` (specific Step 6 output; default = newest).

Output: `output_model_feed\Model_Feed_<date>.xlsx` (this folder is **gitignored** — the
feed is sensitive). Three sheets:
- **FACT_CodeClinic** — `FACT_CodeClinicKey, ItemCode, SiteCode, Cluster, Quant_25,
  Sales_25, Elasticity, _R2, _pValue`. ~99.5% of rows carry a matched elasticity.
- **DIM_Code** — per ItemCode: R12 sales/quantity, prefix, invoice group.
- **DIM_Site** — per site: cluster, site type.

Columns with a **yellow header** are intentionally empty — they are filled from external
sources (pricing from Provet, competition/HHI, FTE from Quinyx). See
`presentations\Model_Update_Guide.pdf` for the full have/remaining map.

### 3.4 Paste into the BCG workbook and read the revenue effect

Open `Model_Feed_<date>.xlsx`. For each sheet, select the columns, copy, and paste into
the matching blue tab of the BCG pricing workbook (`...BCG_Pricing_Model_vFinal.xlsx`),
matching on the key. **Do not touch the calculation tabs** (Calculations, Pricing Model,
dashboards) — they recompute automatically. Enter a price assumption in the model's input
and the workbook produces the revenue effect.

For a teaching walk-through of how a price assumption flows to a revenue effect, see
`presentations\Elasticitet_Beslutssnurra_BCG.xlsx` (an end-to-end calculator on one
article) and `presentations\Elasticitet_Sandbox_BCG.xlsx` (the method, step by step).

---

## 4. What is fresh vs frozen (operational truth)

| Part | State | To make fresh |
|---|---|---|
| Cluster + Site elasticities | **GROWING** | already fresh |
| R12 volume & revenue | **GROWING** | `build_r12_for_model.py` |
| Cluster step-5 routing | FROZEN (2025) | FD.15 — cheapest; `fallback_blend.py` on growing input |
| Weave weights | FROZEN (2025) | FD.14 — Alteryx Module 4 / DuckDB rebuild |
| Bundle branch | FROZEN (parked) | FD.11 — only 2.2% weave-win; conditional |

The core price-sensitivity signal — the figures that drive pricing — is fresh today. The
three frozen locks affect a small, documented share of the outcome. Lift them in the order
FD.15 → FD.14 → FD.11 (cost vs impact). See `docs/governance/LOCKED_ASSUMPTIONS.md` LF.9.

---

## 5. Re-running as periods grow

The whole chain is re-runnable. When a new month closes:
1. Refresh the source extract (the growing weekly CSV).
2. Re-run Cluster + Site models (VM) → Step 6 (`run_step6.py`).
3. Re-validate (`run_all_*`).
4. Re-build the feed (`build_r12_for_model.py`) — the R12 window rolls forward
   automatically.
5. Re-run `analysis\analys_bcg_freshness.py` if you want the "what changed since BCG"
   decomposition and the top-management deliverable refreshed.

---

## 6. Where things live (post-cleanup)

```
verify_tool\run\        run_step6, build_r12_for_model, fallback_blend, run_bundle_dataprep
verify_tool\            proof_chain, extraction_validation, output_rationality, provenance
analysis\               analys_bcg_freshness, xlsx_export_bcg_freshness, compare_elasticity_runs
presentations\          elasticity_since_bcg.*, Model_Update_Guide.*, Elasticitet_*.xlsx
output_model_feed\      Model_Feed_<date>.xlsx (gitignored — sensitive)
output_analyspaket\     Analyspaket_BCG_Freshness_<date>.xlsx
docs\governance\        PLAYBOOK, ROADMAP, LOCKED_ASSUMPTIONS, FUTURE_DEVELOPMENT
docs\knowledge\         LESSONS_BCG, INSIGHTS_BCG, F9_BUNDLE_INVENTORY
docs\ops\               TECHNICAL_PREREQUISITES, KRAVSPEC_IT, MASTER_AZURE, UBUNTU_AZURE_VM
Pipeline\               the model itself (steps 1–6) — unchanged
```

---

*Maintained by Jens Palmö. This runbook reflects the state after FAS F (fresh-data
operation) was completed: Step 6 runs on growing data, output is validated, and the model
can be fed and run end to end on each new period.*

# verify_tool — re-runnable proof that our pipeline reproduces BCG's

**Developer:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Purpose:** A library of independent, re-runnable validators — one per model part —
that each prove our replicated pipeline reproduces BCG's frozen result. When a
decision-maker questions a number, run that one validator **live**: the screen shows
what-is-compared-to-what and that it matches. Granularity is the credibility.

Each validator is standalone, path-agnostic (sensible defaults, overridable with
`--args`), and **reports deviations** rather than a binary PASS/FAIL — showing where
and how much it differs is what makes a clean result trustworthy.

---

## Environment — IMPORTANT, read before running

The validators run with the Python that has the pipeline dependencies
(duckdb, pandas, openpyxl). On this machine that is **global Python 3.11**
(duckdb 1.5.3, pandas 3.0.1) — NOT the `.venv` under `Pipeline\02. Elasticity`
and NOT Python 3.13; neither has duckdb.

Run the suite with 3.11 explicitly:

```powershell
cd "C:\Projekt\BCG\verify_tool"
py -3.11 verify_dataprep.py
py -3.11 verify_model.py --family cluster
py -3.11 verify_blend.py
py -3.11 verify_fallback.py
```

Why this matters: `verify_dataprep.py` and `verify_blend.py` shell out to
`replicate_dataprep.py` / `fallback_blend.py` using the SAME interpreter that
runs the wrapper (`sys.executable`). If you launch from a venv without duckdb,
the inner call fails with `ModuleNotFoundError: No module named 'duckdb'` — the
tool is fine, the interpreter is wrong. `verify_model.py` and `verify_fallback.py`
need only pandas/numpy/openpyxl, so they are less fragile, but run them all with
3.11 for consistency.

> **Tech-debt (FAS T):** the replication env lives in global Python 3.11, not an
> isolated venv. It works but is not reproducible for a successor. A pinned venv
> (or requirements.txt + fresh venv) belongs on the FAS T list.

## The chain (run in this order — mirrors the README milestone tracker)

| # | Validator | Phase / FR | Proves (in business terms) |
|---|---|---|---|
| 1 | `verify_dataprep.py` | FR-1 | The input feeding the model is BCG's data: same rows, same revenue (TotalNet), same volume (SoldQuantity) — per row. |
| 2 | `verify_model.py --family cluster` | FR-4 | Cluster elasticities reproduce BCG's (3812 product×cluster groups). |
| 2 | `verify_model.py --family site` | FR-5 | Site elasticities reproduce BCG's (4673 product×site groups). |
| 2 | `verify_model.py --family bundle` | FR-6 | Bundle elasticities reproduce BCG's (125 basket groups). |
| 3 | `verify_blend.py` | FR-3 | The sparse-group rescue (step 5) picks the same 43 representatives BCG did. |
| 4 | `verify_fallback.py` | FR-7 | The full F1–F7 fallback weave (step 6) reproduces BCG's final elasticity per product — bit-for-bit. |

Optional deep-dive (not in the main sequence): `compare_features_to_facit.py` validates
feature_selection (FR-2). Skipped by default because `verify_model` already proves the
elasticity that feature selection produces — validating the elasticity is the stronger
proof than validating the intermediate feature choice.

---


## Run everything at once + receipt

`run_all.py` is an orchestrator: it runs the five validators above in milestone
order, streams each one's full output, prints a consolidated milestone table at
the end, and (with `--excel`) writes a dated Excel receipt.

```powershell
cd "C:\Projekt\BCG\verify_tool"
py -3.11 run_all.py            # full chain, console only
py -3.11 run_all.py --excel    # full chain + dated receipt in receipts\
```

The receipt is a single "Logg" sheet: the run's raw stdout verbatim, in Consolas
monospace so stdout's own column alignment is preserved (one log line per cell,
'='-lines forced to text so they aren't read as formulas). It is a frozen snapshot
of one run, named `verify_receipt_YYYY-MM-DD.xlsx`.

## Check the environment first

`verify_infra.py` answers "is everything in place to run the suite?" *before* you
trust any proof. Run it when returning to the project, on a new machine, or before
a live demo:

```powershell
py -3.11 verify_infra.py
```

It checks, in order: (1) Python 3.11 has duckdb/pandas/openpyxl/numpy; (2) the suite
files are present; (3) the frozen BCG facit files exist (the untouched original);
(4) our produced artefacts exist; (5) a structure audit of repo root + verify_tool
(EXPECTED / STRAY / MISSING / UNKNOWN); (6) a deep file-by-file audit of the folders
we own (each model's `code\` + `code\src\`, dataprep `scripts\`) - naming every
stray log/backup and flagging any missing core file. It reports; it never deletes.


## How to read the output

Every validator leads with a **SUMMARY** of the reliable measures, then keeps full
detail below ("for anyone who wants to dig") — nothing is hidden.

The measures that matter, in order:
1. **Population match** — same set of groups (no missing / extra).
2. **Median |diff|** — 0 means the typical group is bit-identical.
3. **% identical groups** — how much of the mass matches exactly.
4. **Rank correlation (Spearman)** — do groups rank-order the same way. Robust to a
   few weak-signal tail groups (unlike Pearson, which a handful of near-zero or
   sign-flipped groups can drag down — Pearson is shown last, with that caveat).
5. **Decision-relevant subset** — match on the *significant* groups (IB.2 gate:
   RSQ≥0.5, p≤0.20, −10<elasticity<0). These are the only groups that can flip a
   price decision; diffs elsewhere are weak-signal noise the fallback discards.

A faithful replication is **not** expected to be 100% on every single group, and it
need not be: finer levels (Site, Bundle) carry weak-signal tail groups (IB.9) that the
model's own fallback discards before any price decision. What must hold is the
structure, the typical value, and the price-relevant groups.

---

## Per-validator reference

### 1. verify_dataprep.py  (FR-1)
- **Proves:** rows, revenue (TotalNet), volume (SoldQuantity), items, groups all match
  BCG's frozen 0828 facit, per row (corr 1.0, max_abs_diff 0).
- **Against:** `…\BCG_orginal_V2_New\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv` (and P_CH).
- **Method:** thin wrapper around `replicate_dataprep.py --validate-only` (no SQL re-run).
- **Run:** `python verify_dataprep.py`
- **Expected:** P_C and P_CH both diff = 0.000% on every aggregate, corr 1.000000, PASS.
- **CRITICAL:** the default `--facit-dir` points at the UNTOUCHED original, NOT the
  `Pipeline\…\data` working copy — that copy gets overwritten by `export_b4b` runs
  (the 2026-05-25 drift that broke encoding and emptied the P_CH facit). Facit must be
  the frozen source.

### 2. verify_model.py  (FR-4 / FR-5 / FR-6)
- **Proves:** elasticity per KEY matches BCG, for each model family.
- **Against:** `…\<N>. … Models\output\model\output_summary.xlsx` in the original.
  Our side = `…\Pipeline\…\<N>. … Models\output\azure_run_model\output_summary.xlsx`.
- **Run:** `python verify_model.py --family cluster|site|bundle`
- **Expected:**
  - cluster: 3812/3812 population, median |diff| 0, rank-corr 1.000, decision-relevant 1118/1118 (100%).
  - site:   4673/4673 population, median |diff| 0, rank-corr ~0.91, decision-relevant ~113/144.
  - bundle:  125/125 population, median |diff| 0, rank-corr ~0.93, decision-relevant ~57/70.
- **Note (IB.9):** Site/Bundle have a handful of *significant* groups that sign-flip
  between runs — weak-signal OLS near the noise boundary, not a replication error.

### 3. verify_blend.py  (FR-3)
- **Proves:** the cluster-blend (step 5) selects the same 43 representatives as BCG, with
  matching significance flags, on key (Service, big_cluster, New_cluster).
- **Against:** `…\2. Product Cluster Level Models\output\final_model_cluster_granularity.xlsx` (43 reps) in the original.
- **Method:** thin wrapper around `fallback_blend.py --facit`.
- **Run:** `python verify_blend.py`
- **Expected:** representative set 43/43 (only_facit 0, only_ours 0), significance 43/43, PASS.

### 4. verify_fallback.py  (FR-7)
- **Proves:** the full F1–F7 fallback weave (step 6) assigns the same final elasticity per
  product as BCG, bit-for-bit, on row grain (ProductKey + SiteCode + Clusters).
- **Against:** `…\6. Fall Back Logic\output_data\Final_Fallback_Data_20250930_091648.xlsx` in the original.
- **Run:** `python verify_fallback.py`
- **Expected:** correlation 1.000000, |diff| 0, F1–F7 distribution identical, 100% level
  match across 108,979 rows / 15,128 ProductKeys.

---

## Lessons baked in (so they aren't re-learned the hard way)

- **Validate against the frozen original, never a working-folder copy.** The
  `Pipeline\…\data` facit copies drifted (re-encoded, P_CH emptied) because that folder
  is also an `export_b4b` output target. All defaults here point at the OneDrive original.
- **Distrust corr 1.0 until source independence is confirmed.** Our dataprep reads raw
  `transaction_data.parquet` + DW dimensions and aggregates independently — it does NOT
  read BCG's 0828 file. So corr 1.0 is a genuine match, not a copy compared to itself.
  (Confirmed: different sort order, different column count, different number formatting.)
- **No scipy in the env.** Rank correlation is computed as Pearson-on-ranks
  (`.rank().corr()`), not `.corr(method="spearman")`, which needs scipy.
- **Facit lives in the original; some facit files carry extra columns** (`TotalNetXVat`,
  `Productive_time_per_site`) our dataprep doesn't emit — flagged as `only_facit`, not an
  error for FR-1, but `Productive_time_per_site` (FTE) may matter for a future full run.

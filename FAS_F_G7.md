# FAS F — G7: Parametrized date window (fresh-data readiness)

**Branch:** `fas-f-fresh-data`
**Status:** G7 complete and proven across the whole pipeline. Fresh-data *run*
not yet attempted — three prerequisites remain (see "What's left").
**Developer:** Jens Palmö, with AI advisor.

---

## What G7 solves

BCG's pipeline hardcoded the data window (`2022-07-01 … 2025-06-29`) in several
files. With fresh 2026 data this would **silently filter out everything after
June 2025** — no crash, just wrong (stale) results. G7 makes the window
parametrizable so a fresh run needs **no code edit**: set an environment
variable and run.

**Design principle — default reproduces the old facit exactly.** With no env
vars set, every changed file behaves bit-for-bit as before. This was proven:
`verify_dataprep.py` with no env still gives `overall=PASS`, corr 1.000000,
485,248 + 196,464 rows, diff 0.000% — FR-1 untouched. The easy way back to BCG's
frozen window is simply to run without env vars (or `git checkout main`).

---

## How to run a fresh window

Set the end date (and optionally the start anchor) before running:

```powershell
$env:BCG_END_DATE = '2026-04-30'   # last day of data to include
# optional:
# $env:BCG_START_DATE  = '2022-07-01'   # fixed anchor (default already this)
# $env:BCG_SPECIAL_WEEKS = '...'        # comma-separated media weeks; default = BCG's
```

`END_DATE2` (exclusive upper bound used by model filters) is **derived
automatically** as `END_DATE + 1 day` — never set it by hand.

Window type is a **growing window with fixed anchor** (always starts 2022-07-01,
grows as months accrue). Rolling windows (e.g. last 36 months) are a deliberate
later analytical step, intentionally **not** built here.

To return to BCG's frozen window: unset the vars (`Remove-Item Env:\BCG_END_DATE`)
or check out `main`.

---

## What was changed (all on branch `fas-f-fresh-data`)

| File | Change | Backup |
|------|--------|--------|
| `constants.py` (cluster) | Date block → env-overridable; `END_DATE2` derived; `SPECIAL_WEEKS` env-overridable. `import os` + `datetime` added. | rebuilt (full file) |
| `constants.py` (site, bundle) | Same date block, surgical (granularity preserved: site `ItemCode`/`Cluster`, bundle `Bundle_code`/`Clusters`). | `.bak-g7` |
| `data_prepration.py` (cluster) | line 565: hardcoded `'2025-06-23'` → `END_DATE` (W-MON rounding makes them equivalent). | `.bak-g7` |
| `data_prepration.py` (site, bundle) | **No change** — already used `END_DATE`. | — |
| `replicate_dataprep.py` | Added `_inject_dates()`: env-gated in-memory rewrite of the SQL date window. SQL file on disk stays verbatim. | `.bak-g7` |
| `01_process.sql` | **No change** — date window injected in-memory by the Python above. | — |

Environment: `pyyaml` installed into global Python 3.11 (site/bundle
`constants.py` load `config.yml` at import; 3.11 lacked yaml). FAS T debt: env
lives in global Python, not an isolated venv.

---

## Proof it works

- **Default unchanged:** `verify_dataprep.py` (no env) → PASS, corr 1.000000,
  485,248 + 196,464 rows, no `[G7]` log line.
- **Override active:** with `BCG_END_DATE=2026-04-30`, `_inject_dates` rewrote
  the SQL window in-memory (`2026-04-30` in, `2025-06-28` gone) and logged
  `[G7] 01_process.sql: SQL date window overridden -> end=2026-04-30`.

---

## What's left before a real fresh run (next session)

G7 makes the window *settable*. It does **not** by itself produce valid fresh
results — three prerequisites remain, in order:

1. **Isolate the facit.** A fresh run writes to dirs where BCG's facit currently
   sits unprotected (the 2026-05-25 drift showed this risk). Copy the BCG
   original to a read-only reference **before** any fresh run touches those dirs.
2. **Fresh source, not just fresh window (Spår B).** `00_read.sql` still reads
   BCG's frozen `transaction_data.parquet`. A fresh window over a frozen source
   has no fresh data to find. The DW-native read must be built/verified so the
   pipeline reads *current* transactions for the chosen window.
3. **Data-completeness gate (Nivå 1 safety).** Before auto-running "latest closed
   month", verify the DW actually has complete data for the whole window —
   running an incomplete latest month is a silent error. This is the gate that
   makes monthly auto-runs safe.

Only after these three is a fresh run meaningful, followed by reasonableness
validation against the (now isolated) facit.

---

## Cleanup pending

`.bak-g7` files (3× constants, 1× data_prepration, 1× replicate_dataprep) are
flagged STRAY by `verify_infra.py`. Remove them **only after** the full G7 path
is run and verified end-to-end — they are the rollback until then.

"""
assess_bundle_materiality.py — F.9 Bundle, drivande-effekt-validering (v2)

Purpose
-------
Decide whether to finish Bundle now or park it (FUTURE_DEVELOPMENT). v1 measured all
bundle-cluster transaction revenue (23.9% of total) -- but Jens's key insight: the
FALLBACK WEAVE (FR-7, F1-F7) means a ProductKey's final elasticity can come from
Cluster, Site, OR Bundle depending on which survives the significance gate. So "how
much does Bundle drive" is NOT a revenue question -- it's "how often does Bundle
become the chosen source in the weave", which can't be known until Step 6 runs (and
Step 6 needs Bundle output we don't have -> a circular dependency).

This v2 measures the STRUCTURAL signals that bound Bundle's possible role in the weave,
without running it:

1. Modelled-basket revenue: only the baskets BCG flagged To_run_elasticity_analysis=1
   (the 98), via the Revenue column in sweden_bundle_analysis.csv -- the RELEVANT
   materiality, not all 63,737 baskets. v1 measured the wrong denominator.

2. Overlap framing: bundle transactions are ALSO product x site transactions already
   priced by Cluster/Site. Bundle is an ALTERNATIVE pricing of the same money, not
   additive. We report this as a caveat, not a number (true overlap needs Step 6).

3. Service-mix of modelled baskets: which ProductGroupL4Name services the 98 baskets
   touch (Surgery/Imaging/Hospitalisation/etc). If they concentrate in services
   Cluster/Site already price well, Bundle's marginal weave-contribution is likely
   low; if they hit services that are thin/insignificant at cluster level, Bundle may
   be the only source that rescues those KEYs -> higher weave value.

Honest limit
-----------
None of this MEASURES drivande effekt -- only Step 6 (fallback weave) does, and the
Cluster+Site rimlighetsgrind gives the fuller read. This bounds the question so the
FUTURE_DEVELOPMENT note is grounded, not guessed.

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 assess_bundle_materiality.py

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-11 (v2: modelled-basket focus + weave caveats).
"""
import sys
from pathlib import Path

import duckdb

BUNDLE_ROOT = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\4. Bundle Clinic Data Prep"
    r"\Sweden_Bundling_Data_Prep"
)
MASTER_PARQUET = BUNDLE_ROOT / "parquet" / "sweden_master_data.parquet"
BUNDLE_OUTPUT = BUNDLE_ROOT / "output" / "Raw_Data_Clinic_Hospital.csv"
BUNDLE_DEF = BUNDLE_ROOT / "input" / "sweden_bundle_analysis.csv"


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def money(v):
    if v is None:
        return "n/a"
    return f"{v/1e9:.3f} mdr" if abs(v) >= 1e9 else f"{v/1e6:.1f} M"


def main() -> int:
    for f in (MASTER_PARQUET, BUNDLE_OUTPUT, BUNDLE_DEF):
        if not f.exists():
            log("ERROR", f"missing: {f}")
            return 1

    con = duckdb.connect()
    mp = str(MASTER_PARQUET).replace("\\", "/")
    bo = str(BUNDLE_OUTPUT).replace("\\", "/")
    bd = str(BUNDLE_DEF).replace("\\", "/")

    # --- 0) denominator: total growing revenue ------------------------------
    total_rev = con.execute(
        f"""SELECT SUM(CAST(SalesTotal AS DOUBLE)) FROM read_parquet('{mp}')
            WHERE CAST(week_starting_monday AS DATE) >= DATE '2022-07-01'
              AND CAST(SalesTotal AS DOUBLE) > 0"""
    ).fetchone()[0]
    log("TOTAL", f"masterdata revenue (gross, anchor>=2022-07-01) = {money(total_rev)}")

    # --- 1) ALL bundle-transaction revenue (v1 number, kept for context) ----
    all_bundle_rev = con.execute(
        f"SELECT SUM(CAST(SalesTotal AS DOUBLE)) FROM read_csv('{bo}', all_varchar=true)"
    ).fetchone()[0]
    log("ALL-BASKETS", f"all bundle-transaction revenue = {money(all_bundle_rev)} "
                       f"({100*all_bundle_rev/total_rev:.1f}% of total) "
                       f"-- overlaps Cluster/Site, NOT additive")

    # --- 2) MODELLED baskets only (To_run_elasticity_analysis=1) ------------
    # sweden_bundle_analysis.csv has a per-basket Revenue column.
    cols = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv('{bd}', all_varchar=true)"
    ).fetchall()]
    if "Revenue" in cols and "To_run_elasticity_analysis" in cols:
        row = con.execute(
            f"""SELECT
                  SUM(CAST(Revenue AS DOUBLE)) AS rev_all,
                  SUM(CASE WHEN CAST(To_run_elasticity_analysis AS INTEGER)=1
                           THEN CAST(Revenue AS DOUBLE) ELSE 0 END) AS rev_modelled,
                  COUNT(*) AS n_all,
                  SUM(CASE WHEN CAST(To_run_elasticity_analysis AS INTEGER)=1 THEN 1 ELSE 0 END) AS n_modelled
                FROM read_csv('{bd}', all_varchar=true)"""
        ).fetchone()
        rev_all, rev_modelled, n_all, n_modelled = row
        log("DEF-FILE", f"{n_all:,} baskets defined, {n_modelled:,} flagged to model "
                        f"({100*n_modelled/n_all:.2f}%)")
        log("MODELLED", f"revenue in the {n_modelled} modelled baskets = {money(rev_modelled)} "
                        f"(per basket-def Revenue column)")
        if rev_all:
            log("MODELLED", f"modelled baskets = {100*rev_modelled/rev_all:.1f}% of all "
                            f"basket-def revenue; the other {n_all-n_modelled:,} baskets "
                            f"are defined but NOT modelled")
        # NOTE: basket-def Revenue is BCG's own basket revenue (may differ in scope from
        # our growing txn revenue) -- treat as order-of-magnitude, not exact.
    else:
        log("WARN", f"Revenue/To_run_elasticity_analysis not both in def file cols: {cols}")

    # --- 3) service-mix of bundle transactions (where do baskets live?) -----
    svc = con.execute(
        f"""SELECT ProductGroupL4Name,
                   SUM(CAST(SalesTotal AS DOUBLE)) AS rev
            FROM read_csv('{bo}', all_varchar=true)
            GROUP BY 1 ORDER BY rev DESC"""
    ).df()
    svc["rev_M"] = (svc["rev"] / 1e6).round(1)
    svc["pct"] = (100 * svc["rev"] / svc["rev"].sum()).round(1)
    log("SERVICE-MIX", "bundle-transaction revenue by service (where the baskets concentrate):")
    print(svc[["ProductGroupL4Name", "rev_M", "pct"]].to_string(index=False))

    print()
    log("CAVEAT", "Bundle's true drivande effekt = how often it becomes the CHOSEN source "
                  "in the FR-7 fallback weave. That needs Step 6 (which needs Bundle output "
                  "-> circular). These numbers BOUND the question; the Cluster+Site "
                  "rimlighetsgrind gives the fuller verdict.")
    log("NEXT", "Feed MODELLED revenue + SERVICE-MIX into the FUTURE_DEVELOPMENT Bundle note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

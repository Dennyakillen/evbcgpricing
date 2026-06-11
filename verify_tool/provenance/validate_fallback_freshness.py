"""
validate_fallback_freshness.py
==============================
Output rationality on FRESH data: what did the growing data actually change in the
final blended elasticity? Compares our growing Step 6 output (Final_Fallback_Data)
against BCG's frozen fallback facit, per ProductKey+SiteCode+Clusters, and reports
the drift -- so a decision-maker sees, concretely, how much the fresh data moved the
numbers and which products moved most.

This is the fresh-data analogue of verify_fallback.py (which proved bit-for-bit match
on OLD data). On growing data there is no facit to match -- instead we judge by:
  - Is the fresh final_elasticity still rational? (negative, in (-10,0) band)
  - How big is the drift vs the frozen facit? (within IB.11 baseline band or beyond?)
  - Which F-level sources the fresh number, and does the mix differ from facit?
  - Would the drift flip a price decision? (IB.6: that's the only precision that matters)

Honest framing (LF.9): the growing inputs are Cluster+Site elasticities; weights,
routing, and bundle are frozen. So observed drift is driven by the GROWING elasticities
flowing through a partly-frozen weave. This validator attributes drift to that, and
flags that fully-fresh drift requires lifting FD.14/15/11.

Against: BCG frozen Final_Fallback_Data_20250930_091648.xlsx (the OneDrive facit).
Method:  load both, align on row grain, compute per-row delta + distribution.

Run (PowerShell):
    cd "C:\\Projekt\\BCG\\verify_tool\\provenance"
    py -3.11 validate_fallback_freshness.py
    py -3.11 validate_fallback_freshness.py --our "<path>" --facit "<path>"

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Created:   2026-06-11
"""
import sys
import argparse
import glob
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
import numpy as np   # noqa: E402

from _provenance_helpers import (  # noqa: E402
    BCG_ROOT, section, subsection, now_iso,
)

FBL = BCG_ROOT / "Pipeline" / "02. Elasticity" / "6. Fall Back Logic"
BCG_FBL_FACIT = (
    Path("C:/Users/jepa02/OneDrive - Evidensia Djursjukvård AB/Datastrategi/BCG")
    / "BCG_orginal_V2_New" / "02. Elasticity" / "6. Fall Back Logic"
)

# IB.11 baseline drift band (revenue 0.057%, per-cluster up to ~1.5%); for elasticity
# we use the rationality-suite drift thresholds (acceptable < 0.5, decision-relevant > 1.0).
DRIFT_ACCEPTABLE = 0.5
DRIFT_DECISION = 1.0

GRAIN = ["ProductKey", "SiteCode", "Clusters"]


def _find_our_output(override):
    if override:
        return Path(override)
    cands = glob.glob(str(FBL / "output_data" / "Final_Fallback_Data*.xlsx")) + \
            glob.glob(str(FBL / "Final_Fallback_Data*.xlsx"))
    if not cands:
        return None
    return Path(max(cands, key=os.path.getmtime))


def _find_facit(override):
    if override:
        return Path(override)
    # The frozen 20250930 facit named in verify_tool README.
    cands = glob.glob(str(BCG_FBL_FACIT / "output_data" / "Final_Fallback_Data*.xlsx")) + \
            glob.glob(str(BCG_FBL_FACIT / "Final_Fallback_Data*.xlsx"))
    if not cands:
        return None
    # prefer the 20250930 one if present
    for c in cands:
        if "20250930" in c:
            return Path(c)
    return Path(max(cands, key=os.path.getmtime))


def _load(path, label):
    df = pd.read_excel(path)
    # normalise grain dtypes for a clean join
    for c in GRAIN:
        if c in df.columns:
            df[c] = df[c].astype(str)
    df["final_elasticity"] = pd.to_numeric(df.get("final_elasticity"), errors="coerce")
    subsection(f"{label}: {Path(path).name}")
    print(f"  rows: {len(df):,}  ProductKeys: {df['ProductKey'].nunique():,}"
          if "ProductKey" in df.columns else f"  rows: {len(df):,}")
    return df


def main():
    ap = argparse.ArgumentParser(description="Fresh-data rationality: growing Step 6 vs frozen facit.")
    ap.add_argument("--our", default=None, help="override path to our growing Final_Fallback_Data")
    ap.add_argument("--facit", default=None, help="override path to BCG frozen Final_Fallback_Data")
    args = ap.parse_args()

    section("STEP 6 FRESHNESS RATIONALITY  -  what did growing data change?")
    print(f"Run timestamp: {now_iso()}")
    print("Comparing our GROWING Step 6 output to BCG's FROZEN fallback facit, per")
    print("ProductKey+SiteCode+Clusters. On growing data there's no facit to match;")
    print("we judge rationality + drift, and attribute drift to the growing inputs.")
    print("Honest note (LF.9): elasticities are growing; weights/routing/bundle frozen.")
    print()

    our_path = _find_our_output(args.our)
    facit_path = _find_facit(args.facit)
    if our_path is None or not our_path.exists():
        print(">> Result: REVIEW  (our growing output not found -- run run_step6.py first)")
        return 1
    if facit_path is None or not facit_path.exists():
        print(f"  facit not found at {BCG_FBL_FACIT}")
        print(">> Result: REVIEW  (frozen facit not found -- check OneDrive path)")
        return 1

    our = _load(our_path, "OURS (growing)")
    facit = _load(facit_path, "FACIT (frozen BCG)")

    # ---- 1) standalone rationality of the fresh output ----
    section("1. FRESH OUTPUT RATIONALITY (does it stand on its own?)")
    fe = our["final_elasticity"]
    print(f"  median final_elasticity : {fe.median():.3f}")
    print(f"  negative                : {100*(fe<0).mean():.1f}%")
    print(f"  in (-10, 0) band        : {100*((fe>-10)&(fe<0)).mean():.1f}%")
    print(f"  positive (review)       : {100*(fe>0).mean():.1f}%")
    print(f"  below -10 (absurd)      : {100*(fe<-10).mean():.1f}%")
    rational = (fe < 0).mean() > 0.95 and ((fe > -10) & (fe < 0)).mean() > 0.95
    print(f"  -> {'RATIONAL: negative + bounded, decision-usable' if rational else 'REVIEW: irrational tail present'}")
    print()

    # ---- 2) drift vs frozen facit (what the growing data moved) ----
    section("2. DRIFT vs FROZEN FACIT (what growing data changed)")
    keys = [c for c in GRAIN if c in our.columns and c in facit.columns]
    if not keys:
        print("  cannot align: grain columns missing in one side; skipping drift.")
    else:
        m = our.merge(
            facit[keys + ["final_elasticity"]].rename(columns={"final_elasticity": "fe_facit"}),
            on=keys, how="inner"
        )
        m["fe_ours"] = m["final_elasticity"]
        m["delta"] = m["fe_ours"] - m["fe_facit"]
        m = m.dropna(subset=["delta"])
        n = len(m)
        print(f"  aligned rows (in both): {n:,}")
        if n:
            ad = m["delta"].abs()
            print(f"  median |delta|          : {ad.median():.4f}")
            print(f"  mean   |delta|          : {ad.mean():.4f}")
            print(f"  within acceptable (<{DRIFT_ACCEPTABLE}) : {100*(ad<DRIFT_ACCEPTABLE).mean():.1f}%")
            print(f"  decision-relevant (>{DRIFT_DECISION})  : {100*(ad>DRIFT_DECISION).mean():.1f}%  "
                  f"({(ad>DRIFT_DECISION).sum():,} rows)")
            print()
            print("  Top 10 products by |drift| (growing data moved these most):")
            top = m.reindex(ad.sort_values(ascending=False).index).head(10)
            for _, r in top.iterrows():
                print(f"    {str(r['ProductKey'])[:14]:<14} {str(r.get('Clusters',''))[:14]:<14} "
                      f"facit {r['fe_facit']:+.3f} -> ours {r['fe_ours']:+.3f}  (delta {r['delta']:+.3f})")
        only_ours = len(our) - n
        only_facit = len(facit) - n
        print()
        print(f"  population: matched {n:,}, only_ours {only_ours:,}, only_facit {only_facit:,}")
        if only_ours or only_facit:
            print("  (population diff expected: growing data adds/drops KEYs -- new items, "
                  "credit/return mix, clinic reclass; cf IB.11 snapshot drift)")
    print()

    # ---- 3) F-level mix: growing vs frozen ----
    section("3. F-LEVEL SOURCE MIX (growing vs frozen) -- bundle reliance check")
    if "elasticity_level" in our.columns:
        ours_mix = our["elasticity_level"].value_counts(normalize=True).mul(100).round(1)
        print("  OURS (growing):")
        for lvl, pct in ours_mix.items():
            mark = "  <-- BUNDLE" if isinstance(lvl, str) and ("F2" in lvl or "F4" in lvl) else ""
            print(f"    {str(lvl):<30} {pct:5.1f}%{mark}")
        bundle_share = our["elasticity_level"].astype(str).str.contains("F2|F4").mean() * 100
        print(f"  bundle (F2/F4) reliance: {bundle_share:.1f}%  (IB.12: weave-win, frozen via FD.11)")
    print()

    # ---- verdict ----
    section("FRESHNESS VERDICT")
    print("  The fresh blended elasticities are decision-usable to the extent that:")
    print(f"    - they are rational on their own ({'YES' if rational else 'REVIEW'})")
    print("    - drift vs facit is mostly within band (see section 2)")
    print("    - the bundle-frozen share is small (IB.12: ~2% weave-win)")
    print()
    print("  CAVEAT (LF.9): drift here is driven by GROWING Cluster+Site elasticities")
    print("  flowing through a weave whose WEIGHTS (FD.14), ROUTING (FD.15) and BUNDLE")
    print("  branch (FD.11) are still frozen at 2025. Fully-fresh drift needs those lifted.")
    print()
    overall = "PASS" if rational else "REVIEW"
    print(f"  >> Result: {overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

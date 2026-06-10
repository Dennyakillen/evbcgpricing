"""
investigate_outliers_and_drift.py
=================================================================================
Investigation script (READ-ONLY) for the 2026-06-08 cluster output_summary
(4180 KEY). Single-sheet "Logg" Excel receipt, matching the nine existing
output_rationality validators exactly (same helpers, same capture/receipt API).

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Created:   2026-06-08 follow-up session (REVIEW deep-dive)

WHAT IT DOES
  [1] MBAS0703 deep-dive
      - Pull Clinics-MBAS0703 from ours output_summary (rev, qty, RSQ, p-value).
      - n_weeks / price variance are NOT in output_summary (8-col schema), so
        scan model_results.csv in chunks ONLY for MBAS0703 rows if present.
      - Look the same KEY up in BCG facit. New KEY (post-2025-06) -> no facit.
      - Show 2-cond vs IB.2 4-cond significance for this KEY.

  [2] R2 drift sampling (random, seed=42)
      - Reproduce check 03's drift definition BIT-IDENTICALLY:
        inner merge on KEY, dropna on both elasticities, abs_delta > 1.0.
      - Print drift count as a self-check vs the 359 check 03 reported.
      - seed=42, sample 10. Per KEY: ours/bcg elast, delta, both RSQ/p, revenue.

  [3] Significance-definition impact  *** the real decision input ***
      - helpers.is_significant() uses TWO of IB.2's FOUR conditions
        (RSQ>=0.5 & p<=0.2), omitting (-10 < elast < 0).
      - Measures the blast radius of correcting it: how many KEY currently
        flagged Sig=YES flip to not-significant under the full IB.2 gate, with
        a reason breakdown and a listing. "Measure, don't guess" before touching
        a helper that five scripts import.

  [4] Check 07 re-run WITHOUT MBAS0703 (in-memory)
      - Recompute Top-50 leverage with MBAS0703 removed (2-cond), and under the
        corrected 4-cond gate; report which KEY enter the Top-50.

METHODOLOGY GUARANTEES
  - NEVER mutates any data file. Pure read. Section 3/4 use in-memory copies.
  - Everything goes through capture_stdout() -> single Logg receipt; paste back.
  - Uses the SAME helpers/columns/significance logic as the suite, so numbers
    reconcile with the nine validators by construction.

USAGE
  cd C:\\Projekt\\Business_Analytics
  & ".\\.venv\\Scripts\\Activate.ps1"
  python C:\\Projekt\\BCG\\verify_tool\\output_rationality\\investigate_outliers_and_drift.py
  # or override:
  python .../investigate_outliers_and_drift.py --output-summary "<path to xlsx>"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse
import numpy as np
import pandas as pd

from _rationality_helpers import (
    resolve_our_output_summary, BCG_FACIT_OUTPUT_SUMMARY,
    COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET, COL_QUANTITY,
    SIG_RSQ_MIN, SIG_PVALUE_MAX,
    OUTLIER_ABS_THRESHOLD, OUTLIER_NEGATIVE_FLOOR, DRIFT_HARD_THRESHOLD,
    is_significant, extract_itemcode_from_key, extract_cluster_from_key,
    fmt_int, fmt_msek, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, capture_stdout, write_log_receipt,
)

# --------------------------------------------------------------------------- #
TARGET_KEY = "Clinics-MBAS0703"
TARGET_ITEMCODE = "MBAS0703"
SAMPLE_N = 10
SAMPLE_SEED = 42
TOP_LEVERAGE_N = 50
EXPECTED_DRIFT_COUNT = 359   # what check 03 reported on 2026-06-08; self-check


def _full_ib2_significant(elast, rsq, pval):
    """IB.2 FOUR-condition gate (the correct BCG significance flag):
       RSQ>=0.5 AND p<=0.2 AND elast<0 AND elast>-10.
       helpers.is_significant() does only the first two."""
    return (
        (rsq >= SIG_RSQ_MIN)
        & (pval <= SIG_PVALUE_MAX)
        & (elast < 0)
        & (elast > OUTLIER_NEGATIVE_FLOOR)   # -10.0 from helpers
    )


def _model_results_path(our_path: Path) -> Path:
    return our_path.parent / "model_results.csv"


# =================================================================================
# SECTION 1 - MBAS0703 DEEP-DIVE
# =================================================================================
def section_mbas(ours, bcg, our_path):
    section("[1/4] MBAS0703 DEEP-DIVE")

    e = pd.to_numeric(ours[COL_ELASTICITY], errors="coerce")
    rsq = pd.to_numeric(ours[COL_RSQ], errors="coerce")
    pval = pd.to_numeric(ours[COL_PVALUE], errors="coerce")
    rev = pd.to_numeric(ours[COL_TOTALNET], errors="coerce")
    qty = pd.to_numeric(ours[COL_QUANTITY], errors="coerce")

    rows = ours[ours[COL_KEY].astype(str) == TARGET_KEY]
    if rows.empty:
        ic = extract_itemcode_from_key(ours[COL_KEY])
        rows = ours[ic.astype(str) == TARGET_ITEMCODE]
        if not rows.empty:
            print(f"  NOTE: exact KEY '{TARGET_KEY}' not found; showing all "
                  f"{TARGET_ITEMCODE} grains.")
    if rows.empty:
        print(f"  ** {TARGET_ITEMCODE} not found in ours output_summary. **")
        return

    print(f"  Found {len(rows)} row(s) for {TARGET_ITEMCODE} in ours output_summary:")
    print()
    print(f"  {'KEY':<28} {'Elast':>11} {'RSQ':>7} {'p':>7} {'Rev MSEK':>9} {'Qty':>12}")
    for idx, r in rows.iterrows():
        print(f"  {str(r[COL_KEY])[:28]:<28} "
              f"{e.loc[idx]:>+11.3f} {rsq.loc[idx]:>7.3f} {pval.loc[idx]:>7.3f} "
              f"{rev.loc[idx]/1e6:>9.2f} {qty.loc[idx]:>12,.0f}")
    print()
    print("  NOTE: output_summary has 8 columns only (KEY, TotalNet, Quantity,")
    print("        Correl, RSQ, ADJ_RSQ, ELASTICITY, PVALUE). n_weeks and price")
    print("        variance are NOT here -> scanning model_results.csv below.")
    print()

    print("  Significance under the two gates:")
    for idx, r in rows.iterrows():
        two = bool(is_significant(rsq.loc[idx], pval.loc[idx]))
        four = bool(_full_ib2_significant(e.loc[idx], rsq.loc[idx], pval.loc[idx]))
        print(f"    {str(r[COL_KEY])[:28]:<28} "
              f"helpers(2-cond)={'YES' if two else 'no':<3}  "
              f"IB.2(4-cond)={'YES' if four else 'no'}")
    print("  -> 2-cond YES but 4-cond no = exactly the class the suite mislabels.")
    print()

    mr = _model_results_path(our_path)
    if mr.exists():
        size_mb = mr.stat().st_size / 1e6
        print(f"  Scanning model_results.csv ({size_mb:.0f} MB) for {TARGET_ITEMCODE} "
              f"rows (chunked, memory-safe)...")
        try:
            collected = []
            for chunk in pd.read_csv(mr, chunksize=200_000, low_memory=False):
                m = pd.Series(False, index=chunk.index)
                for col in chunk.columns:
                    cl = str(col).lower()
                    if "key" in cl or "itemcode" in cl or "item code" in cl:
                        m = m | chunk[col].astype(str).str.contains(TARGET_ITEMCODE, na=False)
                if m.any():
                    collected.append(chunk[m])
            if collected:
                hit = pd.concat(collected, ignore_index=True)
                print(f"    matched {len(hit)} row(s) in model_results.csv")
                price_col = next((c for c in hit.columns if "price" in str(c).lower()), None)
                week_col = next((c for c in hit.columns if "week" in str(c).lower()), None)
                key_col = next((c for c in hit.columns if "key" in str(c).lower()), None)
                print(f"    price column: {price_col}")
                print(f"    week column : {week_col}")
                if key_col is not None:
                    exact = hit[hit[key_col].astype(str) == TARGET_KEY]
                    scope = exact if len(exact) else hit
                    label = "exact KEY" if len(exact) else "all MBAS0703 grains"
                    print(f"    reporting on: {label} ({len(scope)} rows)")
                    if week_col is not None:
                        print(f"    n_weeks (distinct): {scope[week_col].nunique()}")
                    if price_col is not None:
                        p = pd.to_numeric(scope[price_col], errors="coerce").dropna()
                        if len(p) > 1:
                            cv = p.std() / p.mean() if p.mean() else float("nan")
                            ratio = (p.max() / p.min()) if p.min() else float("nan")
                            print(f"    price n={len(p)}  mean={p.mean():.3f}  "
                                  f"std={p.std():.3f}  cv={cv:.3f}  "
                                  f"min={p.min():.3f}  max={p.max():.3f}")
                            print(f"    price max/min ratio: {ratio:.2f}x")
            else:
                print(f"    no {TARGET_ITEMCODE} rows in model_results.csv")
        except Exception as ex:
            print(f"    (could not scan model_results.csv: {ex})")
    else:
        print(f"  model_results.csv not present at {mr}")
        print("  -> n_weeks / price variance unavailable; rely on RSQ/p above.")
    print()

    print("  BCG facit lookup:")
    if bcg is None:
        print("    BCG facit not loaded.")
    else:
        be = pd.to_numeric(bcg[COL_ELASTICITY], errors="coerce")
        brows = bcg[bcg[COL_KEY].astype(str) == TARGET_KEY]
        if brows.empty:
            print(f"    {TARGET_KEY} NOT in BCG facit -> NEW KEY (post-2025-06 data).")
            print("    Implication: no BCG reference; the -320 is entirely ours and")
            print("    NOT a drift case (drift requires both sides present).")
        else:
            for bidx, br in brows.iterrows():
                print(f"    BCG {str(br[COL_KEY])[:28]:<28} elast={be.loc[bidx]:>+.3f}")
    print()

    print("  Hypothesis read-out (verdict goes in the session decision):")
    print("    small N (n_weeks < ~30)      -> OLS unstable, fragility expected")
    print("    high price CV / wide min-max  -> log-log slope can explode")
    print("    one extreme week              -> single leverage point dominates")
    print("    none of the above + high RSQ  -> suspect genuine data bug")


# =================================================================================
# SECTION 2 - R2 DRIFT SAMPLING (bit-identical to check 03)
# =================================================================================
def section_drift(ours, bcg):
    section("[2/4] R2 DRIFT SAMPLING (reproduce check 03, seed=42)")

    if bcg is None:
        print("  BCG facit not loaded -> cannot reproduce drift set.")
        return

    o = ours[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET]].copy()
    b = bcg[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE]].copy()
    for c in [COL_ELASTICITY, COL_RSQ, COL_PVALUE]:
        o[c] = pd.to_numeric(o[c], errors="coerce")
        b[c] = pd.to_numeric(b[c], errors="coerce")
    o[COL_TOTALNET] = pd.to_numeric(o[COL_TOTALNET], errors="coerce")

    o = o.rename(columns={COL_ELASTICITY: "elast_ours", COL_RSQ: "rsq_ours",
                          COL_PVALUE: "pval_ours", COL_TOTALNET: "rev_ours"})
    b = b.rename(columns={COL_ELASTICITY: "elast_bcg", COL_RSQ: "rsq_bcg",
                          COL_PVALUE: "pval_bcg"})

    m = o.merge(b, on=COL_KEY, how="inner").dropna(subset=["elast_ours", "elast_bcg"])
    m["delta"] = m["elast_ours"] - m["elast_bcg"]
    m["abs_delta"] = m["delta"].abs()

    drift = m[m["abs_delta"] > DRIFT_HARD_THRESHOLD].copy()
    match = "MATCH" if len(drift) == EXPECTED_DRIFT_COUNT else "DIFFERS - investigate before trusting"
    print(f"  Compared (both present): {fmt_int(len(m))}")
    print(f"  Drift |delta| > {DRIFT_HARD_THRESHOLD}: {len(drift)} KEY "
          f"(check 03 reported {EXPECTED_DRIFT_COUNT} -> {match})")
    print()

    if len(drift) == 0:
        print("  No drift KEY to sample.")
        return

    np.random.seed(SAMPLE_SEED)
    n = min(SAMPLE_N, len(drift))
    pick = np.random.choice(drift.index.values, size=n, replace=False)
    sample = drift.loc[pick].sort_values("abs_delta", ascending=False)

    print(f"  Random sample of {n} drift KEY (seed={SAMPLE_SEED}):")
    print(f"  {'KEY':<28} {'ours_e':>8} {'bcg_e':>8} {'delta':>8} "
          f"{'o_rsq':>6} {'b_rsq':>6} {'o_p':>6} {'b_p':>6} {'revMSEK':>8}")
    for _, r in sample.iterrows():
        print(f"  {str(r[COL_KEY])[:28]:<28} "
              f"{r['elast_ours']:>+8.3f} {r['elast_bcg']:>+8.3f} {r['delta']:>+8.3f} "
              f"{r['rsq_ours']:>6.2f} {r['rsq_bcg']:>6.2f} "
              f"{r['pval_ours']:>6.3f} {r['pval_bcg']:>6.3f} "
              f"{r['rev_ours']/1e6:>8.2f}")
    print()
    print("  Per-KEY classification guidance (verdict goes in the session):")
    print("    drift (c)       : same sign, |ours|<5, delta plausibly from +10mo data")
    print("    weak-signal (c'): sign flip near zero / low RSQ, thin group (IB.10)")
    print("    artefact (a)    : |ours| extreme (>5/>10) or physically impossible")


# =================================================================================
# SECTION 3 - SIGNIFICANCE-DEFINITION IMPACT (the real decision input)
# =================================================================================
def section_sig_impact(ours):
    section("[3/4] SIGNIFICANCE DEFINITION IMPACT (helpers 2-cond vs IB.2 4-cond)")

    e = pd.to_numeric(ours[COL_ELASTICITY], errors="coerce")
    rsq = pd.to_numeric(ours[COL_RSQ], errors="coerce")
    pval = pd.to_numeric(ours[COL_PVALUE], errors="coerce")
    rev = pd.to_numeric(ours[COL_TOTALNET], errors="coerce")

    two = is_significant(rsq, pval)
    two = two.fillna(False) if hasattr(two, "fillna") else pd.Series(two).fillna(False)
    four = _full_ib2_significant(e, rsq, pval).fillna(False)

    n_two = int(two.sum())
    n_four = int(four.sum())
    flip_mask = two & (~four)
    n_flip = int(flip_mask.sum())

    print(f"  Sig under helpers 2-cond (RSQ>=0.5 & p<=0.2):        {n_two}")
    print(f"  Sig under IB.2 4-cond (+ elast<0 & elast>-10):       {n_four}")
    print(f"  KEY currently 'sig' that IB.2 would REJECT:          {n_flip}")
    print()

    if n_flip:
        flipped = ours[flip_mask].copy()
        fe = e[flip_mask]
        frev = rev[flip_mask]
        rej_pos = int((fe >= 0).sum())
        rej_floor = int((fe <= OUTLIER_NEGATIVE_FLOOR).sum())
        print(f"  Reason breakdown of the {n_flip} rejected:")
        print(f"    elast >= 0 (positive 'significant'): {rej_pos}")
        print(f"    elast <= -10 (absurd magnitude):     {rej_floor}")
        print()
        order = fe.abs().sort_values(ascending=False).index
        show = flipped.reindex(order).head(25)
        print(f"  Rejected KEY (top 25 by |elast|):")
        print(f"  {'KEY':<30} {'elast':>11} {'rev MSEK':>9}")
        for idx, r in show.iterrows():
            rv = rev.loc[idx]
            print(f"  {str(r[COL_KEY])[:30]:<30} {e.loc[idx]:>+11.3f} "
                  f"{(rv/1e6 if pd.notna(rv) else float('nan')):>9.2f}")
        if len(flipped) > 25:
            print(f"  ... and {len(flipped) - 25} more")
    else:
        print("  No KEY change status -> 2-cond and 4-cond agree on this dataset.")
    print()
    print("  DECISION INPUT: correcting is_significant() to the IB.2 four-condition")
    print("  gate removes MBAS0703 AND every other sign/magnitude-implausible 'sig'")
    print(f"  KEY in one change. Blast radius = {n_flip} KEY across checks")
    print("  02/07/08/09 that import this helper.")


# =================================================================================
# SECTION 4 - CHECK 07 RE-RUN WITHOUT MBAS0703
# =================================================================================
def section_leverage(ours):
    section("[4/4] CHECK 07 RE-RUN: Top-50 leverage WITHOUT MBAS0703 (in-memory)")

    df = ours[[COL_KEY, COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET]].copy()
    for c in [COL_ELASTICITY, COL_RSQ, COL_PVALUE, COL_TOTALNET]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["sig2"] = is_significant(df[COL_RSQ], df[COL_PVALUE]).fillna(False)
    df["sig4"] = _full_ib2_significant(
        df[COL_ELASTICITY], df[COL_RSQ], df[COL_PVALUE]).fillna(False)
    df["abs_elast"] = df[COL_ELASTICITY].abs()
    df["leverage"] = df[COL_TOTALNET] * df["abs_elast"]

    def top_set(frame, sig_col):
        v = frame[frame[sig_col] & frame["leverage"].notna()]
        t = v.nlargest(TOP_LEVERAGE_N, "leverage").copy().reset_index(drop=True)
        t["rank"] = t.index + 1
        return t

    orig = top_set(df, "sig2")
    df_nomb = df[df[COL_KEY].astype(str) != TARGET_KEY]
    new2 = top_set(df_nomb, "sig2")
    new4 = top_set(df, "sig4")

    tr = orig[orig[COL_KEY].astype(str) == TARGET_KEY]
    print(f"  MBAS0703 in ORIGINAL Top-50 (2-cond): "
          f"{'rank ' + str(int(tr['rank'].iloc[0])) if len(tr) else 'not in top 50'}")
    print()

    entrants2 = set(new2[COL_KEY]) - set(orig[COL_KEY])
    print(f"  Removing MBAS0703 (2-cond): {len(entrants2)} KEY enter Top-50:")
    if entrants2:
        for _, r in new2[new2[COL_KEY].isin(entrants2)].iterrows():
            print(f"    + rank {int(r['rank']):>2}  {str(r[COL_KEY])[:30]:<30} "
                  f"rev {r[COL_TOTALNET]/1e6:>7.2f} MSEK  elast {r[COL_ELASTICITY]:>+8.3f}")
        print("    -> a high-rev plausible-elast entrant means MBAS0703 masked a")
        print("       genuinely relevant case (check 07 PASS was soft).")
    else:
        print("    -> none; MBAS0703 occupied one slot, no masking.")
    print()

    entrants4 = set(new4[COL_KEY]) - set(orig[COL_KEY])
    print(f"  Under corrected IB.2 4-cond gate: {len(entrants4)} KEY differ from")
    print(f"  the original Top-50 (this is the real post-fix Top-50).")
    print()
    print(f"  Corrected (4-cond) Top-10 leverage:")
    print(f"  {'rank':>4} {'KEY':<30} {'revMSEK':>8} {'elast':>9} {'levMSEK':>9}")
    for _, r in new4.head(10).iterrows():
        print(f"  {int(r['rank']):>4} {str(r[COL_KEY])[:30]:<30} "
              f"{r[COL_TOTALNET]/1e6:>8.2f} {r[COL_ELASTICITY]:>+9.3f} "
              f"{r['leverage']/1e6:>9.2f}")


# =================================================================================
# DRIVER
# =================================================================================
def _run_investigation(output_summary_path=None):
    section("INVESTIGATE OUTLIERS AND DRIFT - deep-dive (READ-ONLY)")
    print(f"Run timestamp: {now_iso()}")
    print()

    subsection("[0] Resolving inputs")
    our_path, source_label = resolve_our_output_summary(output_summary_path)
    print(f"  Ours: {source_label} -> {our_path}")
    print(f"  Hash: {file_hash_short(our_path)}")
    ours = pd.read_excel(our_path)
    print(f"  ours shape: {ours.shape}")
    print(f"  ours columns: {list(ours.columns)}")
    print()

    if BCG_FACIT_OUTPUT_SUMMARY.exists():
        bcg = pd.read_excel(BCG_FACIT_OUTPUT_SUMMARY)
        print(f"  BCG facit: {BCG_FACIT_OUTPUT_SUMMARY}")
        print(f"  bcg shape: {bcg.shape}")
    else:
        bcg = None
        print(f"  ** BCG facit not found at {BCG_FACIT_OUTPUT_SUMMARY}")
        print(f"     Drift section (2) will be skipped.")
    print()

    section_mbas(ours, bcg, our_path)
    section_drift(ours, bcg)
    section_sig_impact(ours)
    section_leverage(ours)

    section("END OF INVESTIGATION - no files were modified (read-only)")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Investigate MBAS0703, drift, sig-definition, leverage.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_investigation(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"10_investigate_outliers_and_drift_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "investigate_outliers_and_drift.py", log_text)
    print()
    print(f"  Receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())

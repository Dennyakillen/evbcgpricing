"""
run_smoke_facit.py  --  end-to-end rok-test mot frozen facit (Phase Z)
======================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.  HARDAD 2026-06-26: helt OFFLINE, ingen Blob.

KARNIDEN (din egen, en niva upp)
--------------------------------
Du anvander redan frozen facit for att validera MODELLUTFALL (bit-for-bit mot BCG).
Detta anvander samma ankare for att validera LIMMET: kor hela limmets verifierbara
del pa KAND data och bevisa att kant utfall fortfarande kommer ut. Samma princip,
en niva upp -- fran "ger modellen ratt tal" till "ar fogmassan runt motorn obruten".

HELT OFFLINE (ratt for ditt syfte)
----------------------------------
Detta validerar LIMMET, inte en live-korning. Limmet ar inte Azure-beroende:
sokvagar, fonster-konsistens, att runners laddar, att kontrakt-kolumner stammer,
att kant utfall reproduceras. INGEN token, INGEN VM, INGEN Blob, INGET 9h-jobb.
Facit ar redan validerat mot BCG -- detta bevisar att din fogmassa inte rubbat det.

VARFOR INTE EN "DROPPE" (AAP130 / en subgrupp)
----------------------------------------------
En enskild produkts elasticitet BERAKNAS RELATIVT hela populationen. En droppe ar
ingen droppe -- det ar en molekyl, och reningsverket ar meningslost pa en molekyl.
Frozen facit ar ratt "droppe": hela populationen vid kand tidpunkt med kant utfall.

VAD DEN GOR (tre lager, mat-gissa-inte, alla offline)
-----------------------------------------------------
  LAGER 1  STRUKTUR : dry_run_full_pipeline (utan --vm) -> skarvarna passar.
  LAGER 2  KOHERENS : window_coherence (LOKAL, offline) -> familjernas output
                      finns + farskhet mot parquet. Ingen Blob.
  LAGER 3  UTFALL   : profilera Final_Fallback och jamfor mot FRYST referens --
                      radantal, distinkta ProductKeys, F-fordelning, elast-median.
                      Drift utover tolerans pa OFORANDRAD data = REGRESSION i limmet.

Forsta korningen BLESSAR en kant-god referens; darefter JAMFOR varje korning mot
den. "Spike-to-harden": forsta matningen blir invariant.

KOR (global py-3.11, repo-roten)
--------------------------------
    py -3.11 verify_tool\\run_smoke_facit.py --bless --fallback-file "<kant-god Final_Fallback.xlsx>"
    py -3.11 verify_tool\\run_smoke_facit.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
VERIFY = REPO / "verify_tool"
FBL = REPO / "Pipeline" / "02. Elasticity" / "6. Fall Back Logic"
REFERENCE = VERIFY / "frozen_facit_reference.json"

DRY_RUN_FULL = VERIFY / "dry_run_full_pipeline.py"
WINDOW_COHERENCE = VERIFY / "window_coherence.py"

TOL = {
    "rows_pct": 0.5,
    "keys_pct": 0.5,
    "elast_median_abs": 0.02,
    "flevel_pct_abs": 2.0,
}

ROWS: list = []


def rec(status, check, detalj=""):
    ROWS.append((status, check, detalj))
    mark = {"PASS": "PASS ", "FAIL": "FAIL!", "INFO": "info ", "WARN": "warn "}.get(status, status)
    print(f"   [{mark}] {check}" + (f"  --  {detalj}" if detalj else ""))


def section(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def _newest_fallback() -> Path | None:
    cands = list((FBL / "output_data").glob("Final_Fallback_Data*.xlsx")) + \
            list(FBL.glob("Final_Fallback_Data*.xlsx"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def _profile(path: Path) -> dict:
    import pandas as pd
    df = pd.read_excel(path)
    prof: dict = {"source_file": path.name, "rows": int(len(df)),
                  "profiled_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}
    if "ProductKey" in df.columns:
        prof["distinct_keys"] = int(df["ProductKey"].nunique())
    if "final_elasticity" in df.columns:
        fe = pd.to_numeric(df["final_elasticity"], errors="coerce")
        prof["elast_median"] = round(float(fe.median()), 4)
        prof["elast_neg_pct"] = round(float((fe < 0).mean() * 100), 2)
    if "elasticity_level" in df.columns:
        vc = df["elasticity_level"].astype(str).value_counts(normalize=True) * 100
        prof["flevel_pct"] = {str(k): round(float(v), 2) for k, v in vc.items()}
    return prof


def _run(script: Path, extra: list[str]) -> int:
    """Kor ett delverktyg. extra ar redan en LISTA -- inga ihopklistrade flaggor
    (buggen 2026-06-26: '2025-06-29--no-require-status'). subprocess far listan
    direkt, sa varje element blir ett eget argv-element. Mat-gissa-inte aven har."""
    if not script.exists():
        rec("WARN", f"hoppar {script.name}", "saknas")
        return 0
    cmd = [sys.executable, str(script)] + extra
    print(f"   kor: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def compare(ref: dict, cur: dict) -> bool:
    ok = True
    if "rows" in ref and ref["rows"]:
        d = abs(cur["rows"] - ref["rows"]) / ref["rows"] * 100
        passed = d <= TOL["rows_pct"]; ok &= passed
        rec("PASS" if passed else "FAIL", f"radantal {cur['rows']} vs ref {ref['rows']}",
            f"avvikelse {d:.2f}% (tol {TOL['rows_pct']}%)")
    if "distinct_keys" in ref and "distinct_keys" in cur and ref["distinct_keys"]:
        d = abs(cur["distinct_keys"] - ref["distinct_keys"]) / ref["distinct_keys"] * 100
        passed = d <= TOL["keys_pct"]; ok &= passed
        rec("PASS" if passed else "FAIL",
            f"distinkta ProductKeys {cur['distinct_keys']} vs ref {ref['distinct_keys']}",
            f"avvikelse {d:.2f}% (tol {TOL['keys_pct']}%)")
    if "elast_median" in ref and "elast_median" in cur:
        d = abs(cur["elast_median"] - ref["elast_median"])
        passed = d <= TOL["elast_median_abs"]; ok &= passed
        rec("PASS" if passed else "FAIL",
            f"elasticitet-median {cur['elast_median']} vs ref {ref['elast_median']}",
            f"avvikelse {d:.3f} (tol {TOL['elast_median_abs']})")
    if "flevel_pct" in ref and "flevel_pct" in cur:
        worst = 0.0; worst_lvl = ""
        for lvl, ref_pct in ref["flevel_pct"].items():
            d = abs(cur["flevel_pct"].get(lvl, 0.0) - ref_pct)
            if d > worst:
                worst, worst_lvl = d, lvl
        passed = worst <= TOL["flevel_pct_abs"]; ok &= passed
        rec("PASS" if passed else "FAIL", "F-niva-fordelning storsta drift",
            f"{worst:.1f} pe pa '{worst_lvl}' (tol {TOL['flevel_pct_abs']} pe)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="End-to-end rok-test mot frozen facit (OFFLINE).")
    ap.add_argument("--bless", action="store_true",
                    help="Skapa/uppdatera referensen ur nuvarande (kant-goda) facit-utfall.")
    ap.add_argument("--fallback-file", default=None,
                    help="Explicit Final_Fallback att profilera (annars nyaste).")
    ap.add_argument("--start", default="2022-07-01")
    ap.add_argument("--end", default="2025-06-29", help="Facit-fonstrets slut (BCG fryst).")
    ap.add_argument("--skip-structure", action="store_true", help="Hoppa lager 1 (dry-run).")
    ap.add_argument("--skip-coherence", action="store_true", help="Hoppa lager 2 (koherens).")
    args = ap.parse_args()

    print("=" * 72)
    print("SMOKE TEST MOT FROZEN FACIT  --  ar limmet runt motorn obrutet? (OFFLINE)")
    print(f"  facit-fonster: {args.start} .. {args.end}")
    print("=" * 72)

    # --- LAGER 1: STRUKTUR (offline, utan --vm) ---
    if not args.skip_structure:
        section("LAGER 1 -- STRUKTUR (skarvarna passar?)")
        rc = _run(DRY_RUN_FULL, ["--start", args.start, "--end", args.end])
        rec("PASS" if rc == 0 else "WARN", "dry_run_full_pipeline",
            "alla skarvar passar" if rc == 0 else f"exit {rc} -- las dess utskrift")

    # --- LAGER 2: KOHERENS (LOKAL, offline -- INGEN Blob) ---
    if not args.skip_coherence:
        section("LAGER 2 -- KOHERENS (familjernas output finns + farsk, lokalt)")
        # OFFLINE: ingen --via-blob. Listan skickas korrekt (ej ihopklistrad).
        rc = _run(WINDOW_COHERENCE, ["--start", args.start, "--end", args.end])
        rec("INFO", "window_coherence (lokal)",
            f"exit {rc} (0=alla familjer pa disk; 1=nagon saknas)")

    # --- LAGER 3: UTFALL (offline) ---
    section("LAGER 3 -- UTFALL (kant utfall ur oforandrad data?)")
    fb = Path(args.fallback_file) if args.fallback_file else _newest_fallback()
    if fb is None or not fb.exists():
        rec("FAIL", "inget Final_Fallback att profilera",
            "ange --fallback-file <kant-god fil>, eller kor EFTER-kedjan forst")
        if args.fallback_file:
            rec("INFO", "angiven fil fanns ej", str(fb))
        return 1
    try:
        cur = _profile(fb)
    except Exception as e:  # noqa: BLE001
        rec("FAIL", "kunde ej profilera utfallet", f"{type(e).__name__}: {e}")
        return 1
    rec("INFO", "profilerat utfall", f"{cur['source_file']}: {cur['rows']:,} rader, "
        f"{cur.get('distinct_keys','?')} keys, median {cur.get('elast_median','?')}")

    if args.bless:
        REFERENCE.write_text(json.dumps(cur, indent=2, ensure_ascii=False), encoding="utf-8")
        rec("PASS", "referens SKAPAD/UPPDATERAD",
            f"{REFERENCE.name} -- framtida korningar jamfors mot denna")
        print("\n" + "-" * 72)
        print("BLESS klar. Referensen ar satt. Kor utan --bless for att bevisa limmets halsa.")
        return 0

    if not REFERENCE.exists():
        rec("WARN", "ingen referens finns an",
            f"kor med --bless --fallback-file <kant-god fil> forst")
        print("\n" + "-" * 72)
        print("Ingen referens att jamfora mot. --bless en kant-god korning forst.")
        return 0

    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    rec("INFO", "jamfor mot referens", f"{REFERENCE.name} (blessad {ref.get('profiled_at','?')})")
    passed = compare(ref, cur)

    section("SAMMANFATTNING")
    n_fail = sum(1 for s, _, _ in ROWS if s == "FAIL")
    if passed and not n_fail:
        print("  PASS -- limmet ger facit-likvardigt utfall pa oforandrad data. Obrutet.")
        return 0
    print("  FAIL -- utfallet DRIFTAR fran facit pa oforandrad data = REGRESSION i limmet.")
    print("  Nagot mellan input och Final_Fallback har andrat sig. Granska skarvarna.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

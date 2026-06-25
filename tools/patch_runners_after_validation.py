#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_runners_after_validation.py -- additiva runner-fixar fran all_chain_validator
===================================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.

Tva ADDITIVA fixar pa de tre MOTOR-runnarna (cluster/site/bundle). BCG-kod oror --
detta ror BARA orkestrerings-runnarna. Idempotent: kor om = ingen effekt.
Enradsankare (LB.35). Python, ej PowerShell (LB.72).

-------------------------------------------------------------------------------
FIX 1  (LB.79 -- ALLA tre runners)  [klart fall, ingen bedomning]
-------------------------------------------------------------------------------
feature_selection skriver per-KEY xlsx till output/model/automl/* + model_objects
men skapar INTE mapparna sjalv -> RayTaskError(OSError) om output/model rensats fore
korning (FAS 18 hade dem kvar -> syntes ej; dok upp forst nar maj-output rensades).
Fix: mkdir -p i preflight_remote (efter output-arkiveringen, fore launch).

-------------------------------------------------------------------------------
FIX 2  (EXPECTED_KEYS -- BARA cluster)  [ett bedomningsval -- se nedan]
-------------------------------------------------------------------------------
cluster EXPECTED_KEYS = 4180 ar FEL LAGER: 4180 ar step-5-BLEND-talet, inte
modellstegen 1-4. Kallan sager det sjalv (measure_cluster_values.py rad 90 +
run_cluster_model rad 98). Faktiskt modell-tal (vaxande) = 3791.

  Site 6624 och bundle 125 ar LEGITIMA baslinjer (site visar korrekt drift
  6604, bundle matchar) -> de rors INTE.

Valt: cluster -> None. Det HAVDAR inget falskt mal; verify rapporterar faktiskt
antal (exakt vad runnerns egen kommentar rad 101 kallar den arliga defaulten:
"None until measured -> verify reports the count without asserting a guessed target").

  >> JENS BEDOMNING: vill du istallet ha en DRIFT-BASLINJE (frozen-facit) for
  >> cluster, satt EXPECTED_KEYS = 3812 (frusna cluster-facit, LB.16) har -- da
  >> visar validatorn drift 3791 vs 3812 (IB.6/IB.11) istallet for att tiga.
  >> En rads andring. None ar den sakra, icke-gissande defaulten.

KOR (global py-3.11, fran repo-roten C:\\Projekt\\BCG):
    py -3.11 tools\\patch_runners_after_validation.py --dry-run   # visa, gor inget
    py -3.11 tools\\patch_runners_after_validation.py             # applicera
Verifiera efterat:
    py -3.11 verify_tool\\probes\\all_chain_validator.py
  -> automl-REVIEW:arna ska bli PASS (sonden bevisar sin egen fix).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
RUNNERS = REPO / "orchestration" / "runners"
FAMILY_RUNNERS = {
    "cluster": RUNNERS / "run_cluster_model.py",
    "site":    RUNNERS / "run_site_model.py",
    "bundle":  RUNNERS / "run_bundle_model.py",
}

# --- FIX 1: automl-mkdir ---
ANCHOR = 'log.info("Existing remote output archived (frozen-baseline, Way A).")'
AUTOML_MARK = "LB.79: automl"                      # idempotens-markor
AUTOML_BLOCK = (
    "\n"
    "    # LB.79 (additiv): feature_selection skriver per-KEY xlsx till\n"
    "    # output/model/automl/* + model_objects men skapar INTE mapparna\n"
    "    # -> RayTaskError(OSError) om output/model rensats. mkdir -p ar\n"
    "    # idempotent. BCG-kod oror; detta ar runnerns ansvar.\n"
    "    _model_dir = os.path.dirname(REMOTE_OUTPUT)\n"
    '    ssh_run(cfg, f"mkdir -p {_model_dir}/automl/details {_model_dir}/automl/results "\n'
    '                 f"{_model_dir}/model_objects", retries=2)\n'
    '    log.info("LB.79: automl/details, automl/results, model_objects sakerstallda pa VM.")'
)

# --- FIX 2: cluster EXPECTED_KEYS (fel lager) ---
CLUSTER_NEW_LINE = (
    "EXPECTED_KEYS  = None          "
    "# 4180 var STEG-5-BLEND-talet (FEL LAGER); modellstegen 1-4 = 3791 (vaxande). "
    "None = rapportera utan att havda fel mal. Satt 3812 (frusen facit, LB.16) for drift-baslinje. "
    "(all_chain_validator-fynd 2026-06-25)"
)


def read_text(p: Path) -> tuple[str, str]:
    """Defensiv lasning (encoding-noten): runnarna ar utf-8, men prova cp1252/utf-16
    sa vi aldrig manglar. Skrivning sker alltid utf-8 (ren .py-kalla)."""
    for enc in ("utf-8", "cp1252", "utf-16"):
        try:
            return p.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"kunde inte avkoda {p}")


def fix_automl(text: str) -> tuple[str, str]:
    if AUTOML_MARK in text:
        return text, "redan patchad (LB.79) -- hoppar"
    if ANCHOR not in text:
        return text, "ANKARE SAKNAS (preflight_remote-arkivraden hittades ej) -- granska manuellt"
    return text.replace(ANCHOR, ANCHOR + AUTOML_BLOCK, 1), "automl-mkdir infogad i preflight_remote"


def fix_expected_keys_cluster(text: str) -> tuple[str, str]:
    if re.search(r"^EXPECTED_KEYS\s*=\s*None", text, re.M):
        return text, "redan None -- hoppar"
    if not re.search(r"^EXPECTED_KEYS\s*=\s*4180", text, re.M):
        return text, "EXPECTED_KEYS=4180 hittades ej (redan andrad?) -- granska manuellt"
    return re.sub(r"^EXPECTED_KEYS\s*=\s*4180.*$", CLUSTER_NEW_LINE, text, count=1, flags=re.M), \
        "EXPECTED_KEYS 4180 -> None (fel-lager-talet borttaget)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Additiva runner-fixar fran all_chain_validator.")
    ap.add_argument("--dry-run", action="store_true", help="Visa vad som skulle andras, skriv inget.")
    args = ap.parse_args()

    print("=" * 74)
    print("PATCH RUNNERS (efter validering) -- FIX1 automl (alla 3) + FIX2 EXPECTED_KEYS (cluster)")
    print(f"  {'DRY-RUN' if args.dry_run else 'APPLICERAR'}   repo={REPO}")
    print("=" * 74)

    changed = 0
    for fam, p in FAMILY_RUNNERS.items():
        if not p.exists():
            print(f"[{fam}] SAKNAS: {p}")
            continue
        text, enc = read_text(p)
        orig = text

        text, msg1 = fix_automl(text)
        print(f"[{fam}] ({enc})  FIX1 automl       : {msg1}")
        if fam == "cluster":
            text, msg2 = fix_expected_keys_cluster(text)
            print(f"[{fam}]        FIX2 EXPECTED_KEYS: {msg2}")

        if text != orig:
            if args.dry_run:
                print(f"[{fam}]        -> dry-run: skulle skriva ({len(text) - len(orig):+d} tecken)")
            else:
                p.write_text(text, encoding="utf-8")   # utf-8, ingen BOM
                print(f"[{fam}]        -> SKRIVEN")
            changed += 1
        else:
            print(f"[{fam}]        -> oforandrad")

    print("-" * 74)
    print(f"{'(dry-run) ' if args.dry_run else ''}Klart. {changed} fil(er) "
          f"{'skulle andras' if args.dry_run else 'andrade'}.")
    print("Verifiera: py -3.11 verify_tool\\probes\\all_chain_validator.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

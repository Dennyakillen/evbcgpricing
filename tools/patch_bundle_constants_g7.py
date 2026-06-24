#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_bundle_constants_g7.py  --  G7 env-override for bundle constants.py (mapp 5)
=================================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.

VARFOR (matt 2026-06-24 via bundle_model_output_sond + datumlas-sond):
  Bundle-modellen (mapp 5) producerade ingen output pa maj-data. Rotorsak:
  constants.py rad 16-18 har HARDKODADE datum (END_DATE='2025-06-29'), medan
  model.py L482 och regular_price.py L224 filtrerar:
      df[(week >= START_DATE) & (week < END_DATE2)]
  -> all maj-data kapas bort, data_for_model slutar 2025-06-23, model.py far
  noll relevanta grupper ("Finished in 6.57s", ingen output).

  Bundle-RUNNERN injicerar redan korrekt (run_bundle_model L150):
      export BCG_START_DATE=... BCG_END_DATE=... && ...
  men constants.py LASTE aldrig env:en. Cluster + Site G7-patchades i FAS 13;
  Bundle missades. Detta speglar EXAKT cluster constants.py:s G7-block.

FIX (additiv, BCG-logik orord -- bara datumkallan parametriseras):
  - import os + datetime/timedelta (om saknas)
  - START_DATE = os.environ.get("BCG_START_DATE", "2022-07-01")   # BCG fryst default
  - END_DATE   = os.environ.get("BCG_END_DATE",   "2025-06-29")   # BCG fryst default
  - END_DATE2  HARLEDS = END_DATE + 1 dag (datetime)  -- ALDRIG hardkodad separat (G7-regel)
  Tomma env-vars => BCG:s frysta fonster reproduceras BIT-IDENTISKT (vagen tillbaka
  till facit). SPECIAL_WEEKS lamnas (historiska, ligger inom fonstret anda).

KORS PA VM (dar constants.py bor, dar modellen laser):
    (bygg lokalt, scp, kor)  -- se foljebrev
    ~/bcg/cluster/.venv/bin/python ~/patch_bundle_constants_g7.py            # dry-run
    ~/bcg/cluster/.venv/bin/python ~/patch_bundle_constants_g7.py --apply

Backup skapas alltid fore andring (LB.24).
"""
from __future__ import annotations
import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path

CONST = Path("/home/azureuser/bcg/bundle/code/constants.py")
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Det nya G7-blocket som ersatter de tre hardkodade raderna (speglar cluster).
G7_BLOCK = '''# ===========================================================================
# DATE WINDOW  (G7 fix, FAS Z -- Jens Palmo). Speglar cluster/site constants.py.
# ---------------------------------------------------------------------------
# Env-overridable sa en farsk korning INTE kraver kodandring -- satt slutdatum o kor.
#   BCG_START_DATE  fast ankare for vaxande fonstret (default 2022-07-01)
#   BCG_END_DATE    sista dag att inkludera (default = BCG:s frysta 2025-06-29)
# Tomma env-vars = BCG:s original-fonster reproduceras EXAKT (vagen tillbaka till facit).
# Bundle-runnern (run_bundle_model L150) exporterar dessa pa VM fore launch.
# END_DATE2 HARLEDS alltid fran END_DATE (+1 dag) -- aldrig hardkodad separat (G7-regel).
START_DATE = os.environ.get("BCG_START_DATE", "2022-07-01")
END_DATE = os.environ.get("BCG_END_DATE", "2025-06-29")
END_DATE2 = (datetime.strptime(END_DATE, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")'''


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="G7 env-override for bundle constants.py.")
    ap.add_argument("--apply", action="store_true", help="Genomfor (utan: dry-run).")
    ap.add_argument("--path", default=str(CONST), help="Sokvag till bundle constants.py.")
    args = ap.parse_args()

    p = Path(args.path)
    print("=" * 70)
    print("PATCH BUNDLE CONSTANTS G7 -- env-override (speglar cluster)")
    print("=" * 70)

    if not p.exists():
        log("ERROR", f"constants.py saknas: {p}")
        return 1

    txt = p.read_text(encoding="utf-8")
    lines = txt.splitlines()

    # --- hitta de tre hardkodade raderna ---
    idx_start = idx_end = idx_end2 = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"START_DATE\s*=\s*['\"]2022-07-01['\"]", s):
            idx_start = i
        elif re.match(r"END_DATE\s*=\s*['\"]2025-06-29['\"]", s):
            idx_end = i
        elif re.match(r"END_DATE2\s*=\s*['\"]2025-06-30['\"]", s):
            idx_end2 = i

    if idx_start is None or idx_end is None or idx_end2 is None:
        log("STOPP", f"hittade inte alla tre hardkodade rader (start={idx_start}, end={idx_end}, end2={idx_end2}).")
        log("INFO", "Kanske redan patchad? Visar nuvarande START/END_DATE-rader:")
        for i, ln in enumerate(lines, 1):
            if re.search(r"START_DATE|END_DATE", ln):
                print(f"  L{i}: {ln.strip()}")
        return 2

    # de tre ska ligga i foljd (16,17,18) -- verifiera
    if not (idx_end == idx_start + 1 and idx_end2 == idx_start + 2):
        log("VARN", f"raderna ligger ej i foljd (start={idx_start+1}, end={idx_end+1}, end2={idx_end2+1}) -- patchar anda var for sig.")

    # --- behover 'import os' och datetime/timedelta ---
    has_os = any(re.match(r"\s*import os\b", l) for l in lines)
    has_dt = any(re.search(r"from datetime import.*datetime", l) for l in lines)
    has_td = any(re.search(r"from datetime import.*timedelta", l) for l in lines)

    log("FORE", f"START_DATE  (L{idx_start+1}): {lines[idx_start].strip()}")
    log("FORE", f"END_DATE    (L{idx_end+1}): {lines[idx_end].strip()}")
    log("FORE", f"END_DATE2   (L{idx_end2+1}): {lines[idx_end2].strip()}")
    log("INFO", f"import os finns: {has_os}   datetime: {has_dt}   timedelta: {has_td}")

    # --- bygg ny fil ---
    new_lines = list(lines)
    # ersatt de tre raderna med G7-blocket (pa START_DATE-raden), ta bort de andra tva
    new_lines[idx_start] = G7_BLOCK
    # ta bort END_DATE + END_DATE2-raderna (hogre index forst sa numreringen haller)
    for j in sorted([idx_end, idx_end2], reverse=True):
        del new_lines[j]

    # lagg till imports hogst upp om de saknas
    header_inserts = []
    if not has_os:
        header_inserts.append("import os")
    if not (has_dt and has_td):
        header_inserts.append("from datetime import datetime, timedelta")
    if header_inserts:
        # infoga efter ev. forsta import-rad, annars langst upp
        insert_at = 0
        for i, l in enumerate(new_lines):
            if l.startswith("import ") or l.startswith("from "):
                insert_at = i
                break
        new_lines[insert_at:insert_at] = header_inserts
        log("INFO", f"infogar imports: {header_inserts}")

    new_txt = "\n".join(new_lines) + "\n"

    print("\n  EFTER (nytt G7-block):")
    for l in G7_BLOCK.splitlines():
        print(f"    {l}")

    if not args.apply:
        print("\n  (dry-run -- kor med --apply)")
        print("=" * 70)
        return 0

    # backup + skriv
    bak = p.with_suffix(f".py.bak-pre-g7-{STAMP}")
    shutil.copy2(p, bak)
    log("BACKUP", str(bak))
    p.write_text(new_txt, encoding="utf-8")
    log("SKRIVET", str(p))

    # R7: las tillbaka, verifiera env-override + default-repro
    import importlib.util
    log("R7", "verifierar att modulen importerar + datum stammer...")
    # test 1: utan env (BCG fryst)
    for k in ("BCG_START_DATE", "BCG_END_DATE"):
        os.environ.pop(k, None)
    spec = importlib.util.spec_from_file_location("bundle_const_test", p)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        ok_default = (m.START_DATE == "2022-07-01" and m.END_DATE == "2025-06-29"
                      and m.END_DATE2 == "2025-06-30")
        log("R7", f"utan env: START={m.START_DATE} END={m.END_DATE} END2={m.END_DATE2}  "
                  f"{'OK (BCG fryst repro)' if ok_default else 'GRANSKA'}")
    except Exception as e:
        log("R7", f"import-fel utan env: {e}")
        ok_default = False

    # test 2: med maj-env
    os.environ["BCG_START_DATE"] = "2022-07-01"
    os.environ["BCG_END_DATE"] = "2026-05-31"
    spec2 = importlib.util.spec_from_file_location("bundle_const_test2", p)
    m2 = importlib.util.module_from_spec(spec2)
    try:
        spec2.loader.exec_module(m2)
        ok_maj = (m2.END_DATE == "2026-05-31" and m2.END_DATE2 == "2026-06-01")
        log("R7", f"med maj-env: END={m2.END_DATE} END2={m2.END_DATE2}  "
                  f"{'OK (maj genomslag)' if ok_maj else 'GRANSKA'}")
    except Exception as e:
        log("R7", f"import-fel med env: {e}")
        ok_maj = False
    finally:
        for k in ("BCG_START_DATE", "BCG_END_DATE"):
            os.environ.pop(k, None)

    print("\n  VERDICT: " + ("RATT -- env-override fungerar, default reproducerar BCG fryst."
                             if (ok_default and ok_maj) else "GRANSKA -- se R7 ovan + backup."))
    print("=" * 70)
    return 0 if (ok_default and ok_maj) else 3


if __name__ == "__main__":
    sys.exit(main())

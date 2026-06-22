#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# after_chain_probe.py -- Sond 6: kartlagg "Efter"-kedjan (lokala eftersteg)
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Forfattare: Claude-radgivare. Sessionsdatum 2026-06-22.
#
# SYFTE (komplement till sond 4 infrastructure_map + sond 5 contract_integrity)
#   Sond 4/5 validerade MOTORN (orkestrering + kontrakt). DEN HAR sonden
#   kartlagger "EFTER -- resultat och affarssignal": de lokala efterstegen
#   som kors UTANFOR Azure (xlwings/COM finns ej pa Linux, LB.44) och som en
#   framtida run_after.py ska orkestrera.
#
#   Den svarar pa de fragor som blockerar run_after.py:
#     1. Vilka filer i verify_tool/run ar PRODUKTIONssteg (i kedjan) vs
#        VALIDERINGsverktyg (vid sidan om)?
#     2. Vad LASER varje produktionssteg (input + kalla)? Vad SKRIVER det?
#     3. For run_step6: vilka input ar LIVE GROWING vs FRUSNA (FD.11/14/15)?
#        -- avgor vad PULL fran Blob ska skriva over med farsk data.
#     4. Hur ANROPAS varje steg (argument, subprocess)?
#     5. Hanger BEROENDEKEDJAN ihop? (steg N:s output = steg N+1:s input)
#
#   AVSIKTLIGT STATISK: laser kod (AST + monstermatchning), kor den ALDRIG.
#   Ingen az-token, ingen VM, ingen Blob. Mat, gissa inte -- ur kallkod.
#
# BINAR DOM (i sond-anda): for varje produktionssteg, ar dess input-kalla
#   identifierad och dess output fangad av nasta steg? Luckor = REVIEW.
#
# ANVANDNING (global Python 3.11, ingen token):
#   py -3.11 after_chain_probe.py                       # mot verify_tool/run
#   py -3.11 after_chain_probe.py --root <run-mapp>
#
# BEROENDEN: endast standardbibliotek (ast, re, pathlib, argparse).
# =====================================================================
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------
# Klassificering: vilka run-filer ar PRODUKTIONssteg i Efter-kedjan, vilka
# ar valideringsverktyg/andra faser. Harlett ur filernas docstrings + roll.
# (run_after.py finns inte an -- den ar det denna sond informerar.)
# ---------------------------------------------------------------------
PRODUCTION_CHAIN = {
    # ordning : (fil, roll)
    1: ("run_step6.py",            "STEP 6 -- fallback-vav (F1-F7) -> Final_Fallback_Data"),
    2: ("build_r12_for_model.py",  "STEP 7 -- R12 model feed -> Model_Feed (matbar prismodell)"),
}
# Vid sidan om kedjan (ej produktionssteg):
SIDE_TOOLS = {
    "fallback_blend.py":   "VALIDERING -- fristaende step-5-replikering (bevis-sparet, ej produktion)",
    "run_bundle_dataprep.py": "ANNAN FAS -- bundle SQL data-prep (FORE-motorn, ej Efter)",
}


def _parse(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        for enc in ("cp1252", "utf-16", "latin-1"):
            try:
                src = path.read_text(encoding=enc); break
            except Exception:
                continue
        else:
            return None, ""
    try:
        return ast.parse(src), src
    except SyntaxError as e:
        print(f"  [varning] kunde inte parsa {path.name}: {e}")
        return None, src


# ---------------------------------------------------------------------
# Extraktorer (monstermatchning -- robustare an AST for path/glob-strangar)
# ---------------------------------------------------------------------
def extract_argparse(src: str) -> list[str]:
    """Vilka --argument tar steget? (hur det anropas)"""
    return sorted(set(re.findall(r'add_argument\(\s*["\'](--[a-z0-9-]+)["\']', src)))


def extract_reads(src: str) -> list[str]:
    """Vad laser steget? (read_excel/read_csv-mal + glob-monster for input)"""
    reads = []
    for m in re.findall(r'(?:read_excel|read_csv)\([^)]*?([A-Za-z_]\w*)', src):
        reads.append(m)
    # glob-monster (filnamn steget letar efter)
    for m in re.findall(r'glob\([^)]*?["\']([^"\']*\*[^"\']*)["\']', src):
        reads.append(f"glob:{m}")
    for m in re.findall(r'["\'](\w*Final_Fallback_Data\*?[^"\']*)["\']', src):
        reads.append(m)
    return sorted(set(reads))


def extract_writes(src: str) -> list[str]:
    """Vad skriver steget? (to_excel/to_csv-mal + namngivna output-filer)"""
    writes = []
    for m in re.findall(r'(?:to_excel|to_csv)\(\s*([^,)]+)', src):
        writes.append(m.strip().strip('"\'')[:60])
    for m in re.findall(r'["\'](\w*(?:Model_Feed|Final_Fallback|FACT_)\w*[^"\']*)["\']', src):
        writes.append(m)
    return sorted(set(writes))


def extract_placements(src: str) -> list[dict]:
    """For run_step6: parsa PLACEMENTS-listan -- label + kind (LIVE/FROZEN).
    Detta ar nyckeln: vilka input ar farska vs frusna."""
    placements = []
    # Hitta varje {...} block i PLACEMENTS med label + kind
    for block in re.findall(r'\{[^{}]*?"label"[^{}]*?\}', src, re.DOTALL):
        label = re.search(r'"label":\s*"([^"]+)"', block)
        kind  = re.search(r'"kind":\s*"([^"]+)"', block)
        fd    = re.search(r'"fd":\s*"([^"]+)"', block)
        if label:
            placements.append({
                "label": label.group(1),
                "kind": kind.group(1) if kind else "?",
                "fd": fd.group(1) if fd else "-",
            })
    # Aven ALREADY-listan (redan pa plats)
    for block in re.findall(r'\{[^{}]*?"label"[^{}]*?"path"[^{}]*?\}', src, re.DOTALL):
        label = re.search(r'"label":\s*"([^"]+)"', block)
        kind  = re.search(r'"kind":\s*"([^"]+)"', block)
        if label and not any(p["label"] == label.group(1) for p in placements):
            placements.append({"label": label.group(1),
                               "kind": kind.group(1) if kind else "?", "fd": "-"})
    return placements


def extract_subprocess(src: str) -> bool:
    """Anropar steget ett annat skript via subprocess? (orkestrerings-monster)"""
    return "subprocess.run" in src


# ---------------------------------------------------------------------
# Analys + dom
# ---------------------------------------------------------------------
def analyze_step(path: Path) -> dict:
    tree, src = _parse(path)
    return {
        "name": path.name,
        "args": extract_argparse(src),
        "reads": extract_reads(src),
        "writes": extract_writes(src),
        "placements": extract_placements(src) if "PLACEMENTS" in src else [],
        "subprocess": extract_subprocess(src),
        "src_len": len(src),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sond 6: kartlagg Efter-kedjans in/ut/ordning (statisk, tokenfri).")
    ap.add_argument("--root", default=None, help="verify_tool/run-mapp (auto om utelamnad).")
    args = ap.parse_args()

    if args.root:
        root = Path(args.root)
    else:
        here = Path(__file__).resolve().parent
        cand = [Path.cwd() / "verify_tool" / "run",
                here.parent / "run",                       # om sonden ligger i probes/
                Path(r"C:\Projekt\BCG\verify_tool\run")]
        root = next((c for c in cand if c.exists()), None)
        if root is None:
            print("Hittade ingen verify_tool/run-mapp. Ange med --root <sokvag>.")
            return 1
    root = root.resolve()
    print(f"Sond 6 -- Efter-kedjans karta")
    print(f"Rot: {root}\n")

    # ---- Produktionskedjan i ordning ----
    print("=" * 72)
    print("PRODUKTIONSKEDJA (Efter -- i ordning run_after.py ska kora)")
    print("=" * 72)
    prev_writes = []
    chain_ok = True
    for order in sorted(PRODUCTION_CHAIN):
        fname, roll = PRODUCTION_CHAIN[order]
        p = root / fname
        if not p.exists():
            print(f"\n[{order}] {fname} -- SAKNAS i {root}  (REVIEW)")
            chain_ok = False
            continue
        a = analyze_step(p)
        print(f"\n[{order}] {fname}")
        print(f"     roll:    {roll}")
        print(f"     anrop:   {('--'+', --'.join(x.lstrip('-') for x in a['args'])) if a['args'] else '(inga argument)'}")
        if a["subprocess"]:
            print(f"     KOR:     annat skript via subprocess (orkestrerar Fall_Back_Logic.py)")
        if a["placements"]:
            print(f"     INPUT-PLACERING (live vs fryst -- PULL skriver over de LIVE):")
            for pl in a["placements"]:
                live = "LIVE" in pl["kind"].upper() or "GROWING" in pl["kind"].upper()
                tag = "FARSK -> PULL fran Blob" if live else f"FRUSEN ({pl['fd']}) -> ror ej"
                print(f"        - {pl['label']:<38} [{pl['kind']:<16}] {tag}")
        if a["reads"]:
            print(f"     laser:   {', '.join(a['reads'][:6])}")
        if a["writes"]:
            print(f"     skriver: {', '.join(a['writes'][:6])}")

        # Beroendekontroll: laser detta steg nagot foregaende steg skrev?
        if order > 1:
            linked = any("Final_Fallback" in r for r in a["reads"]) or \
                     any("Final_Fallback" in w for w in prev_writes)
            if linked:
                print(f"     KEDJA:   OK -- laser foregaende stegs output (Final_Fallback_Data)")
            else:
                print(f"     KEDJA:   REVIEW -- ingen tydlig koppling till steg {order-1}:s output")
                chain_ok = False
        prev_writes = a["writes"]

    # ---- Sidoverktyg (ej produktion) ----
    print("\n" + "=" * 72)
    print("VID SIDAN OM KEDJAN (ej produktionssteg -- ska EJ vavas in)")
    print("=" * 72)
    for fname, roll in SIDE_TOOLS.items():
        p = root / fname
        status = "finns" if p.exists() else "saknas"
        print(f"  {fname:<26} [{status}]  {roll}")

    # ---- PULL/PUSH-checklista for run_after.py ----
    print("\n" + "=" * 72)
    print("CHECKLISTA FOR run_after.py (harledd ur kedjan ovan)")
    print("=" * 72)
    print("""  PULL  : ladda ner motorns LIVE-output fran Blob (fonster-run_id) ->
          placera pa run_step6:s LIVE-destinationer (cluster growing + site).
          De FRUSNA placeringarna (FD.11/14/15) ror PULL inte.
  STEP 6: subprocess run_step6.py (preflightar, placerar, vaver, verifierar R7).
  STEP 7: subprocess build_r12_for_model.py --tx <growing-csv>
          (auto-hittar senaste Final_Fallback_Data -> Model_Feed).
  PUSH  : ladda upp Final_Fallback_Data + Model_Feed till Blob (samma run_id);
          uppdatera statusfil: step6 + build_r12 -> gron, finalize().
  OBS   : blob.py saknar download_outputs() -- den maste byggas for PULL.
  OBS   : utfallet bar tre FRUSNA las (FD.11/14/15). provenance-kvittot
          marker det REVIEW -- run_after bor rapportera, ej dolja.""")

    print("\n" + "=" * 72)
    print(f"DOM: {'PASS -- kedjan komplett och sparbar' if chain_ok else 'REVIEW -- se luckor ovan'}")
    print("=" * 72)
    return 0 if chain_ok else 2


if __name__ == "__main__":
    sys.exit(main())

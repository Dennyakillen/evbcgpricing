#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_3_dataprep_provenance.py  --  SOND 3: VARFÖR skiljer maj-CSV från april?
===============================================================================
FRÅGAN den svarar: var i data_prep-kedjan PRODUCERAS de kolumner som skiljer
(No_of_Sites vs 'No of Sites', den tappade TotalNetXVat)? Detta är ROTORSAKEN,
inte symptomet. Sond 1+2 visar VAD som skiljer; denna visar VARFÖR.

VARFÖR den behövs: 2026-06-23 producerade maj-data_prep (SQL/DuckDB) en CSV
med 'No_of_Sites' (understreck) + utan 'TotalNetXVat', medan april-CSV:n hade
'No of Sites' (mellanslag) + 'TotalNetXVat'. Två olika data_prep-VÄGAR gav
olika kolumnstruktur. Att bara lappa config döljer rotorsaken -- nästa
data_prep kan divergera igen. Denna sond letar upp var namnen/kolumnerna
sätts i SQL-filer + replicate_dataprep.py, så fixen kan ske VID KÄLLAN.

LETAR (lokalt, i repot -- SQL-prep körs lokalt, ej VM):
  - VAR sätts 'No of Sites' / 'No_of_Sites' (AS-alias i SQL, rename i Python)?
  - VAR skapas/tappas 'TotalNetXVat'?
  - Skiljer sig SQL-prep-vägen (Sweden_Elasticity_Data_Prep_SQL) från den
    väg som matade april (ev. export_b4b_for_model.py i Business_Analytics)?

Detta är NYCKELN till om felet är (a) SQL-prep skriver fel namn, (b) två olika
prep-vägar (BA-export vs SQL-prep) ger olika scheman, eller (c) en kolumn
genuint saknas i en källa.

KÖR (lokalt, py -3.11 -- INGEN VM behövs, läser repo-filer):
    py -3.11 probe_3_dataprep_provenance.py
    py -3.11 probe_3_dataprep_provenance.py --repo "C:\\Projekt\\BCG"

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia). Författare: Claude-rådgivare.
Beroende: std-lib (pathlib, re). Körs lokalt mot repo-träd.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

# Kolumner vars härkomst vi spårar (de som skiljer april/maj enligt sond 1+2)
TRACK = ["No_of_Sites", "No of Sites", "NoofUnits", "TotalNetXVat", "ProductGroupL4Name"]

# Var data_prep-logiken bor (SQL-prep lokalt + ev. BA-export-vägen)
SEARCH_DIRS = [
    "Pipeline/02. Elasticity/Sweden_Elasticity_Data_Prep_SQL",
    "Pipeline/02. Elasticity/2. Product Cluster Level Models",
    "tools",  # replicate_dataprep.py med _inject_dates + VALIDATIONS-alias
]
# Companion-repo (DW-extraktion) — kan vara april-vägen
COMPANION = r"C:\Projekt\Business_Analytics"

EXTS = {".sql", ".py", ".yml", ".yaml"}


def scan_file(fp: Path, terms: list[str]) -> list[tuple[int, str, str]]:
    """Returnera (radnr, term, rad) för varje träff. Tål kodningsstrul."""
    hits = []
    try:
        text = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return hits
    for i, line in enumerate(text.splitlines(), 1):
        for t in terms:
            if t.lower() in line.lower():
                hits.append((i, t, line.strip()[:160]))
    return hits


def scan_dir(root: Path, label: str, terms: list[str]) -> None:
    print(f"\n{'='*72}\n{label}: {root}\n{'='*72}")
    if not root.exists():
        print(f"  [SAKNAS] {root}")
        return
    any_hit = False
    for fp in sorted(root.rglob("*")):
        if fp.suffix.lower() not in EXTS or not fp.is_file():
            continue
        if any(skip in str(fp) for skip in ("_archive", ".venv", "__pycache__", "node_modules")):
            continue
        hits = scan_file(fp, terms)
        if hits:
            any_hit = True
            rel = fp.relative_to(root) if root in fp.parents else fp.name
            print(f"\n  {rel}:")
            for ln, term, line in hits:
                print(f"    L{ln:<4} [{term}] {line}")
    if not any_hit:
        print("  (inga träffar på spårade kolumner)")


def main() -> int:
    ap = argparse.ArgumentParser(description="SOND 3: data_prep-härkomst för kolumn-divergens.")
    ap.add_argument("--repo", default=r"C:\Projekt\BCG")
    ap.add_argument("--companion", default=COMPANION)
    ap.add_argument("--terms", nargs="*", default=TRACK)
    args = ap.parse_args()

    repo = Path(args.repo)
    print("=" * 72)
    print("SOND 3 -- VARFÖR skiljer maj-CSV från april? (data_prep-härkomst)")
    print(f"Spårar kolumner: {args.terms}")
    print("=" * 72)

    for d in SEARCH_DIRS:
        scan_dir(repo / d, f"REPO/{d}", args.terms)

    # Companion-repo (DW-extraktion) — möjlig april-väg
    comp = Path(args.companion)
    scan_dir(comp, f"COMPANION (DW-extraktion, möjlig april-väg)", args.terms)

    print("\n" + "=" * 72)
    print("TOLKNING (läs träffarna ovan):")
    print("  - Hittar du 'No of Sites' (mellanslag) som AS-alias/rename i EN väg och")
    print("    'No_of_Sites' i en ANNAN -> det är källan till namn-driften.")
    print("  - Om TotalNetXVat skapas i april-vägen men inte i SQL-prep-vägen ->")
    print("    förklarar varför maj-CSV tappade den.")
    print("  - Två prep-vägar (BA-export vs SQL-prep) med olika scheman = rotorsaken.")
    print("  FIX VID KÄLLAN: normalisera namnet/kolumnen i SQL-prep så maj-CSV matchar")
    print("  april-schemat, ELLER (additivt, snabbare) gör config tolerant för båda.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())

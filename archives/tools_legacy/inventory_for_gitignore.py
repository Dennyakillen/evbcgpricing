#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventory_for_gitignore.py  --  READ-ONLY: kartlägg alla data-/config-filer i BCG-repot för att
                                 fatta ett faktabaserat .gitignore-beslut (arkitektur vs output).

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB), med AI-rådgivaren.

VARFÖR
    .gitignore byggd på filändelse (*.csv, *.xlsx) kan inte skilja en KURERAD parameter
    (transform_control_TT.csv, kluster-mappning -- "receptet") från GENERERAD output
    (data_for_model.csv, output_summary.xlsx -- "maten"). Ändelsen avslöjar inte rollen;
    sökväg + ursprung gör det. Detta script listar varje fil med storlek och en HEURISTISK
    klassning så vi ser vad som är vad innan vi skriver reglerna. (LB.15: ett kartläggningsscript
    slår tio fil-frågor.)

VAD
    Skannar roten + Pipeline/ + Elasticity/ efter .csv/.xlsx/.xls/.yml/.yaml/.parquet.
    Per fil: relativ sökväg, storlek, ändringsdatum, och en GISSAD klass:
        [ARKITEKTUR?]  -- ser ut som kurerad parameter/config/control (kandidat FÖR Git)
        [OUTPUT?]      -- ser ut som genererad output (kandidat MOT Git)
        [TUNG]         -- > storleksgräns; oavsett klass troligen MOT Git
        [?]            -- oklar; kräver ditt öga
    Heuristiken är ett FÖRSLAG. Du har sista ordet -- den finns för att göra listan läsbar.

    Skriver INGENTING utom rapporten (default stdout; --out sparar till fil).
    Öppnar aldrig filinnehåll -- bara os.stat-metadata. Hydrerar därför inte OneDrive-stubbar.

KÖR (PowerShell, valfri venv -- inga beroenden utöver stdlib):
    cd "C:\\Projekt\\BCG"
    python inventory_for_gitignore.py 2>&1 | Tee-Object -FilePath gitignore_inventory.txt
    # eller spara direkt:
    python inventory_for_gitignore.py --out gitignore_inventory.txt
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Encoding-guard (PS 5.1 / cp1252 -- BCG-sökvägar har å/ä/ö). LB.11.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# Filtyper vi bryr oss om för .gitignore-beslutet.
DATA_EXT = {".csv", ".xlsx", ".xls", ".parquet"}
CONFIG_EXT = {".yml", ".yaml"}

# Mappar vars hela underträd hoppas över (rena artefakter, aldrig till Git).
SKIP_SEGMENTS = {".venv", "venv", "env", "__pycache__", ".git", ".ipynb_checkpoints",
                 "model objects", "automl", "details", "ray_session", "node_modules"}

# Storleksgräns (DEFAULT): över denna är filen "TUNG" oavsett klass. Override med --heavy-mb.
HEAVY_MB = 5.0

# --- Heuristik: namn-/sökvägsmönster ----------------------------------------------------------
# Ser ut som KURERAD arkitektur (handgjord parameter, control, mappning) -> kandidat FÖR Git.
ARCH_HINTS = (
    "control_file", "control_files", "transform_control", "baseline_control",
    "reference", "mapping", "inscope", "in_scope", "cluster", "seed",
    "date_to_month", "item_description", "config",
)
# Ser ut som GENERERAD output -> kandidat MOT Git.
OUTPUT_HINTS = (
    "data_for_model", "data_original", "model_results", "model_summary",
    "output_summary", "blended_output", "final_model", "regular_price",
    "ivc_sweden", "weekly_model_data", "all_x_for_models", "finalized_x_for_models",
    "_log", "automl",
)
# Sökvägssegment som starkt indikerar genererat.
OUTPUT_PATH_SEGMENTS = ("output", "results", "model")


def log(msg: str = "") -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def classify(rel: Path, size_mb: float, heavy_mb: float) -> str:
    name = rel.name.lower()
    parts = [p.lower() for p in rel.parts]
    ext = rel.suffix.lower()

    if ext in CONFIG_EXT:
        return "ARKITEKTUR?"  # .yml/.yaml = nästan alltid config = recept

    in_output_path = any(seg in parts for seg in OUTPUT_PATH_SEGMENTS)
    looks_output = any(h in name for h in OUTPUT_HINTS) or in_output_path
    looks_arch = any(h in name for h in ARCH_HINTS)

    if size_mb > heavy_mb:
        return "TUNG"
    if looks_output and not looks_arch:
        return "OUTPUT?"
    if looks_arch and not looks_output:
        return "ARKITEKTUR?"
    if looks_arch and looks_output:
        return "?"  # motstridiga signaler -- kräver ditt öga
    return "?"


def is_skipped(path: Path, root: Path) -> bool:
    try:
        rel_parts = [seg.lower() for seg in path.relative_to(root).parts]
    except ValueError:
        return False
    return any(skip in rel_parts for skip in SKIP_SEGMENTS)


def human(mb: float) -> str:
    if mb >= 1024:
        return f"{mb/1024:7.2f} GB"
    return f"{mb:7.2f} MB"


def main() -> int:
    ap = argparse.ArgumentParser(description="READ-ONLY inventering av data/config för .gitignore-beslut")
    ap.add_argument("--root", default=".", help="Repo-rot (default: aktuell mapp)")
    ap.add_argument("--subdirs", nargs="*", default=["Pipeline", "Elasticity"],
                    help="Underträd att skanna utöver roten (default: Pipeline Elasticity)")
    ap.add_argument("--heavy-mb", type=float, default=HEAVY_MB, help=f"TUNG-gräns i MB (default {HEAVY_MB})")
    ap.add_argument("--out", default=None, help="Spara rapporten till fil (annars stdout)")
    args = ap.parse_args()

    heavy_mb = args.heavy_mb

    root = Path(args.root).resolve()
    if not root.exists():
        log(f"NOT FOUND: {root}")
        return 2

    out_fh = open(args.out, "w", encoding="utf-8") if args.out else None

    def emit(msg: str = "") -> None:
        if out_fh:
            out_fh.write(msg + "\n")
        else:
            log(msg)

    emit(f"# .gitignore-inventering -- {datetime.now():%Y-%m-%d %H:%M}")
    emit(f"# Rot: {root}")
    emit(f"# TUNG-gräns: {heavy_mb} MB")
    emit("#")
    emit("# Klass-förslag (DU har sista ordet):")
    emit("#   ARKITEKTUR? = kurerad parameter/config/control -> kandidat FÖR Git")
    emit("#   OUTPUT?     = genererad output                 -> kandidat MOT Git")
    emit("#   TUNG        = > gräns                          -> troligen MOT Git")
    emit("#   ?           = oklar                            -> kräver ditt öga")
    emit("")

    # Bygg skann-rötter: roten (icke-rekursivt djupt men vi rglob ändå, skip tar hand om brus)
    # + angivna subdirs.
    scan_roots = [root]
    for sd in args.subdirs:
        p = root / sd
        if p.exists():
            scan_roots.append(p)

    seen: set[Path] = set()
    rows: list[tuple[str, float, str, str]] = []  # (klass, size_mb, datum, relpath)

    for sr in scan_roots:
        for p in sr.rglob("*"):
            if not p.is_file():
                continue
            if p in seen:
                continue
            if is_skipped(p, root):
                continue
            ext = p.suffix.lower()
            if ext not in DATA_EXT and ext not in CONFIG_EXT:
                continue
            seen.add(p)
            try:
                st = p.stat()
                size_mb = st.st_size / 1_000_000
                mdate = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")
            except OSError as e:
                rows.append(("?", 0.0, "stat-fel", f"{p.relative_to(root)}  ({e})"))
                continue
            rel = p.relative_to(root)
            rows.append((classify(rel, size_mb, heavy_mb), size_mb, mdate, str(rel)))

    # Sortera: klass-gruppering, sedan storlek fallande.
    order = {"ARKITEKTUR?": 0, "?": 1, "OUTPUT?": 2, "TUNG": 3}
    rows.sort(key=lambda r: (order.get(r[0], 9), -r[1]))

    # Summering per klass.
    from collections import defaultdict
    agg: dict[str, list[float]] = defaultdict(list)
    for klass, mb, _d, _p in rows:
        agg[klass].append(mb)

    emit(f"## Summering ({len(rows)} filer)")
    emit("")
    emit(f"{'Klass':<14}{'Antal':>7}{'Total':>14}")
    emit(f"{'-'*14}{'-'*7}{'-'*14}")
    for klass in ("ARKITEKTUR?", "?", "OUTPUT?", "TUNG"):
        if klass in agg:
            sizes = agg[klass]
            emit(f"{klass:<14}{len(sizes):>7}{human(sum(sizes)):>14}")
    emit("")

    # Detaljlista.
    emit("## Detalj (klass | storlek | ändrad | sökväg)")
    emit("")
    for klass, mb, mdate, rel in rows:
        emit(f"[{klass:<11}] {human(mb)}  {mdate}  {rel}")

    emit("")
    emit("## Nästa steg")
    emit("# Granska [ARKITEKTUR?] -- bekräfta att dessa SKA till Git (recept/parametrar).")
    emit("# Granska [?]          -- avgör fall för fall.")
    emit("# [OUTPUT?]/[TUNG]     -- bekräfta att dessa INTE ska till Git.")
    emit("# Paste:a [ARKITEKTUR?] + [?]-raderna tillbaka sa skriver vi .gitignore mot dem (LB.14).")

    if out_fh:
        out_fh.close()
        log(f"[Saved] rapport -> {args.out}  ({len(rows)} filer)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

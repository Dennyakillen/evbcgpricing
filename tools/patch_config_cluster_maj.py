#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_config_cluster_maj.py -- Vag A fix: make cluster config canonical for SQL-prep schema
============================================================================================
Purpose
    Applies the cluster-maj fix (NEXT_SESSION section 3, vag A) to the cluster
    family's config.yml, with the exact scope proven by source reading 2026-07-01:

      1. cols_to_try : keep ONLY 'No_of_Sites' (underscore = SQL-prep canon),
                       REMOVE the legacy 'No of Sites' candidate.
                       Why: feature_selection.py builds feature combinations
                       straight into the fit with NO intersection against
                       df.columns (lines ~302-311: features = cols_needed +
                       subset). A candidate column absent from the CSV makes
                       every subset containing it reference a non-existent
                       column -- a new crash (or wasted combos) in step 3.

      2. col_type    : ensure BOTH name variants AND TotalNetXVat exist.
                       Harmless by construction: the astype loop iterates the
                       DataFrame's ACTUAL columns (feature_selection.py ~533,
                       'for col in df.drop(DOLLAR,axis=1).columns'), so extra
                       keys are never looked up -- but a df column MISSING
                       from col_type is exactly the KeyError that blocked
                       cluster-maj twice.

    Idempotent: safe to run repeatedly. Only writes when a change is needed;
    creates a timestamped .bak next to the file before writing. Preserves the
    file's own line endings (opens with newline='') and writes UTF-8 without
    BOM (LB.86 class: never edit byte-critical files via editor/console paste).

Upstream   : Pipeline/02. Elasticity/2. Product Cluster Level Models/code/src/config.yml
Downstream : VM copy ~/bcg/cluster/code/src/config.yml (scp AFTER commit -- the
             VM copy is what feature_selection actually reads at run time)
Lessons    : LB.85-class (declare once / derive), LB.86 (script-written, no BOM)
Run        : py -3.11 tools\\patch_config_cluster_maj.py
             py -3.11 tools\\patch_config_cluster_maj.py <alternative-path>   (test mode)
Developer  : Jens Palmo (Senior Business Analyst, Evidensia). Author: Claude advisor.
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_CFG = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\code\src\config.yml")

SPACE_VARIANT = "No of Sites"
CANON_VARIANT = "No_of_Sites"
COL_TYPE_MUST_HAVE = ["No of Sites", "No_of_Sites", "TotalNetXVat"]


def log(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}", flush=True)


def drop_list_item(block: str, item: str) -> str:
    """Remove a quoted item from a YAML inline list body, eating one adjacent comma."""
    q = re.escape(item)
    block = re.sub(r"'" + q + r"'\s*,\s*", "", block)   # item followed by comma
    block = re.sub(r",\s*'" + q + r"'", "", block)      # comma before item (last element)
    block = re.sub(r"'" + q + r"'", "", block)          # lone occurrence
    return block


def main() -> int:
    cfg = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CFG
    if not cfg.exists():
        log("FAIL", f"config not found: {cfg}")
        return 1

    # newline='' -> keep the file's own CRLF/LF verbatim in memory and on write.
    with open(cfg, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    orig = text

    # ---- 1. cols_to_try: exactly the canon variant, never the space variant ----
    m = re.search(r"(cols_to_try\s*:\s*\[)(.*?)(\])", text, flags=re.S)
    if not m:
        log("FAIL", "cols_to_try block not found in config")
        return 1
    body = m.group(2)
    new_body = drop_list_item(body, SPACE_VARIANT)
    if f"'{CANON_VARIANT}'" not in new_body:
        stripped = new_body.rstrip()
        sep = ", " if stripped.strip() else ""
        new_body = stripped + sep + f"'{CANON_VARIANT}'"
        log("PATCH", f"cols_to_try: added '{CANON_VARIANT}' (was missing entirely)")
    if new_body != body:
        text = text[: m.start(2)] + new_body + text[m.end(2):]
        log("PATCH", f"cols_to_try: removed '{SPACE_VARIANT}', kept '{CANON_VARIANT}'")
    else:
        log("OK", "cols_to_try already canonical (underscore only)")

    # ---- 2. col_type: ensure both variants + TotalNetXVat are typed ----
    for key in COL_TYPE_MUST_HAVE:
        pat = re.compile(r"^[ \t]+" + re.escape(key) + r"\s*:\s*'float64'", re.M)
        if pat.search(text):
            log("OK", f"col_type has: {key}")
            continue
        anchor = re.search(r"^col_type\s*:[ \t]*\r?\n", text, re.M)
        if not anchor:
            log("FAIL", "col_type block header not found")
            return 1
        eol = "\r\n" if "\r\n" in text[:200] else "\n"
        insertion = f"    {key} : 'float64'  {eol}"
        text = text[: anchor.end()] + insertion + text[anchor.end():]
        log("PATCH", f"col_type: inserted {key} : 'float64'")

    # ---- 3. Verify final state before touching disk ----
    final_body = re.search(r"cols_to_try\s*:\s*\[(.*?)\]", text, flags=re.S).group(1)
    ok = (
        f"'{SPACE_VARIANT}'" not in final_body
        and f"'{CANON_VARIANT}'" in final_body
        and all(
            re.search(r"^[ \t]+" + re.escape(k) + r"\s*:\s*'float64'", text, re.M)
            for k in COL_TYPE_MUST_HAVE
        )
    )
    if not ok:
        log("FAIL", "post-patch verification failed -- file NOT written")
        return 1

    if text == orig:
        log("OK", "config already fully patched -- nothing to write (idempotent no-op)")
        return 0

    bak = cfg.with_name(cfg.name + f".bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(cfg, bak)
    log("BACKUP", bak.name)
    with open(cfg, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    log("SAVED", f"{cfg} (UTF-8 no BOM, line endings preserved)")
    log("NEXT", "git add + commit, then scp to VM: ~/bcg/cluster/code/src/config.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())

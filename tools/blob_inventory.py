#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blob_inventory.py v0.1.0 -- inventeringssond (read-only) över ett Azure Storage-konto: vilka blobbar finns,
var, hur stora, när ändrade -- och vilka lokala data-/Excel-/parquet-filer som finns i Blob respektive bara lokalt.

Utvecklare: Jens Palmö (Senior Business Analyst).

FRÅGAN DEN BESVARAR
  "Var ligger de operativa filerna (parquet, Excel, CSV) som modellerna behöver, och vad finns bara på min
  disk?" Svaret blir dokumentation för ärvande kollegor (MASTER_DEVOP §1: rådata passerar aldrig repot;
  repot bär koden, Blob bär datan -- då måste repot säga VAR).

UPPSTRÖMS (läser)   `az` CLI (inloggad, PIM aktiv): `az storage container list` + `az storage blob list`
                     med --auth-mode key (LB.67: --auth-mode login ger TYST tomt utan dataroll -- därför
                     räknas 0 blobbar i en container som misstanke, inte som OK). Valfritt: en lokal mapp.
NEDSTRÖMS (matar)   <ut>/BLOB_INVENTORY_<konto>_<datum>.md (sammanfattning), <ut>/blob_inventory_<konto>_<datum>.csv
                     (en rad per blob) och, med --lokal, <ut>/blob_lokal_korsning_<datum>.csv. Avsedd hemvist: docs/ops/
                     i repot, så att ärvande kollegor kan köra om sonden och läsa var datan ligger.
RÖR ALDRIG          Blob (bara list-anrop), lokala filer (bara os.stat), az-kontots aktiva subscription
                     (--subscription skickas per anrop, inget `az account set`).

ICKE-UPPENBARA BESLUT
  - Korsningen lokal<->Blob matchar på (filnamn, storlek i byte): samma namn i olika mappar (model_results.csv)
    skiljs av storleken; lika namn OCH storlek räknas som samma fil. En trunkerad lokal kopia syns därför
    som "bara lokalt" -- det är rätt (P.6: en mätare som godkänner på namn ljuger).
  - --json-dir läser sparade `az storage blob list -o json`-svar i stället för att anropa az: testväg och
    offline-väg (kör az för hand, spara JSON, kör sonden).
  - Avslutskod speglar fyndet (DEVOP §6): 0 = alla containrar listade med minst en blob,
    2 = någon container gav 0 blobbar eller ett az-fel, 1 = fel före listningen.

KÖRNING (PowerShell, efter `az login --scope https://management.core.windows.net//.default` och aktiv PIM)
  python tools\\blob_inventory.py --account evbcgpricinginput --subscription "ev-lz3-ai (SE)" --lokal "C:\\Projekt\\BCG" --ut "docs\\ops"
BEROENDEN: Python 3.11+, az CLI i PATH. Inga paket.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

VERSION = "0.1.0"
TOOL = "blob_inventory.py"
DATA_EXT = {".parquet", ".xlsx", ".xlsm", ".xls", ".csv", ".tgz", ".zip", ".json", ".pkl"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".vscode"}


def say(msg: str = "") -> None:
    print(msg, flush=True)


def mb(n: int) -> str:
    return f"{n / 1048576:,.1f}".replace(",", " ")


def gb(n: int) -> str:
    return f"{n / 1073741824:,.2f}".replace(",", " ")


def az_cmd() -> list[str]:
    exe = shutil.which("az")
    if not exe:
        raise SystemExit("[FEL] az hittas inte i PATH")
    return [exe]


def run_az(args: list[str], timeout: int = 900) -> tuple[int, str, str]:
    cmd = az_cmd() + args + ["-o", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def parse_blobs(container: str, data) -> list[dict]:
    rows = []
    for b in data or []:
        p = b.get("properties") or {}
        cs = p.get("contentSettings") or {}
        size = p.get("contentLength")
        if size is None:
            size = p.get("content_length", 0)
        rows.append({
            "container": container,
            "name": b.get("name", ""),
            "bytes": int(size or 0),
            "last_modified": str(p.get("lastModified") or p.get("last_modified") or "")[:19],
            "content_type": cs.get("contentType") or cs.get("content_type") or "",
            "tier": p.get("blobTier") or p.get("blob_tier") or "",
        })
    return rows


def list_containers(account: str, sub: str | None, auth: str) -> list[str]:
    args = ["storage", "container", "list", "--account-name", account, "--auth-mode", auth]
    if sub:
        args += ["--subscription", sub]
    code, out, err = run_az(args)
    if code != 0:
        raise SystemExit(f"[FEL] az storage container list (kod {code}): {err.strip()[-400:]}")
    return [c.get("name", "") for c in json.loads(out or "[]") if c.get("name")]


def list_blobs(account: str, container: str, sub: str | None, auth: str) -> tuple[list[dict], str]:
    args = ["storage", "blob", "list", "--account-name", account, "--container-name", container,
            "--auth-mode", auth, "--num-results", "*"]
    if sub:
        args += ["--subscription", sub]
    code, out, err = run_az(args)
    if code != 0:
        return [], f"az-fel kod {code}: {err.strip()[-300:]}"
    try:
        return parse_blobs(container, json.loads(out or "[]")), ""
    except json.JSONDecodeError as e:
        return [], f"ogiltig JSON fran az: {e}"


def local_files(root: Path, min_mb: float) -> list[dict]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if p.suffix.lower() in DATA_EXT or size >= min_mb * 1048576:
                out.append({"path": str(p.relative_to(root)).replace("\\", "/"), "name": fn, "bytes": size})
    return out


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    L = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    L += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return L


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog=TOOL, description="Read-only inventering av ett Storage-konto (Blob) + korsning mot lokala filer.")
    ap.add_argument("--account", required=True, help="storage-kontots namn, t.ex. evbcgpricinginput")
    ap.add_argument("--subscription", default=None, help='subscription-namn eller id, t.ex. "ev-lz3-ai (SE)"')
    ap.add_argument("--containers", nargs="*", default=None, help="containrar att lista (standard: alla i kontot)")
    ap.add_argument("--auth-mode", default="key", choices=["key", "login"], help="key (standard, LB.67) eller login")
    ap.add_argument("--lokal", type=Path, default=None, help="lokal mapp att korsa mot Blob (namn + storlek)")
    ap.add_argument("--min-mb", type=float, default=50.0, help="lokala filer >= detta räknas även utan datafiländelse (standard 50)")
    ap.add_argument("--ut", type=Path, default=None, help="utmapp (standard: ./blob_inventory_<konto>_<datum>)")
    ap.add_argument("--json-dir", type=Path, default=None, help="offline/test: läs <container>.json (az -o json) härifrån i stället för att anropa az")
    ap.add_argument("--version", action="version", version=f"{TOOL} {VERSION}")
    a = ap.parse_args(argv)

    today = dt.date.today().isoformat()
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    ut = (a.ut or Path(f"blob_inventory_{a.account}_{today}")).resolve()
    ut.mkdir(parents=True, exist_ok=True)
    say(f"{TOOL} v{VERSION}  konto={a.account}  auth={a.auth_mode}  ut={ut}")

    problems: list[str] = []
    if a.json_dir:
        containers = a.containers or sorted(p.stem for p in a.json_dir.glob("*.json"))
        say(f"  Offline: läser {len(containers)} container-JSON ur {a.json_dir}")
    else:
        code, out, err = run_az(["account", "show"] + (["--subscription", a.subscription] if a.subscription else []))
        if code != 0:
            say(f"[FEL] az account show misslyckades -- kör: az login --scope https://management.core.windows.net//.default  ({err.strip()[-200:]})")
            return 1
        acc = json.loads(out or "{}")
        say(f"  az: inloggad som {acc.get('user', {}).get('name', '?')}, subscription {acc.get('name', '?')} ({str(acc.get('id', ''))[:8]}…)")
        containers = a.containers or list_containers(a.account, a.subscription, a.auth_mode)
        say(f"  Containrar: {', '.join(containers) or '(inga!)'}")
        if not containers:
            problems.append("kontot har inga containrar (eller listningen var tom -- LB.67?)")

    blobs: list[dict] = []
    per_container: dict[str, int] = {}
    for c in containers:
        if a.json_dir:
            f = a.json_dir / f"{c}.json"
            try:
                rows, err = parse_blobs(c, json.loads(f.read_text(encoding="utf-8-sig"))), ""
            except Exception as e:
                rows, err = [], f"kunde inte läsa {f}: {e}"
        else:
            rows, err = list_blobs(a.account, c, a.subscription, a.auth_mode)
        per_container[c] = len(rows)
        if err:
            problems.append(f"{c}: {err}")
            say(f"  [FEL] {c}: {err}")
        elif not rows:
            problems.append(f"{c}: 0 blobbar -- tomt på riktigt eller tyst tomt (LB.67, auth-mode)?")
            say(f"  [OBS] {c}: 0 blobbar (tomt pa riktigt, eller tyst tomt utan dataroll?)")
        else:
            say(f"  [OK] {c}: {len(rows)} blobbar, {gb(sum(r['bytes'] for r in rows))} GB")
        blobs += rows

    # --- blobs.csv ------------------------------------------------------------------------------
    csv_path = ut / f"blob_inventory_{a.account}_{today}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["container", "name", "bytes", "MB", "last_modified", "content_type", "tier"])
        for r in sorted(blobs, key=lambda r: (r["container"], r["name"])):
            w.writerow([r["container"], r["name"], r["bytes"], mb(r["bytes"]), r["last_modified"], r["content_type"], r["tier"]])

    # --- sammanfattning -----------------------------------------------------------------------
    L: list[str] = []
    L.append(f"# BLOB_INVENTORY — `{a.account}` ({today})")
    L.append("")
    L.append(f"*Mätt {stamp} med `{TOOL}` v{VERSION} (read-only, `az storage blob list --auth-mode {a.auth_mode}`). "
             f"Utvecklare: Jens Palmö (Senior Business Analyst). Rådata per blob i `{csv_path.name}` bredvid.*")
    L.append("")
    tot = sum(r["bytes"] for r in blobs)
    L.append(f"**{len(blobs)} blobbar, {gb(tot)} GB, {len(containers)} containrar.** "
             + ("Inga anmärkningar." if not problems else "**Anmärkningar:** " + "; ".join(problems)))
    L.append("")
    L.append("## 1. Per container")
    L.append("")
    rows = []
    for c in containers:
        rs = [r for r in blobs if r["container"] == c]
        last = max((r["last_modified"] for r in rs), default="")
        rows.append([f"`{c}`", len(rs), gb(sum(r["bytes"] for r in rs)), last])
    L += md_table(["Container", "Blobbar", "GB", "Senast ändrad"], rows)
    L.append("")
    L.append("## 2. Per container och första mappnivå")
    L.append("")
    grp: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in blobs:
        parts = r["name"].split("/")
        grp[(r["container"], parts[0] + "/" if len(parts) > 1 else "(rot)")].append(r)
    rows = [[f"`{c}`", f"`{p}`", len(rs), gb(sum(r["bytes"] for r in rs)), max(r["last_modified"] for r in rs)]
            for (c, p), rs in sorted(grp.items(), key=lambda kv: (kv[0][0], -sum(r["bytes"] for r in kv[1])))]
    L += md_table(["Container", "Mapp", "Blobbar", "GB", "Senast ändrad"], rows)
    L.append("")
    L.append("## 3. Per filtyp")
    L.append("")
    ext: dict[str, list[dict]] = defaultdict(list)
    for r in blobs:
        ext[PurePosixPath(r["name"]).suffix.lower() or "(ingen)"].append(r)
    rows = [[f"`{e}`", len(rs), gb(sum(r["bytes"] for r in rs))] for e, rs in sorted(ext.items(), key=lambda kv: -sum(r["bytes"] for r in kv[1]))]
    L += md_table(["Filtyp", "Blobbar", "GB"], rows)
    L.append("")
    L.append("## 4. Operativa filer: alla `.parquet` och `.xlsx`/`.xlsm`")
    L.append("")
    ops = sorted((r for r in blobs if PurePosixPath(r["name"]).suffix.lower() in (".parquet", ".xlsx", ".xlsm")),
                 key=lambda r: (r["container"], r["name"]))
    L += md_table(["Container", "Blob", "MB", "Senast ändrad"], [[f"`{r['container']}`", f"`{r['name']}`", mb(r["bytes"]), r["last_modified"]] for r in ops]) if ops else ["*(inga)*"]
    L.append("")
    L.append("## 5. De 20 största blobbarna")
    L.append("")
    top = sorted(blobs, key=lambda r: -r["bytes"])[:20]
    L += md_table(["Container", "Blob", "MB", "Senast ändrad"], [[f"`{r['container']}`", f"`{r['name']}`", mb(r["bytes"]), r["last_modified"]] for r in top]) if top else ["*(inga)*"]
    L.append("")

    # --- lokal korsning -------------------------------------------------------------------------
    if a.lokal:
        root = a.lokal.resolve()
        loc = local_files(root, a.min_mb)
        key = defaultdict(list)
        for r in blobs:
            key[(PurePosixPath(r["name"]).name, r["bytes"])].append(r)
        in_blob, only_local = [], []
        for f in loc:
            hits = key.get((f["name"], f["bytes"]))
            (in_blob if hits else only_local).append((f, hits or []))
        loc_keys = {(f["name"], f["bytes"]) for f in loc}
        only_blob = [r for r in blobs if (PurePosixPath(r["name"]).name, r["bytes"]) not in loc_keys]
        L.append(f"## 6. Lokal korsning — `{root}` (datafiler: {', '.join(sorted(DATA_EXT))} eller ≥ {a.min_mb:g} MB)")
        L.append("")
        L.append(f"Matchning på filnamn + exakt storlek. Lokala filer: {len(loc)} — i Blob: {len(in_blob)} — "
                 f"bara lokalt: {len(only_local)} ({gb(sum(f['bytes'] for f, _ in only_local))} GB). "
                 f"Blobbar utan lokal motsvarighet: {len(only_blob)} ({gb(sum(r['bytes'] for r in only_blob))} GB).")
        L.append("")
        L.append("### 6a. Bara lokalt (störst först)")
        L.append("")
        rows = [[f"`{f['path']}`", mb(f["bytes"])] for f, _ in sorted(only_local, key=lambda t: -t[0]["bytes"])]
        L += md_table(["Lokal fil", "MB"], rows) if rows else ["*(inga)*"]
        L.append("")
        L.append("### 6b. Finns i Blob (samma namn och storlek)")
        L.append("")
        rows = [[f"`{f['path']}`", mb(f["bytes"]), "; ".join(f"`{h['container']}/{h['name']}`" for h in hits)]
                for f, hits in sorted(in_blob, key=lambda t: -t[0]["bytes"])]
        L += md_table(["Lokal fil", "MB", "Blob"], rows) if rows else ["*(inga)*"]
        L.append("")
        L.append("### 6c. Bara i Blob (ingen lokal fil med samma namn och storlek) — antal per container/mapp")
        L.append("")
        g2: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in only_blob:
            parts = r["name"].split("/")
            g2[(r["container"], parts[0] + "/" if len(parts) > 1 else "(rot)")].append(r)
        rows = [[f"`{c}`", f"`{p}`", len(rs), gb(sum(r["bytes"] for r in rs))] for (c, p), rs in sorted(g2.items())]
        L += md_table(["Container", "Mapp", "Blobbar", "GB"], rows) if rows else ["*(inga)*"]
        L.append("")
        kors_path = ut / f"blob_lokal_korsning_{today}.csv"
        with open(kors_path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["lokal_fil", "bytes", "MB", "i_blob", "blob"])
            for f, hits in sorted(in_blob + only_local, key=lambda t: t[0]["path"]):
                w.writerow([f["path"], f["bytes"], mb(f["bytes"]), "ja" if hits else "nej", "; ".join(f"{h['container']}/{h['name']}" for h in hits)])

    L.append("---")
    L.append(f"*Avslutskod {2 if problems else 0}. 0 = alla containrar listade med minst en blob; 2 = anmärkning ovan (LB.67: "
             f"`--auth-mode login` utan dataroll ger tyst tomt — en tom container är en fråga, inte ett faktum).*")
    md_path = ut / f"BLOB_INVENTORY_{a.account}_{today}.md"
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    say("")
    say(f"  Skrivet: {md_path}")
    say(f"  Skrivet: {csv_path}" + (f"  +  {kors_path}" if a.lokal else ""))
    say(f"  {len(blobs)} blobbar, {gb(tot)} GB" + (f"; {len(problems)} anmarkning(ar)" if problems else "; inga anmarkningar"))
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

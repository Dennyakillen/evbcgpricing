#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spegel_fran_blob.py  --  återställer BCG-repots DATA ur Azure Blob till en klon: facit ur BCG-originalet och den
indata som inget skript skapar. Steg 2 efter `install.py` (se README, "Ny dator"). Torrkörning är default.

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Version: 0.1.0 (2026-10-21)

VARFÖR
    Git bär metoden, Blob bär datan (FUNKTIONSKARTA, LB.66). Det mesta en körning behöver hämtar kedjan själv ur
    Blobs kanoniska struktur (input/, pipeline/00_frozen_facit/, output/). Två saker gör den inte:
      1. FACIT ur BCG-originalet som validatorerna jämför mot (proof_chain, output_rationality, provenance) --
         byte-exakt kopia i pipeline/00_frozen_facit/bcg_original/ (uppladdad 2026-10-21, sha256 per fil).
      2. HANDGJORD INDATA och mallar som inget skript skapar (BCG-leveranser, DW-dimensionssnapshot, Excel-mallar)
         -- de ligger i spegeln spegel/bcg_2026-10-20/ (ögonblicksbild av Jens dator, 2026-10-20), och spegelns
         eget manifest (spegel/bcg_2026-10-20/_spegel/SPEGEL_MANIFEST_*.csv) säger vilken roll varje fil har.
    Det här verktyget hämtar dem till rätt plats i klonen och verifierar varje fil mot sha256 i blob-metadata.

PROFILER (--profil, kan upprepas; default: facit + indata)
    facit   pipeline/00_frozen_facit/bcg_original/02. Elasticity/**  ->  verify_tool/facit/BCG_orginal_V2_New/02. Elasticity/**
            + spegelns _extern/bcg_inputs/**                           ->  verify_tool/facit/bcg_inputs/**
            (~140 MB; validatorerna läser dem via BCG_FACIT_DIR, default verify_tool/facit)
    indata  manifestrader med roll INPUT/MALL/FACIT utanför arkiv      ->  samma repo-relativa sökväg (~1,9 GB)
    allt    hela spegeln (alla manifestrader med spegel=ja)            ->  samma sökväg (~22 GB) -- datorns ögonblicksbild

SÄKERHET
    - Skriver aldrig över en befintlig fil med annat innehåll: KONFLIKT och hoppas. Med --skriv-over flyttas den
      befintliga först till <fil>.fore-aterstallning-<tid> (ingenting raderas).
    - Laddar ned till <fil>.part, verifierar storlek + sha256 mot blob-metadata, byter namn först därefter.
    - Nyckelläge (LB.67): PRICINGMODEL_KEY om satt, annars `az storage account keys list` (kräver az login + roll på
      lagringskontot). Nyckeln skrivs aldrig ut.
    - Kvitto: <repo>/workspace/aterstallning/ATERSTALLNING_<tid>.csv + .md.

AVSLUTSKOD  0 = allt NEDLADDAD/HOPPAD (torr: PLAN utan problem); 2 = KONFLIKT/FEL (se kvittot); 1 = fel före start
ANVÄNDNING (PowerShell, i klonens rot, efter install.py)
    .\\.venv\\Scripts\\python.exe tools\\spegel\\spegel_fran_blob.py                 # torr: visar plan
    .\\.venv\\Scripts\\python.exe tools\\spegel\\spegel_fran_blob.py --kor           # hämtar facit + indata
    .\\.venv\\Scripts\\python.exe tools\\spegel\\spegel_fran_blob.py --profil facit --kor
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TOOL, VERSION = "spegel_fran_blob.py", "0.1.0"
DEFAULT_ACCOUNT = os.environ.get("PRICINGMODEL_STORAGE", "evbcgpricinginput")
DEFAULT_RG = os.environ.get("PRICINGMODEL_RG", "ev-openai-swce-rg-test")
DEFAULT_SUB = os.environ.get("PRICINGMODEL_SUBSCRIPTION", "ev-lz3-ai (SE)")
FACIT_CONTAINER = "pipeline"
FACIT_PREFIX = "00_frozen_facit/bcg_original/02. Elasticity/"
FACIT_DEST = Path("verify_tool") / "facit" / "BCG_orginal_V2_New" / "02. Elasticity"
EXTERN_MAP = {"_extern/bcg_inputs/": Path("verify_tool") / "facit" / "bcg_inputs"}
INDATA_ROLLER = {"INPUT", "MALL", "FACIT"}
ARKIV_ROTTER = ("_ATT_RADERA/", "archives/")
PROBLEM = {"KONFLIKT", "FEL", "SAKNAS-I-BLOB", "UTAN-SHA"}


def say(m: str = "") -> None:
    try:
        print(m, flush=True)
    except UnicodeEncodeError:
        print(m.encode("ascii", "replace").decode("ascii"), flush=True)


def gb(n: int) -> str:
    return f"{n / 1073741824:,.2f}".replace(",", " ")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def account_key(account: str, rg: str, sub: str) -> str:
    k = os.environ.get("PRICINGMODEL_KEY", "").strip()
    if k:
        return k
    az = shutil.which("az")
    if not az:
        raise SystemExit("[FEL] az hittas inte och PRICINGMODEL_KEY är inte satt")
    r = subprocess.run([az, "storage", "account", "keys", "list", "--account-name", account, "--resource-group", rg,
                        "--subscription", sub, "--query", "[0].value", "-o", "tsv"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("[FEL] kunde inte hämta kontonyckel via az -- kör az login --scope https://management.core.windows.net//.default "
                         "och aktivera din roll på lagringskontot (PIM), eller sätt $env:PRICINGMODEL_KEY")
    return r.stdout.strip()


def read_manifest_text(text: str) -> list[dict]:
    delim = ";" if text[:4096].count(";") >= text[:4096].count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delim))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog=TOOL, description="Återställ facit och indata ur Azure Blob till en klon av BCG-repot.")
    ap.add_argument("--repo", type=Path, default=Path("."), help="klonens rot (default: aktuell mapp)")
    ap.add_argument("--profil", action="append", choices=["facit", "indata", "allt"], default=None)
    ap.add_argument("--filter", action="append", default=[], help="bara sökvägar som matchar detta glob-mönster (kan upprepas)")
    ap.add_argument("--kor", action="store_true", help="hämta på riktigt (utan: torrkörning)")
    ap.add_argument("--skriv-over", action="store_true", help="flytta undan befintlig fil med annat innehåll och hämta (raderar inget)")
    ap.add_argument("--konto", default=DEFAULT_ACCOUNT)
    ap.add_argument("--rg", default=DEFAULT_RG)
    ap.add_argument("--subscription", default=DEFAULT_SUB)
    ap.add_argument("--spegel-container", default="spegel")
    ap.add_argument("--spegel-prefix", default="bcg_2026-10-20")
    ap.add_argument("--manifest", type=Path, default=None, help="lokal manifest-CSV i stället för spegelns _spegel/")
    ap.add_argument("--tradar", type=int, default=4)
    ap.add_argument("--endpoint", default=None, help="test: annan blob-endpoint (Azurite)")
    ap.add_argument("--version", action="version", version=f"{TOOL} {VERSION}")
    a = ap.parse_args(argv)

    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        say("[FEL] azure-storage-blob saknas -- kör med klonens .venv (.\\.venv\\Scripts\\python.exe), installerad av install.py")
        return 1

    repo = a.repo.resolve()
    if not (repo / "install.py").is_file():
        say(f"[FEL] {repo} ser inte ut som BCG-repots rot (install.py saknas) -- kör från klonens rot eller ange --repo")
        return 1
    profiler = set(a.profil or ["facit", "indata"])
    mode = "KOR" if a.kor else "TORR"
    now = dt.datetime.now()
    say(f"{TOOL} v{VERSION}  läge={mode}  profiler={','.join(sorted(profiler))}  repo={repo}")

    if a.endpoint:
        svc = BlobServiceClient(account_url=a.endpoint, credential={"account_name": a.konto, "account_key": os.environ.get("PRICINGMODEL_KEY", "")},
                                connection_timeout=60, read_timeout=600)
    else:
        svc = BlobServiceClient(account_url=f"https://{a.konto}.blob.core.windows.net",
                                credential=account_key(a.konto, a.rg, a.subscription), connection_timeout=60, read_timeout=600)

    # ---- plan: (container, blob, dest_rel, bytes, sha) ---------------------------------------------
    plan: list[dict] = []
    if "facit" in profiler:
        cc = svc.get_container_client(FACIT_CONTAINER)
        n0 = len(plan)
        for b in cc.list_blobs(name_starts_with=FACIT_PREFIX, include=["metadata"]):
            rel = b.name[len(FACIT_PREFIX):]
            plan.append({"container": FACIT_CONTAINER, "blob": b.name, "dest": (FACIT_DEST / rel).as_posix(), "bytes": int(b.size),
                         "sha": ((b.metadata or {}).get("sha256") or "").upper(), "kalla": "facit"})
        say(f"  facit: {len(plan) - n0} filer i {FACIT_CONTAINER}/{FACIT_PREFIX}")
        if len(plan) == n0:
            say("  [OBS] inga facit-blobbar hittades -- fel konto/behörighet (LB.67: tyst tomt utan dataroll)?")

    need_manifest = True  # facit behöver manifestet för extern-facit (bcg_inputs); indata/allt för urvalet
    rows: list[dict] = []
    if need_manifest:
        if a.manifest:
            raw = a.manifest.read_bytes()
            src = str(a.manifest)
        else:
            sc = svc.get_container_client(a.spegel_container)
            cands = [b for b in sc.list_blobs(name_starts_with=f"{a.spegel_prefix}/_spegel/SPEGEL_MANIFEST_")]
            if not cands:
                if profiler & {"indata", "allt"}:
                    say(f"[FEL] inget manifest i {a.spegel_container}/{a.spegel_prefix}/_spegel/ -- ange --manifest")
                    return 1
                say("  [OBS] inget spegelmanifest -- extern-facit (bcg_inputs) hoppas")
                cands = None
            if cands:
                newest = max(cands, key=lambda b: b.last_modified)
                raw = sc.get_blob_client(newest.name).download_blob().readall()
                src = f"{a.spegel_container}/{newest.name}"
            else:
                raw, src = b"", "(inget)"
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", "replace")
        rows = read_manifest_text(text)
        say(f"  manifest: {len(rows)} rader ur {src}")

    def blob_for(r: dict) -> str:
        return (r.get("blob_namn") or "").strip() or f"{a.spegel_prefix}/{r['sokvag']}"

    for r in rows:
        if (r.get("spegel") or "").strip().lower() != "ja":
            continue
        sok = r["sokvag"]
        try:
            size = int(str(r.get("bytes", "0")).replace(" ", "").replace(" ", "") or 0)
        except ValueError:
            size = -1
        dest = None
        for pre, target in EXTERN_MAP.items():
            if sok.startswith(pre):
                dest = (target / sok[len(pre):]).as_posix()
                break
        is_extern = sok.startswith("_extern/")
        if is_extern:
            if dest is None or not ({"facit", "allt"} & profiler):
                continue
            src_kind = "facit (extern)"
        elif "allt" in profiler:
            dest, src_kind = sok, "allt"
        elif "indata" in profiler and (r.get("roll") or "").strip().upper() in INDATA_ROLLER \
                and not sok.startswith(ARKIV_ROTTER) and (r.get("kedja") or "").strip().upper() != "ARKIV":
            dest, src_kind = sok, f"indata ({r.get('roll')})"
        else:
            continue
        plan.append({"container": a.spegel_container, "blob": blob_for(r), "dest": dest, "bytes": size,
                     "sha": (r.get("sha256") or "").strip().upper(), "kalla": src_kind})
    if a.filter:
        plan = [p for p in plan if any(fnmatch.fnmatch(p["dest"].lower(), f.replace("\\", "/").lower()) for f in a.filter)]
    seen, uniq = set(), []
    for p in plan:
        if p["dest"] not in seen:
            seen.add(p["dest"])
            uniq.append(p)
    plan = sorted(uniq, key=lambda p: (p["bytes"], p["dest"]))
    tot = sum(max(p["bytes"], 0) for p in plan)
    say(f"  plan: {len(plan)} filer, {gb(tot)} GB")

    # ---- per fil ---------------------------------------------------------------------------------
    kv_dir = repo / "workspace" / "aterstallning"
    kv_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d_%H%M%S")
    kv_csv = kv_dir / f"ATERSTALLNING_{stamp}_{mode}.csv"
    lock = threading.Lock()
    res: list[dict] = []
    prog = {"n": 0, "b": 0, "t0": time.time(), "last": 0.0}

    def done(p: dict, status: str, detalj: str = "") -> None:
        with lock:
            res.append({**p, "status": status, "detalj": detalj})
            prog["n"] += 1
            prog["b"] += max(p["bytes"], 0) if status in ("NEDLADDAD", "PLAN") else 0
            t = time.time()
            if t - prog["last"] >= 15 or prog["n"] == len(plan):
                prog["last"] = t
                rate = prog["b"] / max(t - prog["t0"], 0.001)
                say(f"    {prog['n']}/{len(plan)} filer  {gb(prog['b'])} GB hämtat  {rate / 1048576:,.1f} MB/s")

    def one(p: dict) -> None:
        dest = repo / p["dest"]
        if not p["sha"]:
            return done(p, "UTAN-SHA", "blob saknar sha256 i metadata/manifest -- hämtas inte")
        if dest.exists():
            if dest.stat().st_size == p["bytes"] and sha256_file(dest) == p["sha"]:
                return done(p, "HOPPAD", "identisk fil finns redan")
            if not a.skriv_over:
                return done(p, "KONFLIKT", f"fil med annat innehåll finns ({dest.stat().st_size} B) -- rörs inte (--skriv-over flyttar undan den)")
        if mode != "KOR":
            return done(p, "PLAN")
        try:
            bc = svc.get_container_client(p["container"]).get_blob_client(p["blob"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_name(dest.name + ".part")
            h = hashlib.sha256()
            n = 0
            with part.open("wb") as fh:
                for chunk in bc.download_blob(max_concurrency=1).chunks():
                    fh.write(chunk)
                    h.update(chunk)
                    n += len(chunk)
            got = h.hexdigest().upper()
            if got != p["sha"] or (p["bytes"] >= 0 and n != p["bytes"]):
                part.unlink(missing_ok=True)
                return done(p, "FEL", f"verifiering: {n} B, sha {'stämmer' if got == p['sha'] else 'avviker'} -- filen kastad")
            if dest.exists():
                dest.replace(dest.with_name(dest.name + f".fore-aterstallning-{stamp}"))
            part.replace(dest)
            return done(p, "NEDLADDAD")
        except Exception as e:
            msg = str(e).splitlines()[0][:200] if str(e) else ""
            st = "SAKNAS-I-BLOB" if "BlobNotFound" in msg or e.__class__.__name__ == "ResourceNotFoundError" else "FEL"
            return done(p, st, f"{e.__class__.__name__}: {msg}")

    say(f"  {'hämtar' if mode == 'KOR' else 'planerar'} med {a.tradar} trådar ...")
    with ThreadPoolExecutor(max_workers=max(1, a.tradar)) as ex:
        for f in as_completed([ex.submit(one, p) for p in plan]):
            f.result()

    from collections import Counter
    c = Counter(r["status"] for r in res)
    with kv_csv.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["dest", "container", "blob", "bytes", "sha256", "kalla", "status", "detalj"])
        for r in sorted(res, key=lambda r: r["dest"]):
            w.writerow([r["dest"], r["container"], r["blob"], r["bytes"], r["sha"], r["kalla"], r["status"], r["detalj"]])
    prob = [r for r in res if r["status"] in PROBLEM]
    md = [f"# ÅTERSTÄLLNING — BCG ({now:%Y-%m-%d %H:%M}, läge {mode})", "",
          f"*`{TOOL}` v{VERSION}. Utvecklare: Jens Palmö (Senior Business Analyst). Profiler: {', '.join(sorted(profiler))}. "
          f"Konto `{a.konto}`. Rad per fil i `{kv_csv.name}`.*", "",
          f"Plan: **{len(plan)} filer, {gb(tot)} GB**.", "", "| Status | Filer |", "|---|---|"] + \
         [f"| `{k}` | {v} |" for k, v in c.most_common()] + [""]
    if prob:
        md += ["## Problem", "", "| Fil | Status | Detalj |", "|---|---|---|"] + \
              [f"| `{r['dest']}` | {r['status']} | {r['detalj'].replace('|', '/')} |" for r in prob[:60]] + [""]
    md += ["Omkörning är säker: identiska filer hoppas, befintliga filer med annat innehåll rörs inte."]
    kv_md = kv_csv.with_suffix(".md")
    kv_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    say("")
    say("  status: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    say(f"  kvitto: {kv_md}")
    if mode == "TORR":
        say("  GRIND: " + ("OK -- kör samma rad med --kor" if not prob else f"STOPP -- {len(prob)} problem, se kvittot"))
    code = 0 if not prob else 2
    say(f"  avslutskod: {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())

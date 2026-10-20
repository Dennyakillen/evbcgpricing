#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py — förstagångsinstallation av BCG Pricing (evbcgpricing), lokal miljö, på en ny dator.

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB).

Kontrakt: MASTER_INSTALL §2 (tolv krav). Mall: Scraping_VetPris install.py (2026-10-19). Avvikelser från
mallen är märkta AVSIKT på platsen. Allt projektspecifikt står i tabellen nedan — resten av filen är mallens.

Kör från repo-roten, i ett rent fönster (ingen aktiv venv, ingen PYTHONPATH), med Python 3.11:

    py -3.11 install.py

Gör, i ordning (allt är idempotent — kan köras om när som helst):
  1. Kontrollerar Python-versionen, aktiv venv och PYTHONPATH i terminalen.
  2. Skapar körtidsmapparna som inte ligger i repot: workspace/, output_model_feed/, output_analyspaket/.
  3. Skapar den virtuella miljön .venv/ (återanvänds om den finns; --recreate bygger om).
  4. Installerar beroendena ur requirements-local.txt i .venv (via "python -m pip" — AppLocker-vänligt).
  5. Gör repots platta moduler importerbara i .venv (en .pth-fil med orchestration/shared,
     orchestration/infrastructure, orchestration/webapp, tools/dw) — ersätter PYTHONPATH och de
     hårdkodade sys.path-raderna som pekar på C:\\Projekt\\BCG i äldre verktyg.
  6. Konfiguration: kopierar tools/dw/.env.example -> tools/dw/.env om den saknas (värden fylls i av människa).
  7. Kör verify_setup.py i .venv och ärver dess avslutskod.

Flaggor:
  --recreate     ta bort .venv och bygg om
  --no-install   hoppa över pip (bara mappar, venv, .pth, konfiguration och kontroll)
  --no-verify    kör inte verify_setup.py

Avslutskod: 0 = allt gick, 1 = något steg misslyckades (läs raden med [FEL]).
Flyttar du repomappen: kör install.py igen (.pth-filen bär absoluta sökvägar till DETTA repo).

Vad installationen INTE gör (MASTER_INSTALL §5): den bevisar inte åtkomst till DW (VPN + ODBC + AAD),
Blob (az login + kontonyckel/dataroll) eller VM:en (Ray-venven ~/bcg/cluster/.venv byggs där, se
docs/UBUNTU_AZURE_VM i biblioteket och DRIFT.md). Det är medvetna rök-tester som står i README/DRIFT.
"""
from __future__ import annotations

import argparse
import locale
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

# === Projektspecifikt (MASTER_INSTALL §2 krav 2) =================================================
APP_NAME = "BCG Pricing (evbcgpricing) — lokal miljö"
PYTHON_WANTED = (3, 11)            # EN sanning: verify_setup.py läser värdet härifrån (krav 12)
RUNTIME_DIRS = ["workspace", "workspace/flow_map", "workspace/validation_receipts",
                "output_model_feed", "output_analyspaket"]   # gitignorerade; sonder/validerare skriver hit
# AVSIKT (avviker från mallen, krav 6/11): repot har ingen src/-layout utan platta moduler som skripten
# lägger på sys.path själva (ORCH / "shared" osv). En .pth med FLERA rader ger samma sak i .venv för alla
# skript och verktyg, repo-relativt — utan PYTHONPATH och utan hårdkodade C:\Projekt\BCG-rader (IN.3).
PTH_DIRS = ["orchestration/shared", "orchestration/infrastructure", "orchestration/webapp", "tools/dw"]
PTH_NAME = "bcg_pricing_paths.pth"
# AVSIKT (krav 6): requirements.txt i roten är App Service-/containerlasten (Dockerfile, tools/stage_webapp.py)
# och får inte växa med lokala paket (D.22-klassen). Den lokala miljön pinnas separat.
REQUIREMENTS_REL = "requirements-local.txt"
ENV_EXAMPLE_REL = "tools/dw/.env.example"   # DW-anslutning för bränsleledets REGEN-steg (tools/dw/README.md)
ENV_FILE_REL = "tools/dw/.env"              # gitignorerad (.gitignore: .env, *.env); fylls i av människa
VERIFY_REL = "verify_setup.py"
START_CMD = r".\.venv\Scripts\python.exe orchestration\webapp\app.py"
START_URL = "http://127.0.0.1:5000  (dashboard lokalt; kräver az login för Blob-läsning)"
ROUTINES = "DRIFT.md (FÖRE/MOTOR/EFTER + validera), README.md, REPLIKERING_OCH_VALIDERING.md"
# === Slut projektspecifikt ========================================================================

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / REQUIREMENTS_REL
VERIFY = ROOT / VERIFY_REL


def say(msg: str = "") -> None:
    print(msg, flush=True)


def ok(msg: str) -> None:
    say(f"  [OK]      {msg}")


def warn(msg: str) -> None:
    say(f"  [OBS]     {msg}")


def fail(msg: str) -> None:
    say(f"  [FEL]     {msg}")


def step(title: str) -> None:
    say("")
    say(f"--- {title}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def _same_path(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def _rmtree(path: Path) -> None:
    """rmtree som även tar skrivskyddade filer; onexc från 3.12, onerror före (samma signatur)."""
    def handler(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=handler)
    else:
        shutil.rmtree(path, onerror=handler)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=f"Förstagångsinstallation av {APP_NAME}.")
    ap.add_argument("--recreate", action="store_true", help="ta bort .venv och bygg om")
    ap.add_argument("--no-install", action="store_true", help="hoppa över pip install")
    ap.add_argument("--no-verify", action="store_true", help="kör inte verify_setup.py")
    args = ap.parse_args(argv)

    say("=" * 62)
    say(f"  INSTALL — {APP_NAME}")
    say(f"  Repo-rot: {ROOT}")
    say(f"  Python:   {sys.executable}")
    say("=" * 62)
    errors = 0

    # 1. Python, aktiv venv, PYTHONPATH -------------------------------------------------------
    step("1. Python")
    v = sys.version_info
    if (v.major, v.minor) == PYTHON_WANTED:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        warn(f"Python {v.major}.{v.minor}.{v.micro} — beroendena är pinnade och testade mot "
             f"{PYTHON_WANTED[0]}.{PYTHON_WANTED[1]}. Fortsätter, men kör helst med "
             f"{PYTHON_WANTED[0]}.{PYTHON_WANTED[1]}.")
    if sys.prefix != sys.base_prefix:
        if _same_path(Path(sys.prefix), VENV):
            ok("körs från repots egen .venv")
        else:
            # MASTER_INSTALL IN.2: en aktiv venv från en annan mapp förorenar installationen
            warn(f"en annan venv är aktiv ({sys.prefix}) — kör 'deactivate' eller öppna ett nytt fönster "
                 "och kör om. Fortsätter (.venv byggs från bas-tolken).")
    pp = os.environ.get("PYTHONPATH")
    if pp:
        # Kallstart-vakt: PYTHONPATH går före .venv:s sökväg och kan peka på en annan kopia av koden
        warn(f"PYTHONPATH är satt i terminalen: {pp} — behövs inte efter steg 5 och kan peka på fel kopia "
             "av koden. Ta bort: Remove-Item Env:PYTHONPATH")
    if not REQUIREMENTS.is_file():
        fail(f"{REQUIREMENTS.name} saknas i repo-roten — är du i rätt mapp?")
        return 1

    # 2. Mappar --------------------------------------------------------------------------------
    step("2. Mappar som inte ligger i repot")
    for d in RUNTIME_DIRS:
        p = ROOT / d
        if p.is_dir():
            ok(f"{d}/  finns")
        else:
            p.mkdir(parents=True, exist_ok=True)
            ok(f"{d}/  skapad")

    # 3. Virtuell miljö ------------------------------------------------------------------------
    step("3. Virtuell miljö (.venv)")
    if VENV.exists() and args.recreate:
        say("  tar bort befintlig .venv (--recreate) ...")
        _rmtree(VENV)
    if venv_python().is_file():
        ok(f".venv finns — återanvänds ({venv_python()})")
    else:
        say("  skapar .venv ...")
        try:
            venv.EnvBuilder(with_pip=True, clear=False, symlinks=(os.name != "nt")).create(VENV)
            ok(f".venv skapad ({venv_python()})")
        except Exception as e:
            fail(f"kunde inte skapa .venv: {e}")
            return 1

    # 4. Beroenden -----------------------------------------------------------------------------
    step(f"4. Beroenden ({REQUIREMENTS_REL})")
    if args.no_install:
        warn("hoppar över pip install (--no-install)")
    else:
        cmd = [str(venv_python()), "-m", "pip", "install", "-r", str(REQUIREMENTS)]
        say("  " + " ".join(cmd))
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode == 0:
            ok("beroenden installerade")
        else:
            fail(f"pip install misslyckades (kod {r.returncode}) — läs utskriften ovan (proxy? versionskonflikt?)")
            errors += 1

    # 5. Platta moduler importerbara i .venv ---------------------------------------------------
    # AVSIKT (avviker från mallen): flera mappar i en .pth (en rad var). site.py läser .pth med lokal
    # teckenkodning (cp1252 på svenska Windows), därför skrivs filen i den — en sökväg med tecken utanför
    # kodningen ger [FEL] och rådet att lägga repot i en enklare sökväg.
    step("5. Gör repots moduler importerbara i .venv (.pth)")
    r = subprocess.run([str(venv_python()), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        fail(f"kunde inte läsa .venv:s site-packages: {r.stderr.strip()}")
        errors += 1
    else:
        pth = Path(r.stdout.strip()) / PTH_NAME
        lines = [str((ROOT / d).resolve()) for d in PTH_DIRS]
        missing = [d for d in PTH_DIRS if not (ROOT / d).is_dir()]
        if missing:
            fail(f"mappar saknas i repot: {', '.join(missing)} — är klonen komplett?")
            errors += 1
        enc = locale.getpreferredencoding(False)
        try:
            current = pth.read_text(encoding=enc).splitlines() if pth.is_file() else None
        except (OSError, UnicodeDecodeError):
            current = None
        if current == lines:
            ok(f"{PTH_NAME} pekar redan på {len(lines)} mappar i detta repo")
        else:
            try:
                pth.write_text("\n".join(lines) + "\n", encoding=enc)
                ok(f"{PTH_NAME} skriven -> {len(lines)} mappar under {ROOT}" + (" (ersatte tidigare)" if current else ""))
                for ln in lines:
                    say(f"            {ln}")
            except UnicodeEncodeError:
                fail(f"sökvägen {ROOT} kan inte skrivas i teckenkodningen {enc} — "
                     "lägg repot i en sökväg utan specialtecken")
                errors += 1

    # 6. Konfiguration -------------------------------------------------------------------------
    step("6. Konfiguration (DW-anslutning för REGEN)")
    env_example = ROOT / ENV_EXAMPLE_REL
    env_file = ROOT / ENV_FILE_REL
    if env_file.is_file():
        ok(f"{ENV_FILE_REL} finns — rörs inte")
    elif env_example.is_file():
        shutil.copyfile(env_example, env_file)
        ok(f"{ENV_FILE_REL} skapad från {ENV_EXAMPLE_REL}")
        warn(f"fyll i FABRIC_SERVER/FABRIC_DATABASE i {ENV_FILE_REL} — värdena finns hos den som förvaltar DW (IT); "
             "behövs bara för bränsleledets REGEN-steg (tools/dw/README.md)")
    else:
        warn(f"{ENV_EXAMPLE_REL} saknas — ingen konfigurationsfil skapad")

    # 7. verify_setup --------------------------------------------------------------------------
    step(f"7. Kontroll ({VERIFY_REL})")
    if args.no_verify:
        warn(f"hoppar över {VERIFY_REL} (--no-verify)")
    elif not VERIFY.is_file():
        warn(f"{VERIFY_REL} saknas — ingen kontroll")
    else:
        r = subprocess.run([str(venv_python()), str(VERIFY)], cwd=ROOT)
        if r.returncode == 0:
            ok(f"{VERIFY_REL}: inga [FEL]")
        else:
            fail(f"{VERIFY_REL} avslutade med kod {r.returncode} — rätta [FEL]-raderna ovan")
            errors += 1

    # Nästa steg -------------------------------------------------------------------------------
    say("")
    say("=" * 62)
    if errors:
        say(f"  KLART MED FEL ({errors}) — se [FEL] ovan.")
    else:
        say("  KLART. Nästa steg:")
    if os.name == "nt":
        say(r"    .\.venv\Scripts\Activate.ps1")
    else:
        say("    source .venv/bin/activate")
    say(f"    {START_CMD}")
    say(f"    ({START_URL})")
    say(f"  Rutiner: {ROUTINES}")
    say("  Flyttar du repomappen: kör install.py igen.")
    say("=" * 62)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

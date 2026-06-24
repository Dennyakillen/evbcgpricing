#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_6_launch_resilience.py  --  Bevisa launch-robusthet under REALISTISKA villkor
====================================================================================
VARFOR DENNA SOND (rotorsak till att --launch-test inte raddade oss 2026-06-24):
ssh_launch_selftest (--launch-test) testar detach-mekaniken i VAKUUM -- den gor
EN ren launch utan nagot fore. Darfor gav den PASS samtidigt som en riktig korning
FAILADE: i en riktig korning foregas launch av en SERIE SSH-anrop (preflight: 3x
test -e + archive = 4 anrop) och tunneln blinkar EFTER en serie, inte pa forsta.
launch landade i blinken. Sonden i vakuum triggade aldrig det villkoret.

DENNA SOND testar de breda hypoteserna som --launch-test missar:
  H1  Detach-mekanik frisk i vakuum?           (= gamla --launch-test, baslinje)
  H2  Launch overlever EFTER en anropsserie?   (= dagens faktiska felscenario)
  H3  Launch overlever upprepade cykler?       (intermittens over tid)
  H4  Post-launch pgrep-verifiering fungerar?  (A2-fixens forutsattning)
  H5  scp overlever en serie + blink?          (nedstroms-fallpunkt, B-fixen)

Varje hypotes ar ett ISOLERAT, REPRODUCERBART test som stadar efter sig (pkill).
Anvand FORE en 50-min-korning: om H2 failar, fixa launch INNAN du betalar VM-tid.

DESIGN (KARNPRINCIP P.5 + AZ.7): mat populationen/utfallet per scenario, folj
kedjan, jamfor vakuum vs realistisk. En sond som bara testar det latta fallet
ljuger -- den maste reproducera produktionsvillkoret (anropsserie -> blink).

KOER (global py -3.11, fran orchestration/ sa importerna loser):
    cd C:\\Projekt\\BCG\\orchestration
    py -3.11 ..\\tools\\diagnos\\probe_6_launch_resilience.py
    (VM maste vara igang. Sonden deallokerar INTE -- du styr VM-livscykeln.)

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Forfattare: Claude-radgivare.
Beroende: azure_vm (delad infra), std-lib.
"""
from __future__ import annotations
import sys, time, io
from pathlib import Path
from datetime import datetime

# --- importera delad infra (kor fran orchestration/ ELLER lagg den i sys.path) ---
HERE = Path(__file__).resolve()
for cand in [HERE.parents[2] / "orchestration" / "infrastructure",
             Path(r"C:\Projekt\BCG\orchestration\infrastructure")]:
    if cand.exists():
        sys.path.insert(0, str(cand))
        break
try:
    import azure_vm as A
except Exception as e:
    print(f"[FEL] kan ej importera azure_vm: {e}")
    print("  -> kor fran C:\\Projekt\\BCG\\orchestration eller verifiera sokvagen.")
    sys.exit(2)

# Force UTF-8 stdout (svenska kommentarer i kvitto)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TEST_LOG = "/home/azureuser/bcg/logs/_probe6.log"
TEST_SIG = "sleep 47"            # unik signatur for pgrep/pkill, kort nog
RESULTS = []


def _cfg():
    # Hamta default-config samma vag runnern gor. Justera om din azure_vm
    # exponerar en annan factory.
    for name in ("default_config", "load_config", "get_config", "VmConfig"):
        fn = getattr(A, name, None)
        if fn is None:
            continue
        try:
            return fn() if name != "VmConfig" else None
        except Exception:
            continue
    return None


def _line(tag, ok, detail=""):
    sym = "OK   " if ok else "FAIL "
    print(f"  [{tag}] {sym} {detail}")
    RESULTS.append((tag, ok, detail))


def cleanup(cfg):
    try:
        A.ssh_run(cfg, f"pkill -f '{TEST_SIG}' || true", check=False, timeout=15)
    except Exception:
        pass


def warm_series(cfg, n=4):
    """Reproducera preflight-anropsserien som foregar launch i en riktig korning.
    Det ar HAR tunneln varms upp till blink. --launch-test gor INTE detta."""
    for i in range(n):
        A.ssh_run(cfg, f"test -e /home/azureuser && echo yes || echo no",
                  check=False, timeout=30)


def h1_vacuum(cfg):
    """H1: detach i vakuum (gamla --launch-test-baslinjen)."""
    print("\n[H1] Detach-mekanik i VAKUUM (baslinje = gamla --launch-test)")
    cleanup(cfg)
    t0 = time.time()
    try:
        A.ssh_launch_detached(cfg, f"{TEST_SIG} && echo done", TEST_LOG)
        elapsed = time.time() - t0
        released = elapsed <= 15
        _line("H1.release", released, f"ssh slappte pa {elapsed:.1f}s (gransen 15s)")
        time.sleep(1)
        alive = bool(A.ssh_run(cfg, f"pgrep -f '{TEST_SIG}' || true",
                               check=False, timeout=20).stdout.strip())
        _line("H1.alive", alive, "process lever pa VM" if alive else "process EJ funnen")
    except Exception as e:
        _line("H1", False, f"undantag: {e}")
    finally:
        cleanup(cfg)


def h2_after_series(cfg):
    """H2: launch EFTER en anropsserie -- dagens faktiska felscenario."""
    print("\n[H2] Launch EFTER 4-anropsserie (REPRODUCERAR dagens fel)")
    cleanup(cfg)
    try:
        warm_series(cfg, n=4)            # varm upp tunneln som preflight gor
        t0 = time.time()
        A.ssh_launch_detached(cfg, f"{TEST_SIG} && echo done", TEST_LOG)
        elapsed = time.time() - t0
        released = elapsed <= 15
        _line("H2.release", released, f"ssh slappte pa {elapsed:.1f}s EFTER serie")
        time.sleep(1)
        alive = bool(A.ssh_run(cfg, f"pgrep -f '{TEST_SIG}' || true",
                               check=False, timeout=20).stdout.strip())
        _line("H2.alive", alive,
              "jobb lever efter serie+launch" if alive
              else "JOBB EJ STARTAT efter serie -- DAGENS FEL reproducerat")
    except Exception as e:
        _line("H2", False, f"undantag (= dagens OBSERVATION LOST?): {e}")
    finally:
        cleanup(cfg)


def h3_repeated(cfg, cycles=3):
    """H3: upprepade launch-cykler -- fanga intermittens over tid."""
    print(f"\n[H3] {cycles} upprepade launch-cykler (intermittens)")
    ok_count = 0
    for c in range(1, cycles + 1):
        cleanup(cfg)
        try:
            warm_series(cfg, n=2)
            A.ssh_launch_detached(cfg, f"{TEST_SIG} && echo done", TEST_LOG)
            time.sleep(1)
            alive = bool(A.ssh_run(cfg, f"pgrep -f '{TEST_SIG}' || true",
                                   check=False, timeout=20).stdout.strip())
            if alive:
                ok_count += 1
            _line(f"H3.cykel{c}", alive, "lever" if alive else "ej startad")
        except Exception as e:
            _line(f"H3.cykel{c}", False, f"undantag: {e}")
        finally:
            cleanup(cfg)
    _line("H3.summa", ok_count == cycles, f"{ok_count}/{cycles} cykler lyckades")


def h4_pgrep_verify(cfg):
    """H4: fungerar pgrep-verifieringen som A2-fixen forlitar sig pa?"""
    print("\n[H4] Post-launch pgrep-verifiering (A2-fixens forutsattning)")
    cleanup(cfg)
    try:
        A.ssh_launch_detached(cfg, f"{TEST_SIG} && echo done", TEST_LOG)
        time.sleep(1)
        cp = A.ssh_run(cfg, f"pgrep -f '{TEST_SIG}' || true", check=False, timeout=20, retries=2)
        found = bool(cp.stdout.strip())
        _line("H4.pgrep", found, f"pgrep hittade pid(er): {cp.stdout.strip()[:40]}" if found
              else "pgrep tomt -- verifiering skulle ge falskt negativt")
    except Exception as e:
        _line("H4", False, f"undantag: {e}")
    finally:
        cleanup(cfg)


def h5_scp(cfg):
    """H5: scp overlever serie? (nedstroms-fallpunkt, B-fixen)."""
    print("\n[H5] scp-hamtning efter serie (nedstroms, B-fixen)")
    remote = "/home/azureuser/bcg/logs/_probe6_scptest.txt"
    local = str(Path.home() / "_probe6_scptest.txt")
    try:
        A.ssh_run(cfg, f"echo probe6 > {remote}", check=False, timeout=20)
        warm_series(cfg, n=4)
        A.scp_from_vm(cfg, remote, local)
        ok = Path(local).exists()
        _line("H5.scp", ok, f"hamtad till {local}" if ok else "scp gav ingen fil")
        if ok:
            Path(local).unlink(missing_ok=True)
        A.ssh_run(cfg, f"rm -f {remote} || true", check=False, timeout=15)
    except Exception as e:
        _line("H5", False, f"undantag: {e}")


def main() -> int:
    print("=" * 74)
    print(f"SOND 6 -- launch-robusthet under realistiska villkor   {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 74)
    cfg = _cfg()
    if cfg is None:
        print("[FEL] kunde ej skapa VmConfig. Justera _cfg() till din azure_vm-factory.")
        return 2

    # Snabb nabarhetscheck forst (ingen mening att kora om VM ar nere)
    try:
        cp = A.ssh_run(cfg, "echo ok", check=False, timeout=20)
        if "ok" not in cp.stdout:
            print("[FEL] VM ej SSH-nabar (echo gav inte 'ok'). Starta VM forst."); return 2
    except Exception as e:
        print(f"[FEL] VM ej nabar: {e}. Starta VM forst."); return 2

    h1_vacuum(cfg)
    h2_after_series(cfg)
    h3_repeated(cfg, cycles=3)
    h4_pgrep_verify(cfg)
    h5_scp(cfg)

    print("\n" + "=" * 74)
    print("DOM:")
    fails = [t for t, ok, _ in RESULTS if not ok]
    h1_ok = all(ok for t, ok, _ in RESULTS if t.startswith("H1"))
    h2_ok = all(ok for t, ok, _ in RESULTS if t.startswith("H2"))
    if not fails:
        print("  -> ALLA scenarier grona. Launch robust aven efter serie. Kor pipelinen.")
    elif h1_ok and not h2_ok:
        print("  -> H1 (vakuum) gron men H2 (efter serie) FAIL = EXAKT dagens fel-monster.")
        print("     Launch overlever inte en anropsserie. Harda ssh_launch_detached")
        print("     (retries+pgrep-verify) INNAN du kor en 50-min-pipeline.")
    else:
        print(f"  -> {len(fails)} scenarier failade: {', '.join(fails)}")
        print("     Las raderna ovan. Atgarda fore tung korning.")
    print("=" * 74)
    print(f"[Kvitto] kor med  ... | Tee-Object sond6_<datum>.txt  for arkiv")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

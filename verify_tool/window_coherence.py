"""
window_coherence.py  --  tvars-familje-grinden (Phase Z, additivt)
==================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.  HARDAD 2026-06-26: observation loss != failure.

PROBLEMET DETTA LOSER (din faktiska fraga)
------------------------------------------
"...utan strukturell friktion eller failade korningar for att natt tvars
familjerna fattas, missas eller ignoreras."

Idag ager INGEN komponent helheten over alla familjer. run_data ager extraction.
Tre separata familje-runners ager var sin MOTOR-fas. run_after ager EFTER. Var
och en ar valbyggd men VET INTE OM DE ANDRA. Inget framtvingar att alla tre
familjer kordes mot SAMMA fonster innan EFTER startar.

Fellaget (tyst, plausibelt, dyrt): kor cluster -> hoppa site av misstag -> kor
run_after. run_step6 placerar da FORRA korningens site-output (filen ligger kvar
pa disk), vaver pa inaktuell data, producerar trovardigt men FEL utfall.

TVA KALLOR TILL SANNING -- LOKAL (offline) ELLER BLOB
-----------------------------------------------------
Koherens kan bevisas tva vagar:
  1. LOKAL (default, OFFLINE): jamfor familjernas output_summary-filtider mot
     parquetens tid. Kraver INGEN token, INGEN Blob, INGET nat. Det racker for
     att fanga "en familj saknas/ar inaktuell" -- det vanligaste fellaget.
  2. BLOB (--via-blob): las den delade statusfilen och bevisa att alla MOTOR-
     faser ar SUCCEEDED mot samma run_id. Striktare, men kraver token.

AZ.7 (ARVD UR azure_vm.py): observation loss != failure. Om Blob ej kan nas
(token dod, VPN nere) ar det INTE NO-GO -- det ar "kunde inte bevisa via Blob,
faller tillbaka pa lokal koll". En grind som kraschar pa utgangen token ar en
grind som ljuger. Den degraderar mjukt, alltid.

"Harled, deklarera inte tva ganger": MOTOR-faserna HARLEDS ur
run_status.default_pipeline (PhaseLocation.VM), deklareras inte har.

KOR (global py-3.11, repo-roten)
--------------------------------
    py -3.11 verify_tool\\window_coherence.py --start 2022-07-01 --end 2025-06-29
    py -3.11 verify_tool\\window_coherence.py --end 2026-05-31 --via-blob   # striktare, kraver token
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
ELAST = REPO / "Pipeline" / "02. Elasticity"
PARQUET = (ELAST / "Sweden_Elasticity_Data_Prep_SQL" / "parquet" / "transaction_data.parquet")

FAMILY_OUTPUT_ROOTS = {
    "cluster": ELAST / "2. Product Cluster Level Models" / "output",
    "site":    ELAST / "3. Product Site Level Models" / "output",
    "bundle":  ELAST / "5. Bundle Clinic Models" / "output",
}
PHASE_TO_FAMILY = {"cluster_model": "cluster", "site_model": "site", "bundle_model": "bundle"}

sys.path.insert(0, str(REPO / "orchestration" / "shared"))
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))


@dataclass
class GateResult:
    go: bool
    rows: list


def _newest_output_summary(root: Path):
    if not root.exists():
        return None
    hits = list(root.glob("**/output_summary.xlsx"))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def _motor_phase_keys() -> list[str]:
    try:
        from run_status import default_pipeline, PhaseLocation  # type: ignore
        phases = default_pipeline(run_id="window_coherence_probe").phases
        return [p.key for p in phases if p.location == PhaseLocation.VM]
    except Exception:
        return ["cluster_model", "site_model", "bundle_model"]


def check_coherence(run_id: str, via_blob: bool = False) -> GateResult:
    rows: list = []
    go = True

    def rec(status, check, detalj=""):
        nonlocal go
        rows.append((status, check, detalj))
        if status == "STOP":
            go = False
        mark = {"OK": "  OK ", "STOP": "STOP!", "INFO": "info ", "WARN": "warn "}.get(status, status)
        print(f"   [{mark}] {check}" + (f"  --  {detalj}" if detalj else ""))

    print("=" * 72)
    print(f"WINDOW COHERENCE GATE  --  run_id (fonster): {run_id}")
    print(f"  kalla: {'BLOB (statusfil, kraver token)' if via_blob else 'LOKAL (filtider, offline)'}")
    print("=" * 72)

    if not PARQUET.exists():
        rec("WARN", "parquet saknas lokalt", f"{PARQUET} -- kan ej farskhetskolla output mot indata")
        parquet_mtime = None
    else:
        parquet_mtime = datetime.fromtimestamp(PARQUET.stat().st_mtime)
        rec("INFO", "parquet (indata-referens)",
            f"{PARQUET.stat().st_size/1e6:.0f} MB, {parquet_mtime:%Y-%m-%d %H:%M}")

    motor_keys = _motor_phase_keys()
    rec("INFO", "MOTOR-faser (harledda ur default_pipeline)", ", ".join(motor_keys))

    # --- 1. KOHERENS via Blob-status (valfritt, AZ.7-tolerant) ---
    if via_blob:
        print("\n-- 1. KOHERENS (Blob-status): alla motor-familjer SUCCEEDED mot samma fonster? --")
        try:
            from run_status import PhaseState  # type: ignore
            from blob import read_status        # type: ignore
            rs = read_status(run_id)
            phase_by_key = {p.key: p for p in rs.phases}
            for mk in motor_keys:
                p = phase_by_key.get(mk)
                if p is None:
                    rec("STOP", f"motor-fas '{mk}' saknas i statusfilen",
                        "familjen kordes aldrig mot detta fonster")
                elif p.state == PhaseState.SUCCEEDED:
                    rec("OK", f"{mk}: SUCCEEDED", p.note or "")
                elif p.state == PhaseState.SKIPPED:
                    rec("WARN", f"{mk}: SKIPPED", f"{p.note or ''} -- medvetet parkerad?")
                else:
                    rec("STOP", f"{mk}: {p.state.value.upper()} (ej klar)",
                        "EFTER skulle vava pa inaktuell/saknad familjedata")
        except Exception as e:  # noqa: BLE001 -- AZ.7: observation loss != failure
            msg = str(e)
            is_token = ("token" in msg.lower() or "credential" in msg.lower()
                        or "expired" in msg.lower() or "AADSTS" in msg)
            rec("WARN", "Blob-status ej nabar -- observation loss (AZ.7)",
                ("token dod: az login --scope https://storage.azure.com/.default"
                 if is_token else f"{type(e).__name__}: {msg[:100]}")
                + " -- faller tillbaka pa LOKAL koll nedan, kraschar EJ")

    # --- 2. FARSKHET (LOKAL, alltid -- offline) ---
    print("\n-- 2. FARSKHET (lokal): varje familjs output nyare an indatat? --")
    for mk in motor_keys:
        fam = PHASE_TO_FAMILY.get(mk, mk)
        root = FAMILY_OUTPUT_ROOTS.get(fam)
        if root is None:
            rec("WARN", f"{fam}: ingen output-rot kand", "lagg i FAMILY_OUTPUT_ROOTS")
            continue
        out = _newest_output_summary(root)
        if out is None:
            rec("STOP", f"{fam}: ingen output_summary pa disk",
                f"sokt under {root} -- EFTER har inget farskt att vava")
            continue
        out_mtime = datetime.fromtimestamp(out.stat().st_mtime)
        detail = f"{out.parent.name}\\output_summary.xlsx, {out_mtime:%Y-%m-%d %H:%M}"
        if parquet_mtime is None:
            rec("INFO", f"{fam}: output finns (farskhet ej jamford)", detail)
        elif out_mtime >= parquet_mtime:
            rec("OK", f"{fam}: output nyare an parquet", detail)
        else:
            rec("WARN", f"{fam}: output aldre an parquet",
                f"{detail} < parquet {parquet_mtime:%Y-%m-%d %H:%M} -- forra fonstrets fil? "
                "(WARN ej STOP: vid facit-validering ar detta vantat -- las medvetet)")

    print("\n" + "-" * 72)
    if go:
        print("GO -- ingen tvars-familje-brist funnen (se WARN for sant att granska medvetet).")
    else:
        print("NO-GO -- en familj SAKNAS pa disk. EFTER har inget att vava (se STOP ovan).")
    return GateResult(go=go, rows=rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Tvars-familje-koherensgrind fore EFTER.")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--start", default="2022-07-01")
    ap.add_argument("--end", default="2026-04-30")
    ap.add_argument("--via-blob", action="store_true",
                    help="Bevisa aven via Blob-statusfil (striktare, kraver token). "
                         "Token-dod degraderar mjukt till lokal koll (AZ.7).")
    args = ap.parse_args()

    run_id = args.run_id
    if run_id is None:
        try:
            from run_status import window_run_id  # type: ignore
            run_id = window_run_id(args.start, args.end)
        except Exception:
            run_id = f"{args.start}_{args.end}"

    res = check_coherence(run_id, via_blob=args.via_blob)
    return 0 if res.go else 1


if __name__ == "__main__":
    sys.exit(main())

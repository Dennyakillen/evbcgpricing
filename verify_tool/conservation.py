"""
conservation.py  --  bevarandekontroll tvars skarvarna (Phase Z, additivt)
==========================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.

DJUPARE FRAGA AN DE ANDRA VERKTYGEN
-----------------------------------
pipeline_contracts fragar "har filen ratt form?". window_coherence fragar "ar
familjerna i synk?". Conservation fragar det svaraste: "OVERLEVDE populationen
resan mellan A och B, eller tappades natt TYST pa vagen?" Det ar att rakna vattnet
FORE och EFTER varje skarv -- inte att inspektera roret.

DEN CENTRALA INSIKTEN (varfor detta inte ar "samma antal in som ut")
--------------------------------------------------------------------
Vid nastan varje skarv SKA antalet andras -- det ar poangen. En naiv check som
larmar pa varje forandring blir brus du lar dig ignorera (varre an ingen check).
Konsten ar att skilja VANTAD TRANSFORMATION fran OVANTAD LACKA. Darfor har varje
skarv sin EGEN definition av "bevarad":

  SKARV 1  DW -> parquet      : radantal SKA VAXA monotont. MINSKNING = lacka.
                                (G7/73%-klassen -- din dyraste felklass.)
  SKARV 2  parquet -> CSV     : radantal SKA KRYMPA (aggregering). Bevarad =
                                alla distinkta ENTITETER (produkter/kliniker) finns
                                kvar. Forsvunna entiteter = lacka.
  SKARV 3  CSV -> modell-out  : rader tappas AVSIKTLIGT (signifikanstrosklar).
                                Bevarad = bortfallet matchar BCG:s avsiktliga
                                filtrering, inte mer.

AERLIG AVGRANSNING (kalla fore pastaende)
-----------------------------------------
SKARV 1 ar HELT byggd -- jag kan definiera den korrekt ur kand parquet-struktur
(InvoiceDate, ItemCode m.fl.) + din egen resolve_window_end-logik. SKARV 2 och 3
kraver att du VET exakt vad BCG-koden avsiktligt gor med populationen (vilka
produkter den filtrerar och varfor). Jag har INTE sett regenerate_*, replicate_*
eller modellstegens filtrering. Darfor ar skarv 2-3 ett FORBERETT RAMVERK med en
EXPECTED-mekanism du kalibrerar mot matning -- inte gissade trosklar. Att bygga
dem fardiga utan kallan vore att skapa den falska trygghet hela detta lager finns
for att forhindra.

SNAPSHOT-MONSTRET (hur bevarande mats over tid)
-----------------------------------------------
Conservation kraver TVA matpunkter att jamfora. Verktyget tar en SNAPSHOT av varje
skarvs populationsmatt (radantal, distinkta entiteter, datumspann) och sparar den.
Nasta korning jamfor mot forra snapshotten: vaxte det som skulle vaxa, kymte det
som skulle krympa, forsvann inget som skulle finnas kvar? Spike-to-harden: forsta
snapshotten blir baslinjen, drift mot den blir signalen.

KOR (global py-3.11, repo-roten)
--------------------------------
    py -3.11 verify_tool\\conservation.py --snapshot          # mat + spara nulage
    py -3.11 verify_tool\\conservation.py                      # jamfor mot forra snapshot
    py -3.11 verify_tool\\conservation.py --skarv 1            # bara skarv 1 (parquet-vaxt)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
ELAST = REPO / "Pipeline" / "02. Elasticity"
VERIFY = REPO / "verify_tool"
PARQUET = ELAST / "Sweden_Elasticity_Data_Prep_SQL" / "parquet" / "transaction_data.parquet"
SNAPSHOT = VERIFY / "conservation_snapshot.json"

# Familjernas output_summary-rotter (spegel av window_coherence -- samma sanning)
FAMILY_OUTPUT_ROOTS = {
    "cluster": ELAST / "2. Product Cluster Level Models" / "output",
    "site":    ELAST / "3. Product Site Level Models" / "output",
    "bundle":  ELAST / "5. Bundle Clinic Models" / "output",
}

# ---------------------------------------------------------------------------
# SKARV 2-3 KALIBRERING (du fyller i ur BCG-kunskap -- mat, gissa inte).
# Satt EXPECTED_RETENTION nar du MATT vad BCG avsiktligt filtrerar. Tills dess
# rapporterar skarv 2-3 bara FAKTA (INFO) och domer inte -- ingen falsk trygghet.
# ---------------------------------------------------------------------------
SKARV3_CALIBRATED = False   # satt True nar du mott bortfallet och fyllt i nedan
EXPECTED_RETENTION = {
    # familj: (min_andel, max_andel) av CSV-entiteter som SKA na modell-output.
    # Exempel nar kalibrerad: "cluster": (0.85, 1.0)  # max 15% avsiktligt bortfall
    # Lamna tom tills mott -- da rapporterar skarv 3 bara fakta.
}


@dataclass
class SkarvMatt:
    """Populationsmatt for en skarv vid en tidpunkt."""
    skarv: str
    timestamp: str
    rows: int | None = None
    distinct_entities: int | None = None
    entity_kind: str = ""          # vad distinct_entities raknar
    date_min: str | None = None
    date_max: str | None = None
    note: str = ""
    extra: dict = field(default_factory=dict)


ROWS: list = []


def rec(status, check, detalj=""):
    ROWS.append((status, check, detalj))
    mark = {"OK": "  OK ", "LEAK": "LEAK!", "INFO": "info ", "WARN": "warn ", "PASS": "PASS "}.get(status, status)
    print(f"   [{mark}] {check}" + (f"  --  {detalj}" if detalj else ""))


def section(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


# ---------------------------------------------------------------------------
# SKARV 1: DW -> parquet. Radantal SKA VAXA. Minskning = lacka.
# Helt byggd ur kand parquet-struktur (InvoiceDate).
# ---------------------------------------------------------------------------
def measure_skarv1() -> SkarvMatt:
    m = SkarvMatt(skarv="1_dw_to_parquet", timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                  entity_kind="distinct ItemCode")
    if not PARQUET.exists():
        m.note = "parquet saknas"
        return m
    try:
        import duckdb
        pq = str(PARQUET).replace("\\", "/")
        con = duckdb.connect()
        row = con.execute(
            f"SELECT COUNT(*), "
            f"       MIN(InvoiceDate)::VARCHAR, MAX(InvoiceDate)::VARCHAR, "
            f"       COUNT(DISTINCT ItemCode) "
            f"FROM read_parquet('{pq}')"
        ).fetchone()
        con.close()
        m.rows = int(row[0])
        m.date_min = row[1][:10] if row[1] else None
        m.date_max = row[2][:10] if row[2] else None
        m.distinct_entities = int(row[3]) if row[3] is not None else None
    except Exception as e:  # noqa: BLE001
        m.note = f"duckdb-fel: {type(e).__name__}: {e}"
    return m


# ---------------------------------------------------------------------------
# SKARV 2/3: familjernas output. Mat distinkta entiteter ur output_summary.
# ---------------------------------------------------------------------------
def _newest_output(root: Path):
    if not root.exists():
        return None
    hits = list(root.glob("**/output_summary.xlsx"))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def measure_family_output(fam: str) -> SkarvMatt:
    m = SkarvMatt(skarv=f"3_model_output_{fam}",
                  timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                  entity_kind="distinct KEY")
    out = _newest_output(FAMILY_OUTPUT_ROOTS[fam])
    if out is None:
        m.note = "ingen output_summary"
        return m
    try:
        import openpyxl
        wb = openpyxl.load_workbook(out, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(c) for c in rows[0]] if rows else []
        m.rows = len(rows) - 1
        if "KEY" in hdr:
            ki = hdr.index("KEY")
            m.distinct_entities = len({r[ki] for r in rows[1:] if r[ki] is not None})
        m.extra["file"] = out.parent.name + "\\" + out.name
        wb.close()
    except Exception as e:  # noqa: BLE001
        m.note = f"openpyxl-fel: {type(e).__name__}: {e}"
    return m


# ---------------------------------------------------------------------------
# Jamforelse mot forra snapshot
# ---------------------------------------------------------------------------
def compare_skarv1(prev: dict, cur: SkarvMatt):
    """Skarv 1: rader SKA vaxa (eller vara lika om samma fonster). MINSKNING = LEAK."""
    if cur.rows is None:
        rec("WARN", "skarv 1: kunde ej mata parquet", cur.note)
        return
    rec("INFO", "skarv 1: parquet nu",
        f"{cur.rows:,} rader, {cur.distinct_entities:,} produkter, "
        f"{cur.date_min}..{cur.date_max}")
    if prev is None:
        rec("INFO", "skarv 1: ingen tidigare snapshot", "detta blir baslinjen")
        return
    p_rows = prev.get("rows")
    p_max = prev.get("date_max")
    if p_rows is None:
        rec("INFO", "skarv 1: forra snapshot saknade radantal", "")
        return
    delta = cur.rows - p_rows
    if cur.date_max and p_max and cur.date_max < p_max:
        rec("LEAK", "skarv 1: datumspann KRYMPTE",
            f"max {p_max} -> {cur.date_max} -- parqueten tappade nyare data (G7-klassen!)")
    elif delta < 0:
        rec("LEAK", "skarv 1: radantal MINSKADE",
            f"{p_rows:,} -> {cur.rows:,} ({delta:+,}) -- tyst tapp i DW->parquet")
    elif delta == 0 and cur.date_max == p_max:
        rec("OK", "skarv 1: oforandrad (samma fonster)", f"{cur.rows:,} rader, max {cur.date_max}")
    else:
        rec("OK", "skarv 1: vaxte (vantat for vaxande fonster)",
            f"{p_rows:,} -> {cur.rows:,} ({delta:+,}), max {p_max} -> {cur.date_max}")


def compare_family(prev_all: dict, cur: SkarvMatt, fam: str):
    """Skarv 3: rapportera fakta. Dom ENDAST om SKARV3_CALIBRATED + EXPECTED satt."""
    key = cur.skarv
    if cur.distinct_entities is None and cur.rows is None:
        rec("WARN", f"{fam}: kunde ej mata output", cur.note)
        return
    rec("INFO", f"{fam}: modell-output nu",
        f"{cur.rows:,} rader, {cur.distinct_entities} KEY "
        f"({cur.extra.get('file','?')})")
    prev = prev_all.get(key) if prev_all else None
    if prev and prev.get("distinct_entities"):
        p = prev["distinct_entities"]
        c = cur.distinct_entities or 0
        d = c - p
        pct = (d / p * 100) if p else 0
        verdict = "OK" if abs(pct) < 10 else "WARN"
        rec(verdict, f"{fam}: KEY-antal {p} -> {c} ({d:+}, {pct:+.1f}%)",
            "inom 10% (sunt)" if verdict == "OK" else
            "stor forandring -- vaxande data eller lacka? jamfor mot perioden")
    if not SKARV3_CALIBRATED:
        rec("INFO", f"{fam}: bortfallsdom EJ aktiv",
            "satt SKARV3_CALIBRATED + EXPECTED_RETENTION nar du mott BCG:s avsiktliga filtrering")


def take_snapshot(skarvar: list[int]) -> dict:
    snap: dict = {"created": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), "skarv": {}}
    if 1 in skarvar:
        m = measure_skarv1()
        snap["skarv"][m.skarv] = asdict(m)
    if 3 in skarvar:
        for fam in FAMILY_OUTPUT_ROOTS:
            m = measure_family_output(fam)
            snap["skarv"][m.skarv] = asdict(m)
    return snap


def main() -> int:
    ap = argparse.ArgumentParser(description="Bevarandekontroll tvars skarvarna (population in vs ut).")
    ap.add_argument("--snapshot", action="store_true", help="Mat + SPARA nulage som baslinje.")
    ap.add_argument("--skarv", type=int, default=None, choices=[1, 2, 3],
                    help="Kor bara en skarv (default: alla mätbara).")
    args = ap.parse_args()

    skarvar = [args.skarv] if args.skarv else [1, 3]   # skarv 2 kraver CSV-lasning (ramverk)

    print("=" * 72)
    print("CONSERVATION  --  overlevde populationen resan mellan skarvarna?")
    print("=" * 72)

    cur_snap = take_snapshot(skarvar)

    if args.snapshot:
        SNAPSHOT.write_text(json.dumps(cur_snap, indent=2, ensure_ascii=False), encoding="utf-8")
        section("SNAPSHOT SPARAD")
        for k, v in cur_snap["skarv"].items():
            print(f"   {k}: rows={v.get('rows')}, entities={v.get('distinct_entities')}, "
                  f"dates={v.get('date_min')}..{v.get('date_max')}")
        print(f"\n   -> {SNAPSHOT.name}. Nasta korning (utan --snapshot) jamfor mot denna.")
        return 0

    prev = None
    if SNAPSHOT.exists():
        prev = json.loads(SNAPSHOT.read_text(encoding="utf-8")).get("skarv", {})
        rec("INFO", "jamfor mot snapshot", SNAPSHOT.name)
    else:
        rec("WARN", "ingen snapshot finns", "kor --snapshot forst for att satta baslinjen")

    if 1 in skarvar:
        section("SKARV 1 -- DW -> parquet (radantal ska vaxa)")
        cur_s1 = cur_snap["skarv"].get("1_dw_to_parquet")
        if cur_s1:
            compare_skarv1(prev.get("1_dw_to_parquet") if prev else None,
                           SkarvMatt(**cur_s1))
        else:
            rec("WARN", "skarv 1: kunde ej mata parquet denna korning", "")

    if 3 in skarvar:
        section("SKARV 3 -- CSV -> modell-output (avsiktligt bortfall vs lacka)")
        for fam in FAMILY_OUTPUT_ROOTS:
            key = f"3_model_output_{fam}"
            if key in cur_snap["skarv"]:
                compare_family(prev, SkarvMatt(**cur_snap["skarv"][key]), fam)

    if 2 in skarvar or args.skarv is None:
        section("SKARV 2 -- parquet -> familje-CSV (RAMVERK)")
        rec("INFO", "skarv 2 ej byggd", "kraver lasning av familje-CSV + kunskap om "
            "aggregeringens entitetsbevarande -- ladda upp replicate_dataprep.py + en CSV "
            "for att bygga den korrekt (mat, gissa inte)")

    section("SAMMANFATTNING")
    n_leak = sum(1 for s, _, _ in ROWS if s == "LEAK")
    n_warn = sum(1 for s, _, _ in ROWS if s == "WARN")
    print(f"  LEAK={n_leak}  WARN={n_warn}")
    if n_leak:
        print("  -> LEAK: population tappades dar den skulle bevaras/vaxa. Granska skarven.")
    elif n_warn:
        print("  -> Inga lackor. WARN = saknad snapshot/okalibrerat -- las dem.")
    else:
        print("  -> Population bevarad/vaxande tvars matta skarvar.")
    return 1 if n_leak else 0


if __name__ == "__main__":
    sys.exit(main())

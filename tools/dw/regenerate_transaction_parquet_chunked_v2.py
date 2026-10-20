#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
regenerate_transaction_parquet_chunked_v2.py  --  ROBUST + RAM-SNAL (streaming concat)
======================================================================================
v2-andring mot v1: konkateneringen gar nu via pyarrow ParquetWriter (chunk-for-chunk
skrivning) i stallet for pd.concat av alla ar -- v1 byggde hela datasetet i RAM i
slutsteget, vilket slog i minnesvaggen (MemoryError pa 27M rader, ~14,8 GB+). v2 haller
ALDRIG mer an ett ars-chunk i minnet, varken vid hamtning ELLER skrivning. Sa aven
blygsam hardvara klarar full regenerering -- ingen 128 GB-VM behovs.

Chunkar per kalenderar (robust mot natverksavbrott 08S01), skriver via pyarrow (ingen
DECIMAL-inferensfalla). Aterupptagning: varje ar -> egen chunk-fil; redan klara ar
hoppas (--resume default PA).

Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB), assisterad
av Claude. Projekt: evbcgpricing FAS F (FD.17-forberedelse).

KOPIA (2026-10-20, DevOps-overlamning) -- KANONISK FOR BCG
    Kopierad byte-identiskt fran Business_Analytics@5a1062b (regenerate_transaction_parquet_chunked_v2.py,
    SHA256 F93862E610C0A218A5461B236AA05A79A91A5DCEFE0EDEF375A8975E5FD5D9BA) och andrad pa FYRA stallen,
    alla markta "KOPIA:" -- (1) data_access importeras fran egen mapp (tools/dw), ingen chdir till
    Business_Analytics, (2) default_out ar repo-relativt, (3) KOR-blocket nedan, (4) felmeddelandet vid
    import. Logiken ar orord. Originalet i Business_Analytics ar orort. Andra HAR (BCG) -- eller bada i
    samma commit-par tills BA-stadningen pensionerar originalet. Se tools/dw/README.md.

KOR (KOPIA: PowerShell fran repo-roten; tolk med pyodbc + pyarrow -- .venv fran install.py eller BA-venv;
     kontorsnat/VPN sa DW slapper in; .env = tools\dw\.env eller BCG_DW_ENV=<sokvag>):
    az login --scope https://database.windows.net/.default
    .\.venv\Scripts\python.exe tools\dw\regenerate_transaction_parquet_chunked_v2.py `
        --end 2026-05-31 `
        --out "Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\parquet\transaction_data.parquet" `
        --overwrite
    # (utelamna --end for automatiskt senaste stangda manad)
    # Normalt anropas skriptet av orchestration\runners\run_data.py (REGEN-steget), inte for hand.
"""
from __future__ import annotations
import argparse
import datetime
import glob
import os
import sys

SELECT_COLS = [
    ("ID_Billinginvoice","ID_Billinginvoice"),("ID_BillingInvoiceRows","ID_BillingInvoiceRows"),
    ("ID_Customer","ID_Customer"),("ID_Consultation","ID_Consultation"),
    ("ID_Department","ID_Department"),("ID_User","ID_User"),
    ("ID_ConsultationItemID","ID_ConsultationItemID"),("ID_Item","ID_Item"),
    ("ID_Patient","ID_Patient"),("ID_BillingInvoiceGroupandAccount","ID_BillingInvoiceGroupandAccount"),
    ("invoice_number","InvoiceNumber"),("InvoiceGroup","InvoiceGroup"),
    ("CreditNote","CreditNote"),("IsKlarnaInvoice","IsKlarnaInvoice"),
    ("InvoiceDate","InvoiceDate"),("InvoiceDueDate","InvoiceDueDate"),
    ("PaidDate","PaidDate"),("VATPercentage","VATPercentage"),
    ("DosageUnit","DosageUnit"),("NoofUnits","NoofUnits"),("Unit","Unit"),
    ("SalesExVAT","SalesExVAT"),("SalesVAT","SalesVAT"),("SalesTotal","SalesTotal"),
    ("RemoveVAT","RemoveVAT"),("RunDate","RunDate"),("ByUser","ByUser"),
    ("BillingInvoiceSecurity","BillingInvoiceSecurity"),("SoldQuantity","SoldQuantity"),
    ("PercentageChange","PercentageChange"),("PriceExVAT","PriceExVAT"),
    ("PriceWithVAT","PriceWithVAT"),("Created","Created"),("0","OnlineBookingFlag"),
]


def last_closed_month_end(today: datetime.date) -> str:
    first_this = today.replace(day=1)
    return (first_this - datetime.timedelta(days=1)).isoformat()


def col_sql() -> str:
    return ",\n    ".join((f"[{e}] AS [{a}]" if e != "0" else f"{e} AS [{a}]")
                          for e, a in SELECT_COLS)


def chunk_windows(start: str, end: str):
    s = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    y = s.year
    while datetime.date(y, 1, 1) <= e:
        cs = max(s, datetime.date(y, 1, 1))
        ce = min(e, datetime.date(y, 12, 31))
        if cs <= ce:
            yield y, cs.isoformat(), ce.isoformat()
        y += 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate parquet from DW: chunked + streaming concat (RAM-snal)")
    ap.add_argument("--start", default="2017-02-22")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-resume", action="store_true", help="Hamta om alla ar aven om chunk finns")
    ap.add_argument("--keep-chunks", action="store_true", help="Radera INTE temp-chunks efter slutfil")
    args = ap.parse_args()

    end = args.end or last_closed_month_end(datetime.date.today())
    start = args.start
    # KOPIA: repo-relativt (tools/dw -> repo-roten) i stallet for hardkodat C:\Projekt\BCG
    _here = os.path.dirname(os.path.abspath(__file__))
    _repo = os.path.dirname(os.path.dirname(_here))
    default_out = os.path.join(_repo, "Pipeline", "02. Elasticity",
                               "Sweden_Elasticity_Data_Prep_SQL", "parquet", "transaction_data_growing.parquet")
    out = args.out or default_out

    if os.path.exists(out) and not args.overwrite:
        print(f"[ERROR] {out} finns redan. --overwrite eller nytt --out. (Skyddar frusna parquet.)")
        return 2

    # KOPIA: data_access ligger bredvid denna fil (tools/dw/), inte i Business_Analytics.
    # Ingen chdir -- ett relativt --out tolkas darmed konsekvent mot anroparens CWD
    # (originalet bytte CWD mitt i; run_data skickar alltid absolut --out, sa ingen skillnad dar).
    if _here not in sys.path:
        sys.path.insert(0, _here)

    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        from data_access import get_connection, query_to_df
    except Exception as e:
        print(f"[ERROR] import misslyckades ({type(e).__name__}: {e}). "
              f"Kor med en tolk som har pyodbc + pyarrow (.venv fran install.py, eller BA-venv).")
        return 2

    tmp_dir = os.path.join(os.path.dirname(out), "_parquet_chunks_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    cols = col_sql()
    windows = list(chunk_windows(start, end))
    print(f"[RUN] fonster {start}..{end}  ({len(windows)} ars-chunks)  resume={not args.no_resume}")
    print(f"[RUN] utdata: {out}")

    # ---- FAS 1: hamta ar for ar -> en chunk-fil per ar (toppminne = ett ar) ----
    total = 0
    try:
        with get_connection() as conn:
            for y, cs, ce in windows:
                cp = os.path.join(tmp_dir, f"chunk_{y}.parquet")
                if os.path.exists(cp) and not args.no_resume:
                    try:
                        meta = pq.ParquetFile(cp).metadata
                        total += meta.num_rows
                        print(f"[SKIP] {y}: chunk finns ({meta.num_rows:,} rader)")
                        continue
                    except Exception:
                        print(f"[WARN] {y}: befintlig chunk olasbar, hamtar om")
                q = (f"SELECT\n    {cols}\nFROM dbo.Fact_BillingInvoiceRows\n"
                     f"WHERE InvoiceDate >= '{cs}' AND InvoiceDate <= '{ce}'")
                df = query_to_df(conn, q)
                n = len(df)
                total += n
                df.to_parquet(cp, index=False)   # pyarrow, ingen DECIMAL-falla
                print(f"[RUN] {y} ({cs}..{ce}): {n:,} rader -> {os.path.basename(cp)}")
                del df
    except Exception as e:
        print(f"[ERROR] hamtning misslyckades: {type(e).__name__}: {e}")
        print(f"[INFO] klara chunks ligger kvar i {tmp_dir} -- kor om for att aterupptaga.")
        return 2

    # ---- FAS 2: STROMMANDE konkatenering via pyarrow (toppminne = ett ar) ----
    chunk_files = sorted(glob.glob(os.path.join(tmp_dir, "chunk_*.parquet")))
    if len(chunk_files) != len(windows):
        print(f"[ERROR] forvantade {len(windows)} chunks men hittade {len(chunk_files)}. Kor om.")
        return 2

    print(f"[RUN] strommande konkatenering av {len(chunk_files)} chunks -> {out}")
    writer = None
    rows_written = 0
    min_d, max_d = None, None
    try:
        for f in chunk_files:
            t = pq.read_table(f)                      # ETT ars tabell i minnet
            if writer is None:
                writer = pq.ParquetWriter(out, t.schema)
            else:
                # sakra samma schema (kolumnordning) over alla ar
                t = t.select(writer.schema.names)
            writer.write_table(t)
            rows_written += t.num_rows
            # R7: spar min/max InvoiceDate utan att lasa allt
            col = t.column("InvoiceDate")
            cmin = pa.compute.min(col).as_py()
            cmax = pa.compute.max(col).as_py()
            min_d = cmin if min_d is None or (cmin and cmin < min_d) else min_d
            max_d = cmax if max_d is None or (cmax and cmax > max_d) else max_d
            del t
    except Exception as e:
        print(f"[ERROR] konkatenering misslyckades: {type(e).__name__}: {e}")
        return 2
    finally:
        if writer is not None:
            writer.close()

    size_mb = os.path.getsize(out) / 1_000_000
    print(f"[KPI] slutfil: rader={rows_written:,}  min_d={min_d}  max_d={max_d}")
    print(f"[Saved] {out}  ({size_mb:,.1f} MB)  total_hamtade={total:,}")

    if not args.keep_chunks:
        # Slutfilen ar verifierad (R7 ovan) -> stada temp
        for f in chunk_files:
            try: os.remove(f)
            except Exception: pass
        try: os.rmdir(tmp_dir)
        except Exception: pass
        print(f"[INFO] temp-chunks raderade.")
    else:
        print(f"[INFO] temp-chunks kvar i {tmp_dir} (--keep-chunks).")
    print("[DONE]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_parquet.py  --  READ-ONLY: vad innehaller transaction_data.parquet?
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)

Svarar pa tre fragor utan att skriva nagot:
  1. SCHEMA  -- vilka kolumner + datatyper (sa en farsk DW-export kan matcha exakt)
  2. SPANN   -- min/max InvoiceDate + radantal (bevisar om parquet ar fryst vid 2025-06)
  3. PROV    -- 3 exempelrader (sa vi ser faktiskt innehall, inte bara typer)

Kor (PowerShell, global Python 3.11, FRAN SQL-mappen sa relativ sokvag stammer):
    cd "C:\\Projekt\\BCG\\Pipeline\\02. Elasticity\\Sweden_Elasticity_Data_Prep_SQL"
    py -3.11 "C:\\Projekt\\BCG\\inspect_parquet.py"
"""
import sys
import duckdb

PARQUET = "parquet/transaction_data.parquet"

def main():
    try:
        con = duckdb.connect()
    except Exception as e:
        print(f"[ERROR] kunde inte starta duckdb: {e}")
        return 2

    print(f"[RUN] inspekterar: {PARQUET}\n")

    # 1. SCHEMA
    print("=" * 70)
    print("1) SCHEMA (kolumn -> typ)")
    print("=" * 70)
    try:
        schema = con.sql(f"DESCRIBE SELECT * FROM read_parquet('{PARQUET}')").df()
        for _, r in schema.iterrows():
            print(f"  {str(r['column_name']):<28} {r['column_type']}")
    except Exception as e:
        print(f"[ERROR] schema misslyckades: {type(e).__name__}: {e}")
        return 2

    cols = set(schema["column_name"].tolist())

    # 2. SPANN -- bara om InvoiceDate finns
    print("\n" + "=" * 70)
    print("2) DATUMSPANN + RADANTAL")
    print("=" * 70)
    if "InvoiceDate" in cols:
        try:
            span = con.sql(
                f"SELECT MIN(InvoiceDate) AS min_d, MAX(InvoiceDate) AS max_d, "
                f"COUNT(*) AS n_rows FROM read_parquet('{PARQUET}')"
            ).df()
            print(span.to_string(index=False))
        except Exception as e:
            print(f"[ERROR] spann misslyckades: {type(e).__name__}: {e}")
    else:
        print("  InvoiceDate saknas i parquet -- listar datumliknande kolumner:")
        for c in cols:
            if any(k in c.lower() for k in ("date", "datum", "invoice", "period")):
                print(f"    kandidat: {c}")

    # 3. PROV
    print("\n" + "=" * 70)
    print("3) PROV (3 rader)")
    print("=" * 70)
    try:
        sample = con.sql(f"SELECT * FROM read_parquet('{PARQUET}') LIMIT 3").df()
        print(sample.to_string())
    except Exception as e:
        print(f"[ERROR] prov misslyckades: {type(e).__name__}: {e}")

    print("\n[DONE]")
    return 0

if __name__ == "__main__":
    sys.exit(main())

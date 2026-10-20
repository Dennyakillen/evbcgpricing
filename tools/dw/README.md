# tools/dw — DW-åtkomst och parquet-regenerering (bränsleledets REGEN-steg)

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Skapad:** 2026-10-20 (DevOps-överlämning). Mappen gör BCG-repot självförsörjande på kod för
steget *DW → `transaction_data.parquet`*; tidigare pekade `orchestration/runners/run_data.py` på
filer i ett annat repo (`Business_Analytics`), som en frisk klon inte har.

## Innehåll och härkomst

| Fil | Härkomst | Ändrat mot originalet |
|---|---|---|
| `regenerate_transaction_parquet_chunked_v2.py` | kopia av `Business_Analytics@5a1062b`, SHA256 `F93862E6…D5D9BA` | fyra ställen, alla märkta `KOPIA:` — import av `data_access` från egen mapp (ingen `chdir`), repo-relativ `default_out`, KÖR-blocket, felmeddelandet vid import. Logiken orörd. |
| `data_access.py` | kopia av `Business_Analytics@1988445`, SHA256 `D74F90BF…AF0A3C` | två ställen, märkta `KOPIA:` — `import os` och `.env`-sökvägen (`BCG_DW_ENV`). Logiken orörd. |
| `.env.example` | ny | mall för `.env` (platshållare; `.env` är gitignorerad och committas aldrig) |

Originalen i `Business_Analytics` är orörda. **Regel tills vidare:** ändra här (BCG) — eller båda
kopiorna i samma commit-par. Två kopior är ett *dokumenterat* tillstånd (hash ovan), inte en tyst
drift; när `Business_Analytics` städas eller lämnas över avgörs där om originalet pensioneras.

## Förutsättningar (arvtagarens checklista)

- **Tolk med `pyodbc` + `pyarrow` + `pandas`**: repots `.venv` (byggd av `install.py` ur
  `requirements-local.txt`) räcker. Reserv: en annan tolk via `BCG_DW_PYTHON`.
- **ODBC Driver 17 for SQL Server** — systeminstallation (IT-policy, inte pip).
- **Nätverk:** DW nås bara från kontorsnät/VPN.
- **Token:** `az login --scope https://database.windows.net/.default` (giltig ~4 h, Conditional Access).
- **`.env`:** kopiera `tools\dw\.env.example` → `tools\dw\.env` och fyll i `FABRIC_SERVER`,
  `FABRIC_DATABASE`, `FABRIC_DRIVER`. Värdena finns hos den som förvaltar DW (IT) — de står
  avsiktligt inte i repot. Alternativ: `BCG_DW_ENV=<sökväg till en befintlig .env>`.

## Styrning via miljövariabler (alla valfria)

| Variabel | Betydelse | Default |
|---|---|---|
| `BCG_DW_ENV` | sökväg till `.env` för `data_access.py` | `tools\dw\.env` |
| `BCG_DW_PYTHON` | tolk som kör REGEN (måste ha pyodbc) | tolken som kör `run_data.py` om den har pyodbc, annars `Business_Analytics\.venv` om den finns |
| `BCG_REGEN_SCRIPT` | annat regen-skript än kopian här | `tools\dw\regenerate_transaction_parquet_chunked_v2.py` |

## Köra

Normalt via orkestreraren (den sätter `--out` till den parquet som PREP läser):

```powershell
py -3.11 orchestration\runners\run_data.py --dry-run --end 2026-05-31    # visa planen
py -3.11 orchestration\runners\run_data.py --end 2026-05-31              # REGEN -> PREP -> UPLOAD
```

För hand (sällan): se KÖR-blocket i `regenerate_transaction_parquet_chunked_v2.py`.

## Kvitto efter ändring

`py -3.11 verify_tool\dry_run_full_pipeline.py` ska ge `OK` för `skript: regen (tools/dw)` och
`skript: data_access (tools/dw)`; `BA-venv python (reserv)` får vara `warn` på en dator utan
`Business_Analytics`.

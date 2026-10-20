"""
Data access — Azure SQL via AAD-token (DefaultAzureCredential).

Tunn infrastrukturmodul för Business_Analytics-repot. Innehåller endast
återanvändbar datalager-funktionalitet, ingen domänlogik. Queries och
ladd-funktioner specifika för veterinärdomänen (smådjur, kliniker, etc.)
ligger i respektive metodfolders analyses/-subfolder.

Publikt API:
    get_connection() -> pyodbc.Connection
    query_to_df(conn, sql, params=None) -> pd.DataFrame

Förutsättningar:
    - .env i repots root med FABRIC_SERVER, FABRIC_DATABASE, FABRIC_DRIVER
    - Azure CLI inloggad (az login --scope https://database.windows.net/.default)
    - ODBC Driver 17 for SQL Server installerad
    - Token är giltig ~4h pga Conditional Access; modulen kastar RuntimeError
      med exakt åtgärdsinstruktion om token saknas eller gått ut.

Notering om numeriska typer:
    pyodbc returnerar SQL DECIMAL som Python decimal.Decimal — scipy-funktioner
    bryter mot dessa. Casta i anropande kod:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

Utvecklare: Jens Palmö

KOPIA (2026-10-20, DevOps-överlämning) — KANONISK FÖR BCG
    Kopierad byte-identiskt från Business_Analytics@1988445 (data_access.py,
    SHA256 D74F90BF91173236634CBBF1F35B029C0A520DE892E592A6CE46605C05AF0A3C) och ändrad på TVÅ
    ställen, märkta "KOPIA:" — `import os` samt .env-sökvägen, som kan styras med miljövariabeln
    BCG_DW_ENV (default: .env bredvid denna fil, tools/dw/.env, gitignorerad). Logiken är orörd.
    Originalet i Business_Analytics är orört.
    Ändra HÄR (BCG) — eller båda i samma commit-par tills BA-städningen pensionerar originalet.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

import pandas as pd
import pyodbc
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential


__author__ = "Jens Palmö"


# ---------------------------------------------------------------------------
# Konstanter
# ---------------------------------------------------------------------------

_TOKEN_SCOPE = "https://database.windows.net/.default"
_SQL_COPT_SS_ACCESS_TOKEN = 1256  # pyodbc-attribut för AAD-token
# KOPIA: tools/dw/.env (kopiera .env.example; gitignorerad) eller BCG_DW_ENV=<sökväg till .env>,
# t.ex. en befintlig Business_Analytics\.env på en dator som redan har den.
_ENV_PATH = Path(os.environ.get("BCG_DW_ENV") or (Path(__file__).parent / ".env"))


# ---------------------------------------------------------------------------
# Publikt API
# ---------------------------------------------------------------------------

def get_connection() -> pyodbc.Connection:
    """Öppnar anslutning mot Azure SQL via AAD-token.

    Returnerar
    ----------
    pyodbc.Connection
        Aktiv anslutning. Använd som context manager för att säkra stängning:

            with get_connection() as conn:
                df = query_to_df(conn, "SELECT ...")

    Höjer
    -----
    RuntimeError
        Om token inte kan hämtas (Azure CLI ej inloggad eller token utgången).
        Felmeddelandet innehåller exakta az login-kommandon att köra.
    FileNotFoundError
        Om .env saknas i repots root.
    KeyError
        Om .env saknar obligatoriska nycklar (FABRIC_SERVER, FABRIC_DATABASE,
        FABRIC_DRIVER).
    """
    config = _load_env(_ENV_PATH)
    token_struct = _get_token_struct()
    connection_string = _build_connection_string(config)
    return pyodbc.connect(
        connection_string,
        attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: token_struct},
    )


def query_to_df(
    conn: pyodbc.Connection,
    sql: str,
    params: tuple | None = None,
) -> pd.DataFrame:
    """Kör SQL och returnerar resultatet som DataFrame.

    Parametrar
    ----------
    conn : pyodbc.Connection
        Aktiv anslutning från get_connection().
    sql : str
        SQL-fråga. Använd ? som platshållare vid parametriserad query.
    params : tuple eller None
        Värden till platshållare. Skydd mot SQL injection när SQL byggs
        dynamiskt.

    Returnerar
    ----------
    pd.DataFrame
        Resultatet. DECIMAL-kolumner kommer som decimal.Decimal — casta
        explicit till float i anropande kod om scipy/numpy ska användas.

    Exempel
    -------
    >>> with get_connection() as conn:
    ...     df = query_to_df(
    ...         conn,
    ...         "SELECT * FROM Manual.Agg_Sales_ByMonthClinic WHERE SalesYearMonth >= ?",
    ...         params=(202001,),
    ...     )
    """
    cursor = conn.cursor()
    if params is None:
        cursor.execute(sql)
    else:
        cursor.execute(sql, params)
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return pd.DataFrame.from_records(rows, columns=columns)


# ---------------------------------------------------------------------------
# Interna hjälpfunktioner
# ---------------------------------------------------------------------------

def _load_env(path: Path) -> dict[str, str]:
    """Läser enkel KEY=VALUE-fil utan externa beroenden.

    Tomma rader och rader som börjar med # ignoreras. Värden trimmas men
    avkodas inte (inga quote-strippings, inga escape-sekvenser). Räcker för
    config-värden av typen connection string-komponenter.
    """
    if not path.exists():
        raise FileNotFoundError(
            f".env saknas på förväntad plats: {path}. "
            f"Kopiera .env.example till .env och fyll i värden."
        )
    config: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()
    return config


def _get_token_struct() -> bytes:
    """Hämtar AAD-token och förpackar i pyodbc-format.

    Conditional Access-policy ger token ~4h livslängd. Vid utgång eller
    saknad session kastar denna funktion RuntimeError med exakta
    åtgärdsinstruktioner istället för rå AADSTS-kod.
    """
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token(_TOKEN_SCOPE)
    except (ClientAuthenticationError, CredentialUnavailableError) as e:
        raise RuntimeError(
            "Azure-token kunde inte hämtas eller har gått ut.\n"
            "Detta händer normalt var fjärde timme pga Conditional Access.\n\n"
            "Kör i denna ordning för att förnya:\n"
            "    az login --scope https://management.core.windows.net//.default\n"
            "    az login --scope https://database.windows.net/.default\n\n"
            f"Originalfel: {e}"
        ) from e

    token_bytes = token.token.encode("UTF-16-LE")
    return struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)


def _build_connection_string(config: dict[str, str]) -> str:
    """Bygger ODBC connection string från .env-värden.

    Krav på nycklar: FABRIC_SERVER, FABRIC_DATABASE, FABRIC_DRIVER.
    KeyError kastas med tydligt meddelande om någon saknas.
    """
    required = ("FABRIC_SERVER", "FABRIC_DATABASE", "FABRIC_DRIVER")
    missing = [key for key in required if key not in config]
    if missing:
        raise KeyError(
            f".env saknar obligatoriska nycklar: {missing}. "
            f"Se .env.example för förväntat format."
        )
    return (
        f"Driver={{{config['FABRIC_DRIVER']}}};"
        f"Server={config['FABRIC_SERVER']};"
        f"Database={config['FABRIC_DATABASE']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

"""
io_safe.py  --  atomara skrivningar + cross-row-invarianter (ateranvandbar helper)
==================================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.

INNEHALLER TVA SAKER DENNA SESSION IDENTIFIERADE SOM SAKNADE
------------------------------------------------------------
1. write_*_atomic()  -- atomar skrivning (write-rename). Loser "halv fil vid krasch".
2. assert_conservation() -- cross-row-invariant: invarianter som spanner OVER rader
   (summa bevarad, antal entiteter bevarat), ej bara per-rad-schema.

Bada ar additiva helpers -- importera och anvand vid varje skrivning/gräns. Ersatter
INTE BCG-kärnlogik; wrappar dina skrivpunkter.

KOR (som modul, ej direkt)
--------------------------
    from io_safe import write_parquet_atomic, assert_conservation
"""
from __future__ import annotations

import os
from pathlib import Path


# ===========================================================================
# DEL 1 -- ATOMARA SKRIVNINGAR (write-rename)
# ===========================================================================
def _atomic_write(write_fn, final_path, verify_fn=None):
    """Generisk write-rename. write_fn(tmp_path) skriver till temp; rename nar klart.
    verify_fn(tmp_path) -> bool: valfri kontroll INNAN rename (t.ex. radantal)."""
    final = Path(final_path)
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = final.with_suffix(final.suffix + f".tmp.{os.getpid()}")
    try:
        write_fn(tmp)
        if verify_fn is not None and not verify_fn(tmp):
            raise ValueError(f"verify_fn underkande temp-filen fore rename: {tmp.name}")
        os.replace(tmp, final)          # ATOMART -- helt eller inte alls
    finally:
        if tmp.exists():
            try: tmp.unlink()
            except OSError: pass


def write_parquet_atomic(df, final_path, min_rows=None, **kwargs):
    """Skriv parquet atomiskt. min_rows: vagra om df har farre rader (volym-grind)."""
    if min_rows is not None and len(df) < min_rows:
        raise ValueError(f"df har {len(df)} rader < min_rows={min_rows} -- vagrar skriva "
                         f"(skydd mot tyst populations-tapp, din dyraste felklass)")
    _atomic_write(lambda p: df.to_parquet(p, index=False, **kwargs), final_path)


def write_excel_atomic(df, final_path, sheet_name="Sheet1", min_rows=None, **kwargs):
    """Skriv xlsx atomiskt (output_summary etc)."""
    if min_rows is not None and len(df) < min_rows:
        raise ValueError(f"df har {len(df)} rader < min_rows={min_rows} -- vagrar skriva")
    _atomic_write(lambda p: df.to_excel(p, sheet_name=sheet_name, index=False, **kwargs), final_path)


def write_csv_atomic(df, final_path, min_rows=None, **kwargs):
    """Skriv CSV atomiskt."""
    if min_rows is not None and len(df) < min_rows:
        raise ValueError(f"df har {len(df)} rader < min_rows={min_rows} -- vagrar skriva")
    _atomic_write(lambda p: df.to_csv(p, index=False, **kwargs), final_path)


def write_text_atomic(text, final_path, encoding="utf-8"):
    """Skriv text atomiskt (governing-docs! -- LB.86: undvik halv-skriven korrupt fil)."""
    _atomic_write(lambda p: Path(p).write_text(text, encoding=encoding), final_path)


# ===========================================================================
# DEL 2 -- CROSS-ROW-INVARIANTER (invarianter som spanner over rader)
# ===========================================================================
# Pandera/schema validerar PER RAD (kolumn X icke-null, i intervall). Men vissa
# invarianter spanner OVER rader: "summan av kolumn Y ska bevaras tvars en
# transformation", "antalet distinkta entiteter ska inte minska". De maste
# kollas annorlunda -- jamfor ett AGGREGAT fore och efter.

class ConservationError(AssertionError):
    pass


def assert_sum_preserved(df_before, df_after, column, tol=0.01, label=""):
    """Invariant: summan av `column` bevaras tvars en transformation (inom tol).
    Anvand nar ett steg INTE ska andra en total (t.ex. omfordelning, ej filtrering)."""
    s_before = df_before[column].sum()
    s_after = df_after[column].sum()
    diff = abs(s_before - s_after)
    rel = diff / abs(s_before) if s_before else 0
    if rel > tol:
        raise ConservationError(
            f"{label}: summa({column}) ANDRADES {s_before:,.2f} -> {s_after:,.2f} "
            f"(diff {diff:,.2f}, {rel:.2%} > tol {tol:.2%}). Forvantad bevaring brots.")
    return True


def assert_entities_preserved(df_before, df_after, key_col, allow_loss=0, label=""):
    """Invariant: distinkta entiteter i `key_col` forsvinner inte (mer an allow_loss).
    Anvand vid grain-skifte dar entiteter SKA overleva (ej vid avsiktlig filtrering)."""
    e_before = set(df_before[key_col].dropna().unique())
    e_after = set(df_after[key_col].dropna().unique())
    lost = e_before - e_after
    if len(lost) > allow_loss:
        sample = list(lost)[:5]
        raise ConservationError(
            f"{label}: {len(lost)} entiteter i '{key_col}' forsvann (allow={allow_loss}). "
            f"Prov: {sample}. Tyst entitets-tapp -- KARN P.3-klassen.")
    return True


def assert_row_floor(df, min_rows, label=""):
    """Invariant: radantal under golv = misstankt tapp. Din 73%-drop-grind som assertion."""
    if len(df) < min_rows:
        raise ConservationError(
            f"{label}: {len(df)} rader < golv {min_rows}. Misstankt populations-tapp "
            f"(din dyraste felklass -- befordrad fran sond till invariant).")
    return True


# Demo om kord direkt
if __name__ == "__main__":
    print("io_safe.py -- importera som modul. Demo av cross-row-invariant:")
    try:
        import pandas as pd
        a = pd.DataFrame({"key": [1,2,3], "val": [10,20,30]})
        b = pd.DataFrame({"key": [1,2], "val": [10,20]})   # tappade entitet 3
        assert_entities_preserved(a, b, "key", label="demo")
    except ConservationError as e:
        print(f"  Fangade (forvantat): {e}")
    except ImportError:
        print("  (pandas ej tillgangligt for demo)")

"""
chain_population_probe.py -- folj data genom en pipeline och mat population per steg
===================================================================================
SYFTE: Nar en pipeline ger fel/tomt resultat men INTE kraschar -- hitta exakt var
populationen tappas. Reproducera logiken inline i en KOPIA, mat radantal efter varje
transformation. Tappet syns som "N -> 0" pa en specifik rad. (KARNPRINCIPER P.5,
LESSONS LB.76.) Detta ar en MALL: kopiera, fyll i stegen for din kedja.

ANVANDNING:
    1. Kopiera denna fil till en arbetsmapp (ror aldrig originalkoden den sonderar).
    2. Importera/aterskapa de transformationer du misstanker tappar data.
    3. Anropa step(df, "etikett") efter varje transformation.
    4. Kor: py -3.11 chain_population_probe.py  (eller pa VM:s venv vid Ray-behov)
    5. Las <name>_result.txt -- forsta raden dar count faller till 0 ar boven.

DESIGNPRINCIPER (varfor sa har):
    - Skriv till FIL: Ray/loggbrus begraver annars svaret i stdout.
    - Mat efter VARJE steg: "N->0 pa rad X" pinpointar, "tom till slut" gor inte det.
    - Minsta reproducerande enhet: kor for EN nyckel/grupp -- snabbt, isolerat.
    - Testa flera hypoteser i samma korning (se hypothesis()).

Utvecklare: Jens Palmo. Author: Claude (teknisk radgivare).
"""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd
from datetime import datetime


class ChainProbe:
    """Spar population genom en pipeline. Skriver tidsstamplad rapport till fil."""

    def __init__(self, name: str, result_dir: str = "."):
        self.name = name
        self.path = f"{result_dir}/{name}_result.txt"
        self.f = open(self.path, "w", encoding="utf-8")
        self._log("=" * 64)
        self._log(f"CHAIN POPULATION PROBE: {name}")
        self._log(f"Kord: {datetime.now():%Y-%m-%d %H:%M:%S}")
        self._log("=" * 64)
        self._last = None

    def _log(self, m):
        print(m)
        self.f.write(str(m) + "\n")
        self.f.flush()

    def step(self, df: pd.DataFrame, label: str, key_col: str | None = None):
        """Mat population efter ETT steg. Flaggar om radantal fallit till 0."""
        n = len(df)
        delta = "" if self._last is None else f" (delta {n - self._last:+d})"
        flag = "  <-- TAPP TILL 0!" if n == 0 and (self._last or 0) > 0 else ""
        extra = ""
        if key_col and key_col in df.columns and n > 0:
            extra = f" | unika {key_col}: {df[key_col].nunique()}"
        self._log(f"  [{label}] rader={n}{delta}{extra}{flag}")
        self._last = n
        return df  # kedjebar: tmp = probe.step(transform(x), "efter transform")

    def hypothesis(self, label: str, condition: bool, detail: str = ""):
        """Testa en rotorsaks-hypotes explicit i samma korning."""
        mark = "BEKRAFTAD" if condition else "avskriven"
        self._log(f"  [H: {label}] {mark}  {detail}")

    def note(self, m: str):
        self._log(f"  {m}")

    def done(self):
        self._log(f"\nKLAR -> {self.path}")
        self.f.close()


if __name__ == "__main__":
    # MALL-EXEMPEL (ersatt med din egen kedja):
    probe = ChainProbe("example_chain")
    df = pd.DataFrame({"key": list("aabbcc"), "week": ["2025-01-01"] * 6, "val": range(6)})
    probe.step(df, "raw", key_col="key")
    df2 = df[df["val"] > 1]
    probe.step(df2, "efter filter val>1", key_col="key")
    # Exempel pa hypotes-test (datetime/str-divergens, LB.75):
    a_week_type, b_week_type = "datetime64[ns]", "object"
    probe.hypothesis("week-typ matchar mellan grenar",
                     a_week_type == b_week_type,
                     f"a={a_week_type} vs b={b_week_type}")
    probe.done()

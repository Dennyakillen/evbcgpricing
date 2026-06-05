"""
make_smoke_control.py  --  build a smoke-test control file from OUR data_for_model.csv
Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB), with AI advisor.

Selection criterion (v3): PRICE VARIATION, not week count
    Elasticity is only measurable where PRICE moves. v2 picked the 10 KEYs with most weeks
    (most stable history) -- but a code sold at a near-constant price for 156 weeks has ~0
    price variance, so OLS returns noise (e.g. +15.0 elasticity, p=0.16). Confirmed: SBBS1625
    had CV=0.0004 / 3 unique prices and produced +15.0.
    v3 picks the 10 KEYs with the HIGHEST price coefficient of variation (std/mean of
    Regular_Price_fwbw_max_6), restricted to KEYs with full history (>=MIN_WEEKS), so the
    smoke test runs on groups where elasticity is actually identifiable.

Feature activation (unchanged from v2): model.py (utils.py l.278) selects features where
    VALUE==1. We set Regular_Price_fwbw_max_6 and Seasonality_KEY_fwbw_6 = 1 for active KEYs;
    feature flags default 0; TRAIN per KEY = verbatim model.py split logic.

Run (PowerShell, pipeline venv):
    & "C:\\Projekt\\BCG\\Pipeline\\02. Elasticity\\.venv\\Scripts\\Activate.ps1"
    python "C:\\Projekt\\BCG\\make_smoke_control.py"
"""

from pathlib import Path
import pandas as pd
import yaml

# --- Configuration -------------------------------------------------------
N_GROUPS = 10
MIN_WEEKS = 104                       # full-history floor (model.py also filters >103)
PRICE_COL = "Regular_Price_fwbw_max_6"
ACTIVE_FEATURES = ["Regular_Price_fwbw_max_6", "Seasonality_KEY_fwbw_6"]

CODE_DIR = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\code")
CONFIG   = CODE_DIR / "src" / "config.yml"
CONTROL_OUT = CODE_DIR / "control_files" / "control_file.xlsx"
# -------------------------------------------------------------------------


def main():
    with open(CONFIG, "r") as f:
        cfg = yaml.safe_load(f)

    module_path = (CONFIG.parent / cfg["module_path"]).resolve()
    data_path = (module_path / cfg["model"]["raw_input_data"].lstrip("/\\"))
    date_var = cfg["date_var"]
    dep_var = cfg["dep_var"]
    model_group = cfg["unique_key_var"]
    train_perc = cfg["train_perc"]
    test = 1 - train_perc

    print(f"data_for_model: {data_path}")
    df = pd.read_csv(data_path, encoding="cp1252", encoding_errors="ignore", low_memory=False)
    print(f"rows={df.shape[0]}  distinct {model_group}={df[model_group].nunique()}")

    # --- per-KEY: week count AND price coefficient of variation -------------------------
    df[PRICE_COL] = pd.to_numeric(df[PRICE_COL], errors="coerce")
    g = df.groupby(model_group)
    stats = pd.DataFrame({
        "weeks": g[date_var].nunique(),
        "price_mean": g[PRICE_COL].mean(),
        "price_std": g[PRICE_COL].std(),
        "unique_prices": g[PRICE_COL].nunique(),
    })
    stats["price_cv"] = stats["price_std"] / stats["price_mean"]

    # full-history KEYs only, then top-N by price variation
    eligible = stats[stats["weeks"] >= MIN_WEEKS].copy()
    eligible = eligible.sort_values("price_cv", ascending=False)
    top_keys = eligible.head(N_GROUPS).index.tolist()

    print(f"Eligible KEYs (>= {MIN_WEEKS} weeks): {len(eligible)}")
    print(f"Top {N_GROUPS} by price-CV:")
    for k in top_keys:
        r = eligible.loc[k]
        print(f"  {k}: CV={r['price_cv']:.4f}  unique_prices={int(r['unique_prices'])}  weeks={int(r['weeks'])}")

    # --- build control columns (features default 0) -------------------------------------
    control_var_list = [x for x in list(df.columns) if x not in [date_var, dep_var, model_group]]
    control_var_list.insert(0, "TRAIN")
    control_var_list.insert(0, "RUN")

    df_sorted = df.sort_values([model_group, date_var])
    control = pd.DataFrame(df_sorted[model_group].unique(), columns=[model_group])
    for col in control_var_list:
        control[col] = 0
    control["TRAIN"] = control["TRAIN"].astype(object)

    for x in control[model_group]:
        sub = df_sorted[df_sorted[model_group] == x]
        n = sub.shape[0]
        tail_n = 1 if round(n * test) == 0 else round(n * test)
        control.loc[control[model_group] == x, "TRAIN"] = sub.tail(tail_n)[date_var].iloc[0]

    control["RUN"] = "NO"
    control.loc[control[model_group].isin(top_keys), "RUN"] = "YES"

    missing = [f for f in ACTIVE_FEATURES if f not in control.columns]
    if missing:
        raise SystemExit(f"ACTIVE_FEATURES not found as columns: {missing}")
    for feat in ACTIVE_FEATURES:
        control.loc[control["RUN"] == "YES", feat] = 1

    yes = (control["RUN"] == "YES").sum()
    print(f"RUN=YES groups: {yes}  (of {len(control)})")
    sample_key = top_keys[0]
    row = control.loc[control[model_group] == sample_key].iloc[0]
    flagged = [c for c in control_var_list if c not in ("RUN", "TRAIN") and row[c] == 1]
    print(f"  {sample_key} flagged features: {flagged}")

    control.to_excel(CONTROL_OUT, index=False)
    print(f"Wrote: {CONTROL_OUT}")


if __name__ == "__main__":
    main()

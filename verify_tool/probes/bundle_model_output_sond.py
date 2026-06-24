#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bundle_model_output_sond.py  --  varfor producerar bundle model.py ingen output?
=================================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.

PROBLEM (matt 2026-06-24): bundle-modellen kor pa VM, loggar "Finished model.py in
6.57 sec", men producerar INGEN output:
  - VM output/model/ : TOM (ingen model_summary.xlsx, model_results.csv, output_summary,
    ingen automl/-mapp)
  - Bara regular_price + data_prepration-output finns (ivc_sweden_price.csv,
    data_original.csv, data_for_model.csv)
  - feature_selection korde 47s men skapade ingen automl/results/
  - model.py "korde" 6.57s men skrev inget

Tidigare jamforelse (output_summary 125 KEY, april-revenue) var en GAMMAL LOKAL fil
-- inte fran dagens korningar. De rena korningarna producerar inget pa VM.

DENNA SOND testar flera hypoteser i ETT svep (kor pa VM via ssh, las kod + data):

  H1  feature_selection skapar INTE automl/results/finalized_x -> model.py far ingen
      feature-lista -> hoppar tyst (6.57s = noll grupper).
  H2  control_file regenererades (two-pass) men ar TOM/felaktig -> feature_selection
      producerar 0 valda features -> model.py noll grupper.
  H3  data_for_model.csv saknar KEY/kolumner model.py kraver (col_type-mismatch,
      cluster-maj-klassen: No_of_Sites vs No of Sites) -> tyst filtrering till 0.
  H4  model.py:s output-sokvagar pekar nagon annanstans (skapas men ej dar vi letar).
  H5  model.py kraschar tyst INNI Ray-workers (per-grupp), huvudloggen sager "Finished"
      anda -> noll lyckade grupper, ingen output.
  H6  output_summary skapas av Step5 (xlwings, Linux-omojligt) -> finns ALDRIG pa VM,
      maste koras lokalt (cluster-monstret).

KOR (bygg lokalt, scp, kor pa VM -- ingen Ray, ingen modell-omkorning):
    (se foljebrev) -- sonden laser bara, kor inget tungt.
"""
import os
import datetime

VM_BASE = "/home/azureuser/bcg/bundle"
CODE = VM_BASE + "/code"
OUT = VM_BASE + "/output"
CFG = CODE + "/src/config.yml"


def line(c="-", n=74):
    print(c * n)


def head(t):
    print()
    line("=")
    print(t)
    line("=")


def read(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"<<KAN EJ LASA {p}: {e}>>"


def exists(p):
    return os.path.exists(p)


def finfo(p):
    if not exists(p):
        return "SAKNAS"
    st = os.stat(p)
    mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{st.st_size:,} B   {mt}"


def grep(text, *patterns):
    hits = []
    for i, ln in enumerate(text.splitlines(), 1):
        low = ln.lower()
        if any(pat.lower() in low for pat in patterns):
            hits.append((i, ln.strip()))
    return hits


# ---------------------------------------------------------------------------
def main():
    print("=" * 74)
    print("BUNDLE MODEL OUTPUT SOND -- varfor producerar model.py ingen output?")
    print(f"  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  VM-sida")
    print("=" * 74)

    # ---- 0. Vad FINNS i output? (faktabas) ----
    head("0. OUTPUT-INVENTERING (vad model.py + feature_selection faktiskt skapade)")
    expected = {
        "regular_price": OUT + "/regular price/ivc_sweden_price.csv",
        "data_original": OUT + "/data_original.csv",
        "data_for_model": OUT + "/data_for_model.csv",
        "automl_dir": OUT + "/model/automl",
        "automl_results": OUT + "/model/automl/results",
        "finalized_x": OUT + "/model/automl/results/finalized_x_for_models.csv",
        "control_file_results": OUT + "/model/automl/results/control_file.xlsx",
        "model_summary": OUT + "/model/model_summary.xlsx",
        "model_results": OUT + "/model/model_results.csv",
        "output_summary": OUT + "/model/output_summary.xlsx",
        "model_objects": OUT + "/model/model_objects",
    }
    for label, p in expected.items():
        print(f"  {label:22} {finfo(p)}")

    # ---- 1. data_for_model.csv -- har den KEY + rader + maj? (H3) ----
    head("1. data_for_model.csv -- model.py:s INPUT (H3: saknas KEY/kolumner/rader?)")
    dfm = OUT + "/data_for_model.csv"
    if exists(dfm):
        txt = read(dfm)
        lines = txt.splitlines()
        print(f"  rader (inkl header): {len(lines):,}")
        if lines:
            hdr = lines[0].split(",")
            print(f"  antal kolumner: {len(hdr)}")
            print(f"  header (forsta 15): {hdr[:15]}")
            # finns KEY, Regular_Price, Bundle_visits, week?
            for col in ["KEY", "Regular_Price_fwbw_max_6", "Bundle_visits",
                        "week_starting_monday", "Seasonality_KEY_fwbw_6", "FTE_Interpolated"]:
                present = any(col == h.strip() or col in h for h in hdr)
                print(f"    {'OK ' if present else 'SAKNAS'} kolumn: {col}")
            # max-vecka -> ar det maj?
            try:
                wi = [i for i, h in enumerate(hdr) if "week_starting_monday" in h.strip()][0]
                weeks = sorted({l.split(",")[wi] for l in lines[1:] if len(l.split(",")) > wi})
                print(f"  veckospann: {weeks[0]} -> {weeks[-1]}  ({'MAJ' if weeks[-1] >= '2026-05' else 'EJ MAJ -> ' + weeks[-1]})")
            except Exception as e:
                print(f"  (kunde ej lasa veckospann: {e})")
            # antal unika KEY
            try:
                ki = [i for i, h in enumerate(hdr) if h.strip() == "KEY"][0]
                keys = {l.split(",")[ki] for l in lines[1:] if len(l.split(",")) > ki}
                print(f"  unika KEY i data_for_model: {len(keys)}")
            except Exception:
                pass
    else:
        print("  data_for_model.csv SAKNAS -> data_prepration producerade inget for model.py")

    # ---- 2. finalized_x / control_file -- feature_selection-output (H1/H2) ----
    head("2. feature_selection-output (H1: finalized_x saknas? H2: control_file tom?)")
    fx = OUT + "/model/automl/results/finalized_x_for_models.csv"
    cf = OUT + "/model/automl/results/control_file.xlsx"
    print(f"  finalized_x_for_models.csv : {finfo(fx)}")
    print(f"  control_file.xlsx (results): {finfo(cf)}")
    if exists(fx):
        txt = read(fx)
        lines = txt.splitlines()
        print(f"  finalized_x rader: {len(lines)}")
        if lines:
            print(f"  header: {lines[0][:120]}")
            if len(lines) <= 1:
                print("  >> H1/H2 STARKT: finalized_x har 0 datarader -> model.py far inga features -> noll grupper")
    else:
        print("  >> H1 STARKT: finalized_x SAKNAS -> feature_selection skrev aldrig vald-feature-listan")
        print("     -> model.py har inget att modellera -> 'Finished in 6.57s' = noll grupper")

    # ---- 3. Vad SKRIVER model.py + var? (H4) las koden ----
    head("3. model.py -- vad skriver den och vart? (H4: fel sokvag?)")
    mpy = CODE + "/model.py"
    if exists(mpy):
        txt = read(mpy)
        print("  --- to_csv/to_excel/save i model.py ---")
        for ln, t in grep(txt, "to_csv", "to_excel", ".save", "output_summary", "model_summary", "model_results"):
            print(f"    L{ln}: {t[:110]}")
        print("  --- hur model.py valjer grupper (KEY-loop) ---")
        for ln, t in grep(txt, "model_group", "groupby", "unique", "for ", "ray.get", ".remote"):
            print(f"    L{ln}: {t[:110]}")
        # laser model.py finalized_x eller control_file?
        print("  --- vad model.py LASER ---")
        for ln, t in grep(txt, "read_csv", "read_excel", "finalized", "control_file", "data_for_model"):
            print(f"    L{ln}: {t[:110]}")
    else:
        print(f"  model.py SAKNAS pa {mpy}")

    # ---- 4. feature_selection.py -- skapar den automl/results? (H1) ----
    head("4. feature_selection.py -- skapar den finalized_x/automl-output? (H1)")
    fpy = CODE + "/feature_selection.py"
    if exists(fpy):
        txt = read(fpy)
        for ln, t in grep(txt, "to_csv", "to_excel", "finalized_x", "automl", "results", "makedirs", "mkdir"):
            print(f"    L{ln}: {t[:110]}")
    else:
        print(f"  feature_selection.py SAKNAS")

    # ---- 5. launcher.py -- vilka steg, och fangar den krascher? (H5) ----
    head("5. launcher.py -- stegordning + felhantering (H5: tyst per-grupp-krasch?)")
    lpy = CODE + "/launcher.py"
    if exists(lpy):
        txt = read(lpy)
        for ln, t in grep(txt, "model.py", "feature_selection", "subprocess", "returncode",
                          "check", "Error", "except", "stopping"):
            print(f"    L{ln}: {t[:110]}")

    # ---- 6. output_summary -- skapas av model.py eller Step5? (H6) ----
    head("6. output_summary -- skapas av model.py eller data_prep_after_model_output? (H6)")
    for fn in ["model.py", "data_prep_after_model_output.py"]:
        p = CODE + "/" + fn
        if exists(p):
            txt = read(p)
            hits = grep(txt, "output_summary")
            if hits:
                print(f"  {fn} NAMNER output_summary:")
                for ln, t in hits:
                    print(f"    L{ln}: {t[:110]}")
            else:
                print(f"  {fn}: namner INTE output_summary")
    s5 = CODE + "/data_prep_after_model_output.py"
    if exists(s5):
        txt = read(s5)
        xlw = grep(txt, "xlwings", "xw.", "import xlwings")
        if xlw:
            print("  >> H6: data_prep_after_model_output anvander xlwings (Linux-omojligt)")
            print("     -> om output_summary skapas HAR, maste Step5 koras lokalt (cluster-monstret)")

    # ---- SLUTSATS ----
    head("SLUTSATS -- vilken hypotes haller?")
    print("  Las ovan:")
    print("  - Sektion 0+2: finns finalized_x? Om SAKNAS -> H1 (feature_selection skrev")
    print("    aldrig vald-feature-listan -> model.py noll grupper -> 6.57s, ingen output).")
    print("  - Sektion 1: har data_for_model maj + KEY? Om EJ MAJ/0 KEY -> H3 (uppstroms).")
    print("  - Sektion 3+6: skapar model.py output_summary, eller Step5? -> H4/H6.")
    print("  Atgard foljer av vilken som slar.")


if __name__ == "__main__":
    main()

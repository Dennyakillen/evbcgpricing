#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# infrastructure_map.py -- Sond 4: kartlagg och validera orkestrerings-
#                          lagret som vi byggt OVANPA BCG (Phase Z).
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Forfattare: Claude-radgivare. Sessionsdatum 2026-06-22.
#
# SYFTE (skiljt fran de tre befintliga sonderna)
#   verify_tool/probes/ validerar pipeline-KEDJAN (var data tappas, om en
#   modellmapp tal vaxande data). DEN HAR sonden validerar i stallet vart
#   EGET ORKESTRERINGSLAGER -- runners + statuskontrakt + webapp + blob/vm-
#   infrastruktur. Den svarar pa fragor som "hur hanger allt ihop?", "vem
#   ror run-nivans tillstand vs fasnivan?", och "ar nagon avslutsvag
#   asymmetrisk (staenger fasen men inte korningen)?".
#
#   Den ar AVSIKTLIGT statisk: den LASER koden (AST pa syntaxniva) men
#   KOR den ALDRIG. Darfor kraver den ingen Azure-token, ingen VM, ingen
#   Blob-access -- den fungerar aven nar az-token har dott (E.3). Mat,
#   gissa inte: slutsatserna kommer ur faktisk kallkod, inte minnesbild.
#
# VAD DEN GOR (tre lager, valj med flaggor; default = alla)
#   --map     Importgraf inom orchestration/. Visar STAMMEN (mest
#             importerade modulen = roten) och LOVEN (entry points som
#             ingen importerar). Ger en mental karta av skiktningen.
#   --mutate  Kontrakts-mutationsspar. For varje publik metod pa den
#             centrala status-klassen (default RunStatus): VAR den
#             definieras, VILKA falt den satter (klassificerat som
#             RUN-niva vs FAS-niva), och VAR i kodbasen den anropas.
#   --paths   Avslutsvag-asymmetri. I varje runner: vad anropar success-
#             vagen (finish_*/_handle_outcome 'success') jamfort med
#             felvagarna (fail/mark_waiting)? Larmar om success-vagen
#             aldrig ror run-nivan medan felvagen gor det -- den exakta
#             klass av tyst tillstandslackage vi jagar.
#
# VARFOR EN SOND OCH INTE EN ENGANGSANALYS
#   run_data.py finns redan och FD.17 ska bygga ut extraktionskedjan ->
#   infrastrukturen VAXER. En ny runner som kopieras fran en befintlig
#   arver dess avslutsmonster. Sonden kor pa nytt nar som helst och
#   larmar om en ny gren introducerar samma asymmetri. Indirekt
#   validering av setupen, ej bara ett felsoknings-engangsverktyg.
#
# ANVANDNING (global Python 3.11, ingen token behovs)
#   py -3.11 infrastructure_map.py                          # allt, mot ./orchestration
#   py -3.11 infrastructure_map.py --root <sokvag>          # peka pa annan orchestration-mapp
#   py -3.11 infrastructure_map.py --map                    # bara importgrafen
#   py -3.11 infrastructure_map.py --mutate                 # bara kontrakts-mutationer
#   py -3.11 infrastructure_map.py --paths                  # bara avslutsvag-asymmetri
#   py -3.11 infrastructure_map.py --status-class RunStatus # byt central klass om kontraktet doptes om
#
# BEROENDEN: endast Pythons standardbibliotek (ast, pathlib, argparse,
#   collections). Ingen tredjepart, ingen Azure. Kan koras var som helst.
# =====================================================================
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------
# Faltklassificering: vilka attribut pa status-objektet ar RUN-niva
# (galler hela korningen) och vilka ar FAS-niva (galler en enskild fas).
# Detta ar den enda doman-specifika kunskapen i sonden -- allt annat ar
# generell AST. Harledd ur run_status.py-kontraktet (RunStatus-faltet vs
# Phase-faltet). Om kontraktet andras: uppdatera dessa tva mangder.
# ---------------------------------------------------------------------
RUN_LEVEL_FIELDS = {
    "state", "started_at", "finished_at", "last_heartbeat",
    "current_phase_key", "error", "hint", "output_blob_paths",
    "vm_power_state",
}
# Faltnamn som ofta forekommer pa BADE run och fas (t.ex. 'state',
# 'started_at', 'finished_at', 'note'). Nar de satts pa ett loopat
# fas-objekt (p.state = ...) ar det FAS-niva; nar de satts pa self
# (self.state = ...) ar det RUN-niva. Sonden skiljer pa mottagaren.
PHASE_ALSO_FIELDS = {"state", "started_at", "finished_at", "note"}


def _iter_py_files(root: Path):
    for p in sorted(root.rglob("*.py")):
        # hoppa over uppenbara icke-moduler
        if p.name.startswith("test_"):
            yield p  # ta med tester ocksa -- de visar hur API:t ar tankt
        else:
            yield p


def _module_name(root: Path, path: Path) -> str:
    """Relativ modulnyckel, t.ex. 'runners/run_site_model' (utan .py)."""
    return str(path.relative_to(root).with_suffix("")).replace("\\", "/")


def _parse(path: Path):
    """Las + AST-parsa en fil. Returnerar (tree, kallrader) eller (None, [])
    om filen inte gar att parsa (rapporteras, blockerar inte resten)."""
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Vissa filer kan vara cp1252/utf-16 (MASTER_PYTHON-lärdomen).
        for enc in ("cp1252", "utf-16", "latin-1"):
            try:
                src = path.read_text(encoding=enc)
                break
            except Exception:
                continue
        else:
            return None, []
    try:
        return ast.parse(src), src.splitlines()
    except SyntaxError as e:
        print(f"  [varning] kunde inte parsa {path.name}: {e}")
        return None, []


# =====================================================================
# LAGER 1 -- IMPORTGRAF (stam + grenar)
# =====================================================================
def build_import_graph(root: Path):
    """Bygg en intern importgraf: modul -> vilka SYSKON-moduler den
    importerar. Endast importer som loser till en fil under orchestration/
    raknas (externa libs som flask/azure ignoreras -- vi kartlagger VAR
    arkitektur, inte tredjepart)."""
    modules = {}
    for path in _iter_py_files(root):
        tree, _ = _parse(path)
        if tree is None:
            continue
        modules[_module_name(root, path)] = (path, tree)

    # Map fran "kort modulnamn" (filename utan .py) -> full modulnyckel.
    # Runnrarna gor `from run_status import ...` (de lagger shared/ pa
    # sys.path), sa importen syns som korta namn. Vi matchar pa filnamn.
    short_to_full = defaultdict(list)
    for full in modules:
        short_to_full[full.split("/")[-1]].append(full)

    edges = defaultdict(set)       # modul -> {importerade syskon}
    imported_by = defaultdict(set) # modul -> {moduler som importerar den}

    for full, (path, tree) in modules.items():
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module.split(".")[-1])
            elif isinstance(node, ast.Import):
                for a in node.names:
                    names.append(a.name.split(".")[-1])
            for short in names:
                for target in short_to_full.get(short, []):
                    if target != full:
                        edges[full].add(target)
                        imported_by[target].add(full)
    return modules, edges, imported_by


def print_import_graph(modules, edges, imported_by):
    print("=" * 70)
    print("LAGER 1 -- IMPORTGRAF (intern; externa libs utelamnade)")
    print("=" * 70)

    # Stam = mest importerade modulerna. Lov = entry points (ingen importerar dem).
    ranked = sorted(modules, key=lambda m: (-len(imported_by[m]), m))
    print("\nSTAM (mest importerade -- arkitekturens karna):")
    for m in ranked:
        n = len(imported_by[m])
        if n == 0:
            continue
        importers = ", ".join(sorted(x.split("/")[-1] for x in imported_by[m]))
        print(f"  {m:<34} <- {n} importorer: {importers}")

    print("\nLOV (entry points -- ingen intern modul importerar dem):")
    for m in ranked:
        if len(imported_by[m]) == 0:
            deps = ", ".join(sorted(x.split("/")[-1] for x in edges[m])) or "(inga interna importer)"
            print(f"  {m:<34} -> {deps}")

    print("\nFULL GRAF (modul -> interna beroenden):")
    for m in sorted(modules):
        deps = sorted(edges[m])
        if deps:
            print(f"  {m}")
            for d in deps:
                print(f"       -> {d}")


# =====================================================================
# LAGER 2 -- KONTRAKTS-MUTATIONSSPAR
# =====================================================================
def _receiver_name(target: ast.AST) -> str | None:
    """For ett tilldelningsmal som x.y, returnera mottagaren 'x' (som text).
    self.state -> 'self'; p.state -> 'p'. Annars None."""
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
        return target.value.id
    return None


def _attr_name(target: ast.AST) -> str | None:
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def analyze_status_methods(modules, status_class: str):
    """Hitta status-klassens metoddefinitioner och klassificera vad varje
    metod muterar: RUN-niva (self.<run-falt>) vs FAS-niva (loopad p.<falt>).
    Returnerar dict: metodnamn -> {'run': set, 'phase': set, 'calls': set}."""
    methods = {}
    for full, (path, tree) in modules.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == status_class:
                for item in node.body:
                    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    run_fields, phase_fields, calls = set(), set(), set()
                    for sub in ast.walk(item):
                        # Tilldelningar: self.x = ...  /  p.x = ...
                        if isinstance(sub, ast.Assign):
                            for tgt in sub.targets:
                                recv, attr = _receiver_name(tgt), _attr_name(tgt)
                                if attr is None:
                                    continue
                                if recv == "self" and attr in RUN_LEVEL_FIELDS:
                                    run_fields.add(attr)
                                elif recv and recv != "self":
                                    # loopad mottagare (p.state etc) = fasniva
                                    phase_fields.add(attr)
                        # Metodanrop inom metoden: self.beat() etc
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                            if isinstance(sub.func.value, ast.Name) and sub.func.value.id == "self":
                                calls.add(sub.func.attr)
                    methods[item.name] = {
                        "run": run_fields, "phase": phase_fields,
                        "calls": calls, "where": _module_name(path.parent.parent if False else path.parent.parent, path) if False else full,
                    }
    return methods


def find_method_callsites(modules, status_class: str, method_names: set):
    """Var i kodbasen anropas varje status-metod? Vi letar efter <obj>.<metod>(
    dar metoden ar en av kontraktets. Vi vet inte statiskt att <obj> ar en
    RunStatus, men i den har kodbasen ar konventionen 'rs' -- vi rapporterar
    mottagarnamnet sa du ser om det ser ratt ut."""
    callsites = defaultdict(list)  # metod -> [(modul, mottagare, radnr)]
    for full, (path, tree) in modules.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if attr in method_names:
                    recv = node.func.value.id if isinstance(node.func.value, ast.Name) else "?"
                    callsites[attr].append((full, recv, getattr(node, "lineno", 0)))
    return callsites


def print_mutations(modules, status_class: str):
    print("\n" + "=" * 70)
    print(f"LAGER 2 -- KONTRAKTS-MUTATIONSSPAR (klass: {status_class})")
    print("=" * 70)
    methods = analyze_status_methods(modules, status_class)
    if not methods:
        print(f"  Hittade ingen klass '{status_class}'. Ange ratt med --status-class.")
        return
    print("\nVad varje kontraktsmetod muterar (RUN-niva = hela korningen, "
          "FAS = en enskild fas):")
    print(f"  {'metod':<16} {'RUN-niva-falt':<34} {'FAS-falt':<22} anropar")
    print("  " + "-" * 84)
    for name in sorted(methods):
        m = methods[name]
        run = ", ".join(sorted(m["run"])) or "-"
        phase = ", ".join(sorted(m["phase"])) or "-"
        calls = ", ".join(sorted(m["calls"])) or "-"
        print(f"  {name:<16} {run:<34} {phase:<22} {calls}")

    # Den centrala fragan: vilka metoder staenger RUN-nivan (satter
    # state + finished_at pa self)? De ar de enda som far en korning att
    # sluta se 'levande' ut for frontend.
    closers = [n for n, m in methods.items()
               if "state" in m["run"] and "finished_at" in m["run"]]
    print("\n  RUN-NIVA-STAENGARE (satter bade self.state och self.finished_at):")
    print(f"    {', '.join(sorted(closers)) or '(INGEN -- det vore en designlucka)'}")

    # Anropsstallen for varje metod (sarskilt staengarna)
    callsites = find_method_callsites(modules, status_class, set(methods))
    print("\n  ANROPSSTALLEN per metod (modul : mottagare @ rad):")
    for name in sorted(callsites):
        marker = "  <-- RUN-staengare" if name in closers else ""
        print(f"    {name}{marker}")
        for mod, recv, ln in sorted(callsites[name]):
            # utelamna defintionen i sjalva kontraktet (self-anrop dar)
            if mod.endswith(status_class.lower()) or "run_status" in mod:
                continue
            print(f"        {mod} : {recv} @ rad {ln}")
    return methods, closers, callsites


# =====================================================================
# LAGER 3 -- AVSLUTSVAG-ASYMMETRI (per runner)
# =====================================================================
# Vilka kontraktsmetoder hor till "stang korningen rent"? Vi vill se om
# success-vagen och fel-vagen behandlar run-nivan olika.
def analyze_runner_paths(modules, status_class: str, closers: set):
    """For varje modul som ser ut som en runner (har bade finish_success
    ELLER _handle_outcome OCH fail/mark_waiting-anrop), samla vilka
    kontraktsmetoder som anropas i success- resp fel-relaterade funktioner."""
    # Bygg per-funktion karta over vilka rs.<metod>() som anropas.
    results = {}
    for full, (path, tree) in modules.items():
        if not full.startswith("runners/"):
            continue
        per_func = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                called = set()
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                        # rs.finish_phase(...) etc -- mottagare valfri, metod intressant
                        called.add(sub.func.attr)
                per_func[node.name] = called
        if per_func:
            results[full] = per_func
    return results


def print_paths(modules, status_class: str, closers):
    closers = set(closers)
    print("\n" + "=" * 70)
    print("LAGER 3 -- AVSLUTSVAG-ASYMMETRI (per runner)")
    print("=" * 70)
    print("Fragan: ror SUCCESS-vagen run-nivan (anropar en RUN-staengare),")
    print("eller staenger den bara FASEN och lamnar korningen 'levande'?")
    print(f"RUN-staengare enligt lager 2: {', '.join(sorted(closers)) or '(ingen)'}\n")

    contract_methods = {"start_phase", "finish_phase", "succeed", "fail",
                        "mark_waiting", "beat", "finalize"}
    results = analyze_runner_paths(modules, status_class, closers)
    if not results:
        print("  Inga runner-moduler hittade under runners/.")
        return

    for full in sorted(results):
        print(f"  {full}")
        per_func = results[full]
        # Funktioner vi sarskilt bryr oss om
        focus = [f for f in per_func
                 if any(k in f.lower() for k in
                        ("finish", "handle_outcome", "leave_running", "main"))]
        for fn in sorted(focus):
            cm = sorted(per_func[fn] & contract_methods)
            if not cm:
                continue
            touches_closer = bool(set(cm) & closers)
            flag = "" if touches_closer else "  <-- ror INTE run-nivan"
            print(f"      {fn:<22} anropar: {', '.join(cm)}{flag}")
        # Sammanfattande dom for filen: anropar success-vagens funktion
        # (finish_success) nagon RUN-staengare?
        fs = per_func.get("finish_success", set())
        if fs:
            ok = bool(fs & closers)
            verdict = ("OK -- success-vagen staenger run-nivan"
                       if ok else
                       "LACKAGE -- success-vagen staenger FASEN men inte KORNINGEN")
            print(f"      => {verdict}")
        print()


# =====================================================================
# MAIN
# =====================================================================
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sond 4: kartlagg + validera orkestrerings-lagret (statiskt, ingen token).")
    ap.add_argument("--root", default=None,
                    help="Sokvag till orchestration/ (default: ./orchestration eller "
                         "mappen scriptet ligger bredvid).")
    ap.add_argument("--status-class", default="RunStatus",
                    help="Namnet pa den centrala status-klassen (default RunStatus).")
    ap.add_argument("--map", action="store_true", help="Bara importgrafen.")
    ap.add_argument("--mutate", action="store_true", help="Bara kontrakts-mutationer.")
    ap.add_argument("--paths", action="store_true", help="Bara avslutsvag-asymmetri.")
    args = ap.parse_args()

    # Hitta orchestration-roten robust.
    if args.root:
        root = Path(args.root)
    else:
        here = Path(__file__).resolve().parent
        cand = [Path.cwd() / "orchestration", here / "orchestration",
                here.parent / "orchestration", here.parent.parent / "orchestration"]
        root = next((c for c in cand if c.exists()), None)
        if root is None:
            print("Hittade ingen orchestration/-mapp. Ange med --root <sokvag>.")
            return 1
    root = root.resolve()
    if not root.exists():
        print(f"Sokvagen finns inte: {root}")
        return 1

    print(f"Sond 4 -- orkestrerings-karta")
    print(f"Rot: {root}")
    print(f"Status-klass: {args.status_class}\n")

    modules, edges, imported_by = build_import_graph(root)
    print(f"Hittade {len(modules)} Python-moduler under orchestration/.\n")

    run_all = not (args.map or args.mutate or args.paths)
    closers = set()

    if run_all or args.map:
        print_import_graph(modules, edges, imported_by)

    if run_all or args.mutate:
        res = print_mutations(modules, args.status_class)
        if res:
            _, closers, _ = res

    if run_all or args.paths:
        # behover closers fran lager 2; om bara --paths kordes, rakna dem snabbt
        if not closers:
            methods = analyze_status_methods(modules, args.status_class)
            closers = {n for n, m in methods.items()
                       if "state" in m["run"] and "finished_at" in m["run"]}
        print_paths(modules, args.status_class, closers)

    print("\n" + "=" * 70)
    print("Klart. Detta ar en STATISK lasning -- den kor ingen kod, ror ingen")
    print("VM/Blob, och kraver ingen az-token. Anvand domen i lager 3 som")
    print("riktning, verifiera sedan mot faktisk statusfil nar token ar levande.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

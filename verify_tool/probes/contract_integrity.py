#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# contract_integrity.py -- Sond 5: jaga TYSTA fel i orkestrerings-
#                          lagret vi byggt OVANPA BCG (Phase Z).
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Forfattare: Claude-radgivare. Sessionsdatum 2026-06-22.
#
# SYFTE (komplement till sond 4 infrastructure_map.py)
#   Sond 4 kartlade STRUKTUREN och fann run-niva-lackaget. Sond 5 jagar
#   tre KONKRETA felklasser dar tysta fel doljer sig -- den klass av fel
#   som inte kraschar utan bara ger fel/tomt resultat:
#
#   A  LIVSCYKEL  (--lifecycle)
#      Kan varje fas na ett terminalt tillstand? Finns kontraktsmetoder
#      som ALDRIG anropas (dod kod, som 'succeed' visade sig vara)?
#
#   B  KONTRAKTSDRIFT (--contract)  <-- mest varde
#      Tre stallen MASTE dela samma fas-nycklar men halls i synk for
#      hand: kontraktets default_pipeline(), webapp/story_config.STORY,
#      och webapp/app.PHASE_RECEIPT. En nyckel som finns i en men saknas
#      i en annan = fasen renderas/valideras TYST fel. Sonden korsmatchar
#      och rapporterar exakt vilken nyckel som fattas var.
#
#   C  SVALDA FEL (--swallow)
#      Varje 'except ...: pass' och 'except ...: log.warning(...)' i
#      orchestration/. Klassas som KOMMENTERAD (medveten, har forklarande
#      kommentar) vs NAKEN (oforklarad -> kandidat for tyst fel).
#
#   AVSIKTLIGT STATISK: laser kod (AST), kor den ALDRIG. Ingen az-token,
#   ingen VM, ingen Blob. Mat, gissa inte -- ur faktisk kallkod.
#
# ANVANDNING (global Python 3.11, ingen token)
#   py -3.11 contract_integrity.py                       # alla tre klasser
#   py -3.11 contract_integrity.py --root <sokvag>       # peka pa orchestration/
#   py -3.11 contract_integrity.py --lifecycle           # bara klass A
#   py -3.11 contract_integrity.py --contract            # bara klass B
#   py -3.11 contract_integrity.py --swallow             # bara klass C
#
# BEROENDEN: endast standardbibliotek (ast, pathlib, argparse, collections).
# =====================================================================
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path


# Kontraktets klassnamn + fabriksfunktion (kan overstyras om de doptes om).
STATUS_CLASS_DEFAULT = "RunStatus"
PIPELINE_FACTORY = "default_pipeline"

# Terminala fas-tillstand: en fas anses "kunna avslutas" om nagon kodvag
# satter ett av dessa pa ett fas-objekt. Harlett ur PhaseState i kontraktet.
TERMINAL_PHASE_STATES = {"SUCCEEDED", "FAILED", "SKIPPED",
                         "succeeded", "failed", "skipped"}


def _parse(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        for enc in ("cp1252", "utf-16", "latin-1"):
            try:
                src = path.read_text(encoding=enc); break
            except Exception:
                continue
        else:
            return None, []
    try:
        return ast.parse(src), src.splitlines()
    except SyntaxError as e:
        print(f"  [varning] kunde inte parsa {path.name}: {e}")
        return None, []


def _modname(root: Path, path: Path) -> str:
    return str(path.relative_to(root).with_suffix("")).replace("\\", "/")


def _load_modules(root: Path):
    mods = {}
    for p in sorted(root.rglob("*.py")):
        tree, lines = _parse(p)
        if tree is not None:
            mods[_modname(root, p)] = (p, tree, lines)
    return mods


# =====================================================================
# Hjalp: extrahera fas-nycklar ur olika konstruktioner
# =====================================================================
def _str_keys_from_dict(node: ast.Dict) -> list[str]:
    """Strangnycklar ur en dict-literal (toppniva)."""
    keys = []
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            keys.append(k.value)
    return keys


def keys_from_pipeline_factory(mods, status_class: str):
    """Las fas-nycklar ur default_pipeline(): den bygger en lista av
    Phase("<key>", ...). Vi plockar forsta strang-argumentet ur varje
    Phase(...)-anrop inuti funktionen. Returnerar (lista, modul) eller (None,None)."""
    for mod, (path, tree, _) in mods.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == PIPELINE_FACTORY:
                keys = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                            and sub.func.id == "Phase":
                        if sub.args and isinstance(sub.args[0], ast.Constant) \
                                and isinstance(sub.args[0].value, str):
                            keys.append(sub.args[0].value)
                return keys, mod
    return None, None


def keys_from_module_dict(mods, modname_suffix: str, dict_name: str):
    """Las strang-toppnycklar ur en modulniva-dict (t.ex. STORY i
    story_config, PHASE_RECEIPT i app). Returnerar (lista, modul) eller (None,None)."""
    for mod, (path, tree, _) in mods.items():
        if not mod.endswith(modname_suffix):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == dict_name \
                            and isinstance(node.value, ast.Dict):
                        return _str_keys_from_dict(node.value), mod
    return None, None


# =====================================================================
# KLASS A -- LIVSCYKEL
# =====================================================================
def klass_a_lifecycle(mods, status_class: str) -> bool:
    print("=" * 70)
    print("KLASS A -- LIVSCYKEL (terminala tillstand + dod kontraktskod)")
    print("=" * 70)
    ok_total = True

    # A.1 Alla kontraktsmetoder -- anropas de nagonstans utanfor sin egen def?
    method_defs = {}
    for mod, (path, tree, _) in mods.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == status_class:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and not item.name.startswith("_") \
                            and not isinstance(_first_deco(item), str):
                        method_defs[item.name] = mod
    # rakna anrop overallt (attribut-anrop .<metod>()), exkl. inne i kontraktet
    callcount = defaultdict(int)
    for mod, (path, tree, _) in mods.items():
        is_contract = mod == method_defs.get(next(iter(method_defs), ""), None) if method_defs else False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in method_defs:
                    # rakna inte self-anrop inne i kontraktsklassen
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                        continue
                    callcount[node.func.attr] += 1

    print("\nA.1 Kontraktsmetoder -- anropas de av nagon (utanfor self)?")
    dead = []
    for name in sorted(method_defs):
        n = callcount.get(name, 0)
        verdict = "PASS" if n > 0 else "REVIEW (DOD KOD -- anropas aldrig)"
        if n == 0:
            dead.append(name); ok_total = False
        print(f"  {name:<18} anrop={n:<3} -> {verdict}")
    if dead:
        print(f"\n  ==> DOD KONTRAKTSKOD: {', '.join(dead)}")
        print("      En metod som ingen anropar kan inte gora sitt jobb. 'succeed'")
        print("      var tankt att stanga run-nivan -- om den ar dod lacker success-vagen.")

    # A.2 Satter nagon kodvag ett terminalt fas-tillstand?
    sets_terminal = False
    for mod, (path, tree, _) in mods.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Attribute) and tgt.attr == "state":
                        val = node.value
                        txt = None
                        if isinstance(val, ast.Attribute):
                            txt = val.attr            # PhaseState.SUCCEEDED
                        elif isinstance(val, ast.Constant):
                            txt = str(val.value)
                        if txt and txt in TERMINAL_PHASE_STATES:
                            sets_terminal = True
    print("\nA.2 Satter nagon vag ett terminalt fas-tillstand (SUCCEEDED/FAILED/SKIPPED)?")
    print(f"  {'PASS -- ja' if sets_terminal else 'REVIEW -- ingen vag stanger en fas terminalt'}")
    if not sets_terminal:
        ok_total = False

    return ok_total


def _first_deco(item):
    """Returnera dekoratornamn som str om metoden ar en property/staticmethod
    (de raknas inte som anropbara kontraktsmetoder). Annars None."""
    for d in getattr(item, "decorator_list", []):
        if isinstance(d, ast.Name) and d.id in ("property", "staticmethod", "classmethod"):
            return d.id
    return None


# =====================================================================
# KLASS B -- KONTRAKTSDRIFT (mest varde)
# =====================================================================
def klass_b_contract(mods, status_class: str) -> bool:
    print("\n" + "=" * 70)
    print("KLASS B -- KONTRAKTSDRIFT (fas-nycklar maste vara identiska)")
    print("=" * 70)
    ok_total = True

    pipe_keys, pipe_mod = keys_from_pipeline_factory(mods, status_class)
    story_keys, story_mod = keys_from_module_dict(mods, "story_config", "STORY")
    recpt_keys, recpt_mod = keys_from_module_dict(mods, "app", "PHASE_RECEIPT")

    sources = []
    if pipe_keys is not None:  sources.append(("default_pipeline", pipe_mod, set(pipe_keys), pipe_keys))
    if story_keys is not None: sources.append(("STORY", story_mod, set(story_keys), story_keys))
    if recpt_keys is not None: sources.append(("PHASE_RECEIPT", recpt_mod, set(recpt_keys), recpt_keys))

    if len(sources) < 2:
        print("  Hittade farre an tva nyckelkallor -- kan inte korsmatcha.")
        return False

    print("\nFas-nyckelkallor som hittades:")
    for name, mod, kset, klist in sources:
        print(f"  {name:<16} ({mod}): {len(klist)} nycklar")
        print(f"       {', '.join(klist)}")

    # Referensmangd = default_pipeline om den finns, annars unionen.
    ref = next((s for s in sources if s[0] == "default_pipeline"), None)
    print("\nKorsmatchning (referens = "
          f"{'default_pipeline (kontraktet)' if ref else 'union av alla'}):")

    ref_set = ref[2] if ref else set().union(*[s[2] for s in sources])

    for name, mod, kset, klist in sources:
        missing = ref_set - kset          # finns i referens, saknas har
        extra = kset - ref_set            # finns har, saknas i referens
        if not missing and not extra:
            print(f"  {name:<16} -> PASS (identisk med referens)")
            continue
        ok_total = False
        print(f"  {name:<16} -> REVIEW")
        if missing:
            print(f"       SAKNAR (finns i referens, ej har): {', '.join(sorted(missing))}")
        if extra:
            print(f"       EXTRA (finns har, ej i referens):  {', '.join(sorted(extra))}")

    if not ok_total:
        print("\n  ==> En nyckel som saknas i STORY -> fasen renderas utan rubrik/text (tyst).")
        print("      En nyckel som saknas i PHASE_RECEIPT -> valideringsvyn blir tom (tyst).")
        print("      Saknat i default_pipeline men i STORY/RECEIPT -> kod for en fas som")
        print("      aldrig skapas. Avgor per fall om det ar medvetet (lokala steg utan")
        print("      verify-receipt) eller en glomska -- men gor det till ett AKTIVT beslut.")
    return ok_total


# =====================================================================
# KLASS C -- SVALDA FEL
# =====================================================================
def klass_c_swallow(mods) -> bool:
    print("\n" + "=" * 70)
    print("KLASS C -- SVALDA FEL (except pass / except log.warning)")
    print("=" * 70)
    print("Naken = ingen forklarande kommentar pa/intill raden -> kandidat for tyst fel.")
    print("Kommenterad = medveten (kommentar forklarar varfor det ar ofarligt).\n")

    naken, kommenterad = [], []
    for mod, (path, tree, lines) in mods.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            body = node.body
            # Monster 1: except ...: pass
            is_pass = len(body) == 1 and isinstance(body[0], ast.Pass)
            # Monster 2: enda satsen ar log.warning(...)/log.info(...) (svaljer -> loggar bara)
            is_logonly = (len(body) == 1 and isinstance(body[0], ast.Expr)
                          and isinstance(body[0].value, ast.Call)
                          and isinstance(body[0].value.func, ast.Attribute)
                          and body[0].value.func.attr in ("warning", "info", "debug"))
            if not (is_pass or is_logonly):
                continue
            lineno = node.lineno
            # Kommentar pa except-raden eller raden ovanfor?
            commented = False
            for probe in (lineno - 1, lineno, (body[0].lineno if body else lineno)):
                if 1 <= probe <= len(lines) and "#" in lines[probe - 1]:
                    commented = True; break
            kind = "pass" if is_pass else f"log.{body[0].value.func.attr}"
            rec = (mod, lineno, kind, (lines[lineno-1].strip() if lineno-1 < len(lines) else ""))
            (kommenterad if commented else naken).append(rec)

    print(f"NAKNA (REVIEW -- {len(naken)} st):")
    for mod, ln, kind, txt in sorted(naken):
        print(f"  {mod}:{ln}  [{kind}]  {txt[:70]}")
    if not naken:
        print("  (inga)")

    print(f"\nKOMMENTERADE (medvetna -- {len(kommenterad)} st, visas for fullstandighet):")
    for mod, ln, kind, txt in sorted(kommenterad):
        print(f"  {mod}:{ln}  [{kind}]")

    return len(naken) == 0


# =====================================================================
# MAIN
# =====================================================================
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sond 5: jaga tysta fel (livscykel, kontraktsdrift, svalda fel). Statisk, tokenfri.")
    ap.add_argument("--root", default=None, help="Sokvag till orchestration/ (auto om utelamnad).")
    ap.add_argument("--status-class", default=STATUS_CLASS_DEFAULT)
    ap.add_argument("--lifecycle", action="store_true", help="Bara klass A.")
    ap.add_argument("--contract", action="store_true", help="Bara klass B (kontraktsdrift).")
    ap.add_argument("--swallow", action="store_true", help="Bara klass C (svalda fel).")
    args = ap.parse_args()

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

    print(f"Sond 5 -- kontrakts-integritet")
    print(f"Rot: {root}\nStatus-klass: {args.status_class}\n")
    mods = _load_modules(root)
    print(f"Laste {len(mods)} Python-moduler.\n")

    run_all = not (args.lifecycle or args.contract or args.swallow)
    results = {}
    if run_all or args.lifecycle:
        results["A livscykel"] = klass_a_lifecycle(mods, args.status_class)
    if run_all or args.contract:
        results["B kontraktsdrift"] = klass_b_contract(mods, args.status_class)
    if run_all or args.swallow:
        results["C svalda fel"] = klass_c_swallow(mods)

    print("\n" + "=" * 70)
    print("SAMMANFATTNING")
    print("=" * 70)
    for k, ok in results.items():
        print(f"  {k:<22} {'PASS' if ok else 'REVIEW -- se ovan'}")
    print("\nStatisk lasning -- ingen kod kord, ingen token. REVIEW = mansklig blick")
    print("behovs; avgor om fyndet ar medvetet eller en glomska, och gor det aktivt.")
    return 0 if all(results.values()) else 2


if __name__ == "__main__":
    sys.exit(main())

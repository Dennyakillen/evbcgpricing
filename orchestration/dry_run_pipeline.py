"""
dry_run_pipeline.py -- Rör-kontroll: pekar hela pipelinen rätt? (FD.35-validering)
====================================================================================
Går igenom HELA flödet parquet -> cluster -> site -> bundle -> app UTAN tung körning.
Bevisar att rören pekar rätt och alla bitar finns -- INTE att modellen producerar
output (det kräver riktig körning). Grön/röd per kontroll.

Vad detta BEVISAR:
  - blob.py pekar på rätt konto (test)
  - Input-parqueten finns i test-kontot där VM:en förväntar bränslet
  - Fryst facit finns där bygg-1-auto-valideringen letar (per familj)
  - Statusfil kan läsas/skrivas mot test-kontot
  - Varje familje-runner importerar rent + har rätt familje-konstanter
  - Appens story_config har alla familjer

Vad detta INTE bevisar (kräver körning): att modellen räknar, att bygg 2 scp:ar,
att auto-valideringen klarar bundle-schemat. Det är imorgondagens varma körning.

KÖRS LOKALT (global py -3.11), från repo-roten:
    py -3.11 dry_run_pipeline.py

Developer: Jens Palmö (Senior Business Analyst). Author: Claude advisor, 2026-06-16.
"""
import os, sys
from pathlib import Path

os.environ.setdefault("PRICINGMODEL_AUTH", "key")
REPO = Path(r"C:\Projekt\BCG")
ORCH = REPO / "orchestration"
sys.path.insert(0, str(ORCH / "shared"))
sys.path.insert(0, str(ORCH / "infrastructure"))
sys.path.insert(0, str(ORCH / "runners"))
sys.path.insert(0, str(ORCH / "webapp"))

GREEN, RED, YEL, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
results = []
def check(label, ok, detail=""):
    mark = f"{GREEN}OK {RESET}" if ok is True else (f"{RED}FEL{RESET}" if ok is False else f"{YEL}? {RESET}")
    print(f"  [{mark}] {label}" + (f"  -- {detail}" if detail else ""))
    results.append(ok)

print("=" * 70)
print("DRY-RUN RÖR-KONTROLL: pekar hela pipelinen rätt? (ingen tung körning)")
print("=" * 70)

# ---- 1. blob.py pekar på test-kontot ----
print("\n1. KONTO (FD.35 -- ett hem)")
try:
    from blob import (STORAGE_ACCOUNT, RESOURCE_GROUP, CONTAINER_INPUT,
                      CONTAINER_OUTPUT, CONTAINER_STATUS, _client)
    check("blob.py STORAGE_ACCOUNT = evbcgpricinginput (test)",
          STORAGE_ACCOUNT == "evbcgpricinginput", STORAGE_ACCOUNT)
    check("blob.py RESOURCE_GROUP = ev-openai-swce-rg-test",
          RESOURCE_GROUP == "ev-openai-swce-rg-test", RESOURCE_GROUP)
except Exception as e:
    check("blob.py import", False, str(e))
    print("\nAvbryter -- blob.py måste importera för resten.")
    sys.exit(1)

# ---- 2. Containrar + innehåll i test-kontot ----
print("\n2. BLOB-INNEHÅLL (test-kontot)")
try:
    svc = _client()
    conts = {c.name: c for c in svc.list_containers()}
    # Input: parqueten
    inp = svc.get_container_client(CONTAINER_INPUT)
    inp_blobs = {b.name: b.size for b in inp.list_blobs()}
    has_parquet = "transaction_data.parquet" in inp_blobs
    pmb = inp_blobs.get("transaction_data.parquet", 0) / 1e6
    check(f"input/ har transaction_data.parquet", has_parquet, f"{pmb:.0f} MB")
    # Facit: pipeline/00_frozen_facit per familj
    if "pipeline" in conts:
        pl = svc.get_container_client("pipeline")
        facit = {b.name for b in pl.list_blobs(name_starts_with="00_frozen_facit/")}
        for fam in ["cluster", "site", "bundle"]:
            key = f"00_frozen_facit/{fam}/output_summary.xlsx"
            check(f"facit finns: {fam}", key in facit)
    else:
        check("pipeline-container (facit)", False, "saknas")
except Exception as e:
    check("blob-innehåll", False, str(e))

# ---- 3. Statusfil kan skrivas/läsas mot test ----
print("\n3. STATUS-KONTRAKT (kan skriva/läsa mot test)")
try:
    from run_status import default_pipeline
    from blob import write_status, read_status
    test_id = "_dryrun_probe"
    rs = default_pipeline(run_id=test_id, triggered_by="dry_run_pipeline")
    phases = [p.key for p in rs.phases]
    check("default_pipeline har bundle_model som fas", "bundle_model" in phases,
          " -> ".join(phases))
    write_status(rs)
    rs2 = read_status(test_id)
    check("status skriv+läs mot test-kontot", rs2.run_id == test_id)
    # Städa probe-filen
    try:
        svc.get_container_client(CONTAINER_STATUS).delete_blob(f"{test_id}.json")
    except Exception:
        pass
except Exception as e:
    check("status-kontrakt", False, str(e))

# ---- 4. Familje-runners importerar + rätt konstanter ----
print("\n4. FAMILJE-RUNNERS (import + familje-konstanter)")
import importlib.util
def load_runner(name):
    spec = importlib.util.spec_from_file_location(name, ORCH / "runners" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

for name, fam, expkeys, remote in [
    ("run_cluster_model", "cluster", 4180, "/home/azureuser/bcg/cluster"),
    ("run_site_model",    "site",    6624, "/home/azureuser/bcg/site"),
    ("run_bundle_model",  "bundle",  125,  "/home/azureuser/bcg/bundle"),
]:
    try:
        m = load_runner(name)
        ok_keys = getattr(m, "EXPECTED_KEYS", None) == expkeys
        ok_remote = remote in getattr(m, "REMOTE_CODE", "")
        ok_val = hasattr(m, "run_local_validation") and hasattr(m, "fetch_all_outputs")
        check(f"{name}: import + EXPECTED_KEYS={expkeys} + bygg1+2",
              ok_keys and ok_remote and ok_val,
              f"keys={getattr(m,'EXPECTED_KEYS','?')}, bygg1+2={'ja' if ok_val else 'NEJ'}")
    except Exception as e:
        check(f"{name}: import", False, str(e))

# ---- 5. App: story_config har alla familjer ----
print("\n5. APP (story_config + fas-rendering)")
try:
    import story_config as sc
    for fam in ["extraction", "cluster_model", "site_model", "bundle_model", "step6"]:
        in_story = fam in sc.STORY
        check(f"story_config STORY har {fam}", in_story)
    for fam in ["cluster_model", "site_model", "bundle_model"]:
        check(f"story_config FUNNEL har {fam}", fam in sc.FUNNEL)
except Exception as e:
    check("story_config", False, str(e))

# ---- Summering ----
print("\n" + "=" * 70)
ok = sum(1 for r in results if r is True)
bad = sum(1 for r in results if r is False)
unk = sum(1 for r in results if r not in (True, False))
print(f"RESULTAT: {GREEN}{ok} OK{RESET}, {RED}{bad} FEL{RESET}, {YEL}{unk} ?{RESET}")
if bad == 0:
    print(f"{GREEN}Alla rör pekar rätt. Redo för varm körning (imorgon).{RESET}")
    print("OBS: dry-run bevisar att rören pekar rätt + bitarna finns -- INTE att")
    print("modellen räknar/bygg 2 scp:ar/bundle-validering klarar schemat. Det är körningen.")
else:
    print(f"{RED}{bad} kontroll(er) FEL -- åtgärda före varm körning.{RESET}")
print("=" * 70)
sys.exit(0 if bad == 0 else 1)

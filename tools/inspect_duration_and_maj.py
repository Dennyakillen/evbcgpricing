# inspect_duration_and_maj.py -- READ-ONLY: hur raknas fas-duration, och vad har maj site_model nu?
import sys
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
import os
os.environ.setdefault("PRICINGMODEL_AUTH", "key")
os.environ.setdefault("PRICINGMODEL_STORAGE", "evbcgpricinginput")
import run_status as rs
import inspect

print("=== Hur raknas duration? (Phase-klass + duration_human + timing_summary) ===")
src = inspect.getsource(rs)
lines = src.splitlines()
# Visa Phase-klassen och alla duration-relaterade metoder helt
capture = False
for i, line in enumerate(lines):
    s = line.rstrip()
    if "duration_human" in s or "def duration" in s or "class Phase" in s or "timing_summary" in s:
        print(f"  L{i+1}: {s}")
        # visa nasta 6 rader for kontext
        for j in range(i+1, min(i+7, len(lines))):
            print(f"  L{j+1}: {lines[j].rstrip()}")
        print("  ---")

print("")
print("=== Maj-statusfilens site_model-tider NU ===")
from blob import read_status
r = read_status("2022-07-01_2026-05-31")
for p in r.phases:
    if p.key == "site_model":
        print(f"  site_model: state={p.state.value}")
        print(f"    started_at  = {p.started_at}")
        print(f"    finished_at = {p.finished_at}")
        print(f"    note        = {p.note}")

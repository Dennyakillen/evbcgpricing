# read_maj_site_timing.py -- READ-ONLY: vad har maj site_model for started_at/finished_at NU?
import sys, os
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
os.environ.setdefault("PRICINGMODEL_AUTH", "key")
os.environ.setdefault("PRICINGMODEL_STORAGE", "evbcgpricinginput")
from blob import read_status

r = read_status("2022-07-01_2026-05-31")
print("Run-state:", r.state.value)
print("")
for p in r.phases:
    if p.key == "site_model":
        print("site_model:")
        print("  state       =", p.state.value)
        print("  started_at  =", p.started_at)
        print("  finished_at =", p.finished_at)
        print("  duration    =", p.duration_human, "(", p.duration_seconds, "s )")
        print("  note        =", p.note)
print("")
print("Mal: duration ska bli 69 min 49 s = 4189 s (NEXT_SESSION VM-logg)")

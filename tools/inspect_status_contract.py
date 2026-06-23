# inspect_status_contract.py -- READ-ONLY: hur ser default_pipeline + I/O ut?
# Sa stadskriptet anropar kontraktet RATT, inte gissat.
import sys
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
import inspect
import run_status as rs_mod
import blob as blob_mod

print("=== default_pipeline signatur ===")
print("  " + str(inspect.signature(rs_mod.default_pipeline)))

print("")
print("=== faser som default_pipeline skapar (key, location, state) ===")
rs = rs_mod.default_pipeline(run_id="_inspect_probe")
for p in rs.phases:
    loc = getattr(p, "location", "?")
    loc = getattr(loc, "value", loc)
    st = getattr(p.state, "value", p.state)
    print("  " + str(p.key) + "  | location=" + str(loc) + "  | state=" + str(st) + "  | name=" + str(getattr(p, "name", "?")))

print("")
print("=== write_status / read_status signaturer ===")
print("  write_status: " + str(inspect.signature(blob_mod.write_status)))
print("  read_status:  " + str(inspect.signature(blob_mod.read_status)))

print("")
print("=== RunState-varden (sa finalize-utfall kanns igen) ===")
print("  " + ", ".join(s.name + "=" + repr(s.value) for s in rs_mod.RunState))
print("=== PhaseState-varden ===")
print("  " + ", ".join(s.name + "=" + repr(s.value) for s in rs_mod.PhaseState))

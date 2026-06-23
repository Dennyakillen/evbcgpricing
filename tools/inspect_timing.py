# inspect_timing.py -- READ-ONLY: hur far en fas sin korttid? Satter runnern finished_at vid lyckad korning?
import sys
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
import run_status as rs
import inspect

print("=== Phase-faltet (har det started_at + finished_at + duration?) ===")
src = inspect.getsource(rs)
# Visa duration-logiken + Phase-klassen
for marker in ["class Phase", "duration", "finished_at", "started_at", "timing_summary"]:
    print("")
    print("--- rader som namner: " + marker + " ---")
    for i, line in enumerate(src.splitlines()):
        if marker in line:
            print(f"  L{i+1}: {line.strip()}")

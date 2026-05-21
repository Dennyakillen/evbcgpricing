"""
make_smoke_control.py
---------------------
Builds a smoke-test version of the BCG model control file.

Purpose:
    The model step (model.py -> utils.model()) only iterates over groups where
    RUN == "YES" in the control file. To run a small, fast smoke test that proves
    the mechanics (data load -> Ray -> OLS regression -> Excel output) WITHOUT
    running all ~2450 groups, we keep only the first N groups as "YES" and flip
    the rest to "NO".

Design choices:
    - Reads the ORIGINAL control file, writes to a NEW file. The original
      (all groups = YES, needed for the full run) is never modified.
    - N is a single constant at the top, easy to change.
    - Prints a clear before/after summary so we verify the result instead of
      assuming it.

Developer: Jens Palmo, with AI advisor.
"""

import sys
from pathlib import Path
import pandas as pd

# --- Configuration -------------------------------------------------------
# How many groups to keep active (RUN="YES") for the smoke test.
N_GROUPS = 5

# Paths are relative to the cluster root; resolved from this script's location.
SCRIPT_DIR = Path(__file__).resolve().parent
CONTROL_DIR = SCRIPT_DIR / "code" / "control_files"
SOURCE_FILE = CONTROL_DIR / "control_file.xlsx"
SMOKE_FILE = CONTROL_DIR / "control_file_smoke.xlsx"

RUN_COL = "RUN"
KEY_COL = "KEY"
# -------------------------------------------------------------------------


def main() -> int:
    if not SOURCE_FILE.exists():
        print(f"ERROR: source control file not found: {SOURCE_FILE}")
        return 1

    df = pd.read_excel(SOURCE_FILE)
    print(f"Loaded control file: {SOURCE_FILE.name}")
    print(f"  rows (groups): {df.shape[0]}")
    print(f"  columns: {df.shape[1]}")

    if RUN_COL not in df.columns:
        print(f"ERROR: expected a '{RUN_COL}' column, found: {df.columns.to_list()[:10]} ...")
        return 1

    yes_before = (df[RUN_COL] == "YES").sum()
    print(f"  groups with RUN=YES before: {yes_before}")

    # Identify the first N groups currently set to YES; keep those, flip the rest.
    yes_index = df.index[df[RUN_COL] == "YES"].tolist()
    if len(yes_index) < N_GROUPS:
        print(f"WARNING: only {len(yes_index)} groups are YES; keeping all of them.")
    keep_index = set(yes_index[:N_GROUPS])

    df[RUN_COL] = "NO"
    df.loc[list(keep_index), RUN_COL] = "YES"

    yes_after = (df[RUN_COL] == "YES").sum()
    print(f"  groups with RUN=YES after:  {yes_after}")

    if KEY_COL in df.columns:
        kept = df.loc[df[RUN_COL] == "YES", KEY_COL].tolist()
        print(f"  kept groups: {kept}")

    df.to_excel(SMOKE_FILE, index=False)
    print(f"Wrote smoke control file: {SMOKE_FILE.name}")
    print("Original control_file.xlsx left untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
patch_step6_xlwings.py
=====================================================================
Surgically makes xlwings OPTIONAL in the working-folder copy of
Fall_Back_Logic.py, so step 6 runs to completion (producing dv8 +
Final_Fallback_Data_*.xlsx) even when xlwings is not installed.

It changes ONLY two things:
  1) `import xlwings as xw`  ->  guarded import; xw = None on failure
  2) the write_df_preserve_named_range(...) call in __main__ is wrapped
     in `if xw is not None:` so the (cosmetic) dashboard write is
     skipped when xlwings is absent.

NOTHING that produces dv8 is touched. The real output is saved on the
line ABOVE this call, so skipping it does not affect validation.

Idempotent: safe to run twice (detects already-patched state).
Operates on the WORKING COPY only - the OneDrive original is never read
or written.

Developer: Jens Palmo
Run in: project venv (.venv), AppLocker-clean:
    python patch_step6_xlwings.py
=====================================================================
"""

from pathlib import Path
import sys

TARGET = Path(
    r"C:\Projekt\BCG\_step6_run\02. Elasticity\6. Fall Back Logic\Fall_Back_Logic.py"
)

GUARD_MARKER = "xlwings is optional"

OLD_IMPORT = "import xlwings as xw\r\n"
NEW_IMPORT = (
    "try:\r\n"
    "    import xlwings as xw  # xlwings is optional - only used for the cosmetic dashboard write\r\n"
    "except ImportError:\r\n"
    "    xw = None\r\n"
)

# The call block, verbatim (CRLF), as it appears in __main__.
OLD_CALL = (
    '    write_df_preserve_named_range(\r\n'
    '    file_path=template_path,\r\n'
    '    df=dv8,\r\n'
    '    sheet_name="Raw",\r\n'
    '    named_range="raw",\r\n'
    '    start_cell="A1",\r\n'
    '    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches\r\n'
    '    # refresh_all=False,     # set True only if you want to refresh external connections too\r\n'
    '    visible=False)\r\n'
)
NEW_CALL = (
    '    if xw is not None:  # xlwings is optional - skip dashboard write if not installed\r\n'
    '        write_df_preserve_named_range(\r\n'
    '        file_path=template_path,\r\n'
    '        df=dv8,\r\n'
    '        sheet_name="Raw",\r\n'
    '        named_range="raw",\r\n'
    '        start_cell="A1",\r\n'
    '        refresh_pivots=False,   # keeps slicer state, refreshes pivot caches\r\n'
    '        # refresh_all=False,     # set True only if you want to refresh external connections too\r\n'
    '        visible=False)\r\n'
    '    else:\r\n'
    '        print("[info] xlwings not installed - skipped dashboard write (dv8 already saved).")\r\n'
)


def main() -> int:
    if not TARGET.exists():
        sys.exit(f"[FATAL] target not found: {TARGET}")

    raw = TARGET.read_bytes().decode("utf-8")

    if GUARD_MARKER in raw:
        print("[info] Already patched (guard marker present). No changes made.")
        return 0

    changes = 0

    if OLD_IMPORT in raw:
        raw = raw.replace(OLD_IMPORT, NEW_IMPORT, 1)
        changes += 1
        print("[ok] import guarded.")
    else:
        print("[warn] import line not found verbatim - skipped (already changed?).")

    if OLD_CALL in raw:
        raw = raw.replace(OLD_CALL, NEW_CALL, 1)
        changes += 1
        print("[ok] dashboard call wrapped in 'if xw is not None'.")
    else:
        print("[warn] call block not found verbatim - skipped (already changed?).")

    if changes == 0:
        print("[info] Nothing to change.")
        return 0

    TARGET.write_bytes(raw.encode("utf-8"))
    print(f"[done] {changes} change(s) written to working copy.")
    print("       Original in OneDrive untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

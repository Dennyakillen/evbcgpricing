"""
fix_config_encoding.py  --  strip BOM / normalize config.yml encoding, verify it parses
Developer: Jens Palmo (Senior Business Analyst, Evidensia), with AI advisor.

Why: PowerShell 5.1 `Set-Content -Encoding UTF8` writes a UTF-8 BOM (EF BB BF). PyYAML chokes
on a leading BOM with "mapping values are not allowed here" at line 2. This reads the file,
strips any BOM, rewrites as clean UTF-8 (no BOM), and confirms yaml.safe_load succeeds.
Content is untouched -- only the byte-level encoding/BOM is fixed.

Run (PowerShell, pipeline venv):
    & "C:\\Projekt\\BCG\\Pipeline\\02. Elasticity\\.venv\\Scripts\\Activate.ps1"
    python "C:\\Projekt\\BCG\\fix_config_encoding.py"
"""

from pathlib import Path
import yaml

CFG = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\code\src\config.yml")


def main():
    raw = CFG.read_bytes()
    print(f"File: {CFG}")
    print(f"First 4 bytes (hex): {raw[:4].hex()}")

    had_bom = False
    # UTF-8 BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
        had_bom = True
        print("Stripped UTF-8 BOM (EF BB BF)")
    # UTF-16 LE/BE BOM (in case it got worse)
    elif raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
        raw = text.encode("utf-8")
        had_bom = True
        print("Converted UTF-16 -> UTF-8")

    if not had_bom:
        print("No BOM found at start. Checking for stray BOM chars inside...")

    # Decode, strip any embedded BOM chars, normalize line endings
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\ufeff", "")  # any stray BOM anywhere

    # Write back as clean UTF-8, no BOM, LF endings
    CFG.write_bytes(text.encode("utf-8"))
    print("Rewrote as clean UTF-8 (no BOM)")

    # Verify it parses now
    with open(CFG, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print("\nYAML parses OK.")

    # Confirm the cols_needed edit survived
    # cols_needed lives under feature_selection in this config
    def find_key(d, key, path=""):
        hits = []
        if isinstance(d, dict):
            for k, v in d.items():
                if k == key:
                    hits.append((f"{path}.{k}", v))
                hits += find_key(v, key, f"{path}.{k}")
        return hits

    for p, v in find_key(cfg, "cols_needed"):
        print(f"  cols_needed{p.rsplit('cols_needed',1)[0]}: {v}")
        if "Sum_FTE_Interpolated" in v:
            print("  -> Sum_FTE_Interpolated present. Good.")
        else:
            print("  -> WARNING: Sum_FTE_Interpolated NOT in cols_needed!")


if __name__ == "__main__":
    main()

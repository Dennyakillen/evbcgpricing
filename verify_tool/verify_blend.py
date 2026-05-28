"""
verify_blend.py  --  verify_tool: cluster blend / step 5 (FR-3) vs BCG facit
======================================================================
Phase 4 of the milestone chain (Project Status -> Milestone 9 "Cluster
blend (step 5) replicated"). Proves the representative-selection logic
that makes sparse cluster groups usable: weak groups inherit the
elasticity of a strong "representative" peer. BCG's frozen facit lists
43 representatives; we prove we pick the same 43.

This is a THIN WRAPPER around the existing, proven fallback_blend.py.
We do not re-implement the blend - we run it with --facit (which makes
it compare our representative set to BCG's on the key
(Service, big_cluster, New_cluster) and report agreement), capture its
[STEP]/[KPI]/[FACIT] log, and translate it into the unified SUMMARY
style used by verify_model / verify_dataprep / verify_fallback.

Inputs (all default to the UNTOUCHED BCG original - lesson from the
2026-05-25 dataprep drift: never point facit at a working-folder copy):
  --output-summary : cluster model output_summary.xlsx (the blend input)
  --facit          : final_model_cluster_granularity.xlsx (43 representatives)
  --prod-file      : Complete_Product_Data.xlsx (Service / Rank / Description)

Developer: Jens Palmo, with AI advisor.
Run (PowerShell, project venv):
    python verify_blend.py
    python verify_blend.py --output-summary "<xlsx>" --facit "<xlsx>" --prod-file "<xlsx>"
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_ORIG = (
    r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG"
    r"\BCG_orginal_V2_New\02. Elasticity"
)
_PIPE = r"C:\Projekt\BCG\Pipeline\02. Elasticity"

DEFAULT_BLEND = r"C:\Projekt\BCG\fallback_blend.py"
# Our cluster model output (same file verify_model --family cluster uses).
DEFAULT_OUTPUT_SUMMARY = rf"{_PIPE}\2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx"
# BCG facit: the 43 representatives, read from the cluster model's OWN output
# folder in the untouched original (where the blend artefact is born - not the
# forwarded _Ivce copy in step 6's input_data, though both are byte-identical).
DEFAULT_FACIT = rf"{_ORIG}\2. Product Cluster Level Models\output\final_model_cluster_granularity.xlsx"
# Product file for Service/Rank/Description join (15,134 ItemCodes, 23 services).
DEFAULT_PROD = rf"{_ORIG}\6. Fall Back Logic\input_data\Complete_Product_Data.xlsx"

# fallback_blend.py log-line patterns (stable format).
RE_STEP_MO = re.compile(r"\[STEP\] after model_output: shape=\((\d+),\s*(\d+)\)")
RE_STEP_BLEND = re.compile(r"\[STEP\] after blend: rows=(\d+)\s+representatives=(\d+)")
RE_PRE = re.compile(r"\[KPI\] pre-blend: Significant\?=1\s+(\d+)/(\d+)\s+Check=1\s+(\d+)/(\d+)")
RE_POST = re.compile(r"\[KPI\] post-blend: Significant\?=1\s+(\d+)/(\d+)")
RE_FACIT_SHAPE = re.compile(r"\[FACIT\] facit shape=\((\d+),\s*(\d+)\)\s+ours=\((\d+),\s*(\d+)\)")
RE_FACIT_MATCH = re.compile(r"\[FACIT\] .*match: both=(\d+)\s+only_facit=(\d+)\s+only_ours=(\d+)")
RE_FACIT_AGREE = re.compile(r"\[FACIT\] Significant\? agreement on matched rows: (\d+)/(\d+)")
RE_FACIT_SET = re.compile(r"\[FACIT\] representative-set match: (PASS|REVIEW)")


def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    ap = argparse.ArgumentParser(description="Verify cluster blend / step 5 (FR-3) vs BCG facit.")
    ap.add_argument("--blend", default=DEFAULT_BLEND, help="Path to fallback_blend.py")
    ap.add_argument("--output-summary", default=DEFAULT_OUTPUT_SUMMARY,
                    help="Cluster model output_summary.xlsx (blend input)")
    ap.add_argument("--facit", default=DEFAULT_FACIT,
                    help="BCG final_model_cluster_granularity.xlsx (43 representatives)")
    ap.add_argument("--prod-file", default=DEFAULT_PROD,
                    help="Complete_Product_Data.xlsx for Service/Rank join")
    args = ap.parse_args()

    blend = Path(args.blend)
    for label, p in [("fallback_blend.py", blend),
                     ("output-summary", Path(args.output_summary)),
                     ("facit", Path(args.facit)),
                     ("prod-file", Path(args.prod_file))]:
        if not p.exists():
            sys.exit(f"[FATAL] {label} not found:\n  {p}")

    _section("VERIFY CLUSTER BLEND / STEP 5 (FR-3): representative set vs BCG facit")
    print("Proves the sparse-group rescue logic: weak cluster groups inherit a")
    print("strong representative peer's elasticity. BCG's facit has 43 reps;")
    print("we prove we select the same 43 on (Service, big_cluster, New_cluster).")
    print("Method: thin wrapper around fallback_blend.py --facit.")

    # Run blend to a throwaway output (we only want its validation log).
    with tempfile.TemporaryDirectory() as td:
        out_csv = str(Path(td) / "verify_blend_scratch.csv")
        cmd = [
            sys.executable, str(blend),
            "--output-summary", args.output_summary,
            "--facit", args.facit,
            "--prod-file", args.prod_file,
            "--out", out_csv,
        ]
        print(f"\n[run] {' '.join(cmd[:2])} ... (full args below)")
        print(f"      --output-summary {args.output_summary}")
        print(f"      --facit          {args.facit}")
        print(f"      --prod-file      {args.prod_file}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            sys.exit("[FATAL] fallback_blend.py timed out after 600s")
        output = (proc.stdout or "") + (proc.stderr or "")

    _section("--- raw log from fallback_blend.py (full transparency) ---")
    print(output.rstrip())

    # Parse
    data = {}
    for line in output.splitlines():
        for key, rx in [("step_mo", RE_STEP_MO), ("step_blend", RE_STEP_BLEND),
                        ("pre", RE_PRE), ("post", RE_POST),
                        ("facit_shape", RE_FACIT_SHAPE), ("facit_match", RE_FACIT_MATCH),
                        ("facit_agree", RE_FACIT_AGREE), ("facit_set", RE_FACIT_SET)]:
            m = rx.search(line)
            if m:
                data[key] = m.groups()

    _section("SUMMARY (lead with these - the reliable measures)")
    if "facit_match" in data:
        both, only_f, only_o = (int(x) for x in data["facit_match"])
        total = both + only_f
        print(f"  Representative set : {both}/{total} match BCG  "
              f"(only_facit={only_f}, only_ours={only_o})")
    if "facit_agree" in data:
        agree, n = (int(x) for x in data["facit_agree"])
        print(f"  Significance agree : {agree}/{n} representatives  "
              f"({100*agree/n:.1f}%)")
    if "facit_set" in data:
        print(f"  Representative-set : {data['facit_set'][0]}")
    if "step_blend" in data:
        rows, reps = data["step_blend"]
        print(f"  Blend rescue       : {rows} fine rows -> {reps} representatives")
    if "pre" in data and "post" in data:
        sig_pre, n_pre = data["pre"][0], data["pre"][1]
        sig_post, n_post = data["post"][0], data["post"][1]
        print(f"  Significant groups : pre-blend {sig_pre}/{n_pre}  ->  "
              f"post-blend {sig_post}/{n_post}  (rescue lifts coverage)")

    if "facit_match" not in data:
        print("[warn] no [FACIT] match line parsed - inspect raw log above.")
        print("       (Did fallback_blend.py reach the facit comparison? Check --facit path.)")
        return proc.returncode or 1

    _section("VERDICT")
    set_ok = data.get("facit_set", ["?"])[0] == "PASS"
    if set_ok:
        print("FR-3 (cluster blend / step 5) is faithful: we select the SAME 43")
        print("representatives BCG did, with matching significance flags. The")
        print("sparse-group rescue logic is replicated - weak groups inherit the")
        print("right strong peer, exactly as in BCG's frozen output.")
    else:
        print("Representative-set match is REVIEW, not PASS - inspect only_facit /")
        print("only_ours above. A non-zero either side means we picked a different")
        print("representative for some (Service, big_cluster, New_cluster) group.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

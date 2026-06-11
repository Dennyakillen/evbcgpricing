"""
_provenance_helpers.py
======================
Shared helpers for the DATA PROVENANCE validation suite.

This suite answers a question the other three suites do not: when the model is
NOT a fully dynamic growing pipeline -- when some Step 6 inputs are live growing
data and others are reused frozen BCG facit (a deliberate, documented shortcut to
keep momentum, see FUTURE_DEVELOPMENT) -- WHICH inputs are which? It proves, per
Step 6 input, whether the number a decision-maker sees rests on fresh growing data
or on a frozen locked assumption, and names the FD ticket for every frozen part.

It imports the base helpers from extraction_validation/_validation_helpers.py
(receipt writer, stdout capture, formatting) and overrides get_receipt_dir() so
provenance receipts land in receipts/YYYY-MM-DD/provenance/ -- separate from the
other suites under the same date, exactly as output_rationality does.

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Created:   2026-06-11

DESIGN NOTE: frozen is NOT a failure. The other suites prove correctness
(replication, rationality). This suite proves HONESTY about freshness. A frozen
input reports REVIEW ("works, but rests on a lock -- see FD"), never FAIL. That
mirrors output_rationality's "report deviations, not binary pass/fail" philosophy.
"""
import sys
from pathlib import Path

# Reuse the base helpers (one suite up, in extraction_validation/).
_THIS_DIR = Path(__file__).resolve().parent
_EXTRACTION_DIR = _THIS_DIR.parent / "extraction_validation"
sys.path.insert(0, str(_EXTRACTION_DIR))

from _validation_helpers import (  # noqa: E402
    BCG_ROOT, BUSINESS_ROOT, RECEIPT_ROOT,
    BCG_START, BCG_END,
    fmt_msek, fmt_pct, fmt_int,
    file_hash_short, now_iso, now_file_stamp,
    get_receipt_dir as _base_get_receipt_dir,
    section, subsection,
    capture_stdout, write_log_receipt,
)


def get_receipt_dir():
    """Dated receipt subfolder for PROVENANCE validation:
    verify_tool/receipts/YYYY-MM-DD/provenance/  (overrides base, like rationality)."""
    base_dir = _base_get_receipt_dir()
    prov_dir = base_dir / "provenance"
    prov_dir.mkdir(parents=True, exist_ok=True)
    return prov_dir


# ============================ STEP 6 INPUT PATHS ============================
# Mirrors Constant.py in "6. Fall Back Logic". Paths are relative to the
# Fall Back Logic parent ("02. Elasticity"); we resolve them absolutely here.
_ELAST = BCG_ROOT / "Pipeline" / "02. Elasticity"
_FBL = _ELAST / "6. Fall Back Logic"

# Where Step 6 LOOKS for each input (Constant.py paths, resolved absolute):
STEP6_EXPECTS = {
    "product_base": _FBL / "input_data" / "Complete_Product_Data.xlsx",
    "cluster_blended_output": _ELAST / "2. Product Cluster Level Models" / "output" / "final_model_cluster_granularity.xlsx",
    "cluster_blended_model": _ELAST / "2. Product Cluster Level Models" / "output" / "output_summary_ready.xlsx",
    "site_model": _ELAST / "3. Product Site Level Models" / "output" / "model" / "output_summary.xlsx",
    "bundle_model": _ELAST / "5. Bundle Clinic Models" / "output" / "model" / "output_summary.xlsx",
}

# Candidate LIVE GROWING sources we know exist (from the 2026-06 runs). The
# validator checks these and reports whether they are present to feed Step 6.
GROWING_CANDIDATES = {
    "cluster_blended_model": [
        _ELAST / "2. Product Cluster Level Models" / "_archive_growing_2026-04-27_v2_pg4fix" / "output_summary.xlsx",
    ],
    "site_model": [
        _ELAST / "3. Product Site Level Models" / "output" / "model" / "output_summary.xlsx",
        _ELAST / "3. Product Site Level Models" / "output_growing_2026-06-09" / "model" / "output_summary.xlsx",
    ],
    # NOTE: cluster_blended_output (step-5 blend, 43 reps) has NO growing candidate --
    # it exists only as frozen facit (_Ivce). Provenance found this. See FROZEN_FACIT.
}

# Frozen BCG facit we knowingly reuse as placeholders (the documented shortcut).
BCG_FBL_FACIT = (
    Path("C:/Users/jepa02/OneDrive - Evidensia Djursjukvård AB/Datastrategi/BCG")
    / "BCG_orginal_V2_New" / "02. Elasticity" / "6. Fall Back Logic"
)
FROZEN_FACIT = {
    "product_base": BCG_FBL_FACIT / "input_data" / "Complete_Product_Data.xlsx",
    "bundle_model": BCG_FBL_FACIT / "input_data" / "output_summary_bundle.xlsx",
    # Cluster step-5 blend (43 reps) exists ONLY frozen -- no growing rebuild was ever
    # produced. The only final_model_cluster_granularity in the repo is the _Ivce facit
    # (2025-12-08). Provenance discovered this: step 1-4 ran growing, step-5 blend did not.
    "cluster_blended_output": _FBL / "input_data" / "final_model_cluster_granularity_Ivce.xlsx",
}


# ============================ INPUT REGISTRY ============================
# One entry per Step 6 input. Each declares: which fallback levels it feeds,
# how to find a date in it (to prove growing vs frozen), and -- if frozen --
# the FD ticket and the business impact line for the receipt.
#
# feeds      : F1-F7 levels this input drives (per IB.2 / Constant.py rename map)
# date_col   : column to read max() from to prove the data window (None = no date col)
# expect_growing_to : a 'growing' file should reach at/after this (YYYY-MM)
INPUT_REGISTRY = [
    {
        "key": "site_model",
        "label": "Site model output (product x site)",
        "feeds": "F1 (site level)",
        "kind_expected": "LIVE GROWING",
        "date_col": "KEY",          # site output keys are Cluster-ItemCode; date proven via run timestamp
        "date_from": "timestamp",   # use file mtime as the freshness signal
        "expect_growing_to": "2026-06",
        "fd": None,
        "impact": "Site elasticities feed F1, the finest fallback level.",
    },
    {
        "key": "cluster_blended_model",
        "label": "Cluster model output (product x cluster)",
        "feeds": "F3 (cluster), F5 (product-across), F6/F7 (service)",
        "kind_expected": "LIVE GROWING",
        "date_col": "KEY",
        "date_from": "timestamp",
        "expect_growing_to": "2026-06",
        "fd": None,
        "impact": "Cluster elasticities are the backbone of the weave (F3/F5/F6/F7).",
    },
    {
        "key": "cluster_blended_output",
        "label": "Cluster step-5 blended granularity (43 reps)",
        "feeds": "service-granularity routing in step 6",
        "kind_expected": "FROZEN PLACEHOLDER",
        "date_col": None,
        "date_from": "timestamp",
        "expect_growing_to": "2026-06",
        "fd": "FD.15",
        "impact": ("Step-5 blend (43 reps / service-granularity routing) exists ONLY as "
                   "frozen BCG facit (_Ivce, 2025-12). Cluster step 1-4 ran growing, but the "
                   "step-5 blend on top was never regenerated. The routing that decides each "
                   "service's blend granularity is therefore frozen at BCG's 2025 structure."),
    },
    {
        "key": "bundle_model",
        "label": "Bundle model output (baskets / clinic)",
        "feeds": "F2 (bundle), F4 (bundle-across-clusters)",
        "kind_expected": "FROZEN PLACEHOLDER",
        "date_col": "KEY",
        "date_from": "timestamp",
        "expect_growing_to": "2026-06",
        "fd": "FD.11",
        "impact": ("Bundle model PARKED (FD.11): 98 modelled baskets = 526 M (~4.3%), "
                   "overlaps Cluster/Site. Frozen BCG facit feeds F2/F4 so the weave can "
                   "run and we can MEASURE how often bundle wins (the FD.11 revisit trigger)."),
    },
    {
        "key": "product_base",
        "label": "Product base data (weave revenue weights)",
        "feeds": "TotalNet + year-ending-2025 revenue weights (all levels)",
        "kind_expected": "FROZEN PLACEHOLDER",
        "date_col": None,
        "date_from": "yearending_colname",   # the column name itself encodes the lock year
        "expect_growing_to": "2026-06",
        "fd": "FD.14",
        "impact": ("SalesTotal_YearEnding25 is a hardcoded 2025 weight column. Even when "
                   "Cluster/Site elasticities are growing, they are revenue-WEIGHTED with "
                   "frozen 2025 turnover. Alteryx-origin file (Module 4) -- needs a growing "
                   "rebuild. Until then the weave weights are frozen."),
    },
]


# ============================ CLASSIFICATION ============================
def classify_input(entry, present_path, present_label, max_date, yearending_col):
    """Decide LIVE GROWING vs FROZEN PLACEHOLDER vs MISSING and build the evidence.

    Returns dict: kind, evidence (str), reaches (str), status (PASS/REVIEW/MISSING).
    Frozen is REVIEW (honest, documented), not FAIL. Missing is MISSING.
    """
    if present_path is None:
        return {
            "kind": "MISSING",
            "evidence": "no file found at expected or growing-candidate locations",
            "reaches": "-",
            "status": "MISSING",
        }

    # Determine the freshness signal.
    reaches = "-"
    if entry["date_from"] == "yearending_colname" and yearending_col:
        # The column name itself proves the lock year (e.g. SalesTotal_YearEnding25).
        reaches = f"col '{yearending_col}' (hardcoded 2025)"
    elif max_date is not None:
        reaches = str(max_date)[:10]

    expected_growing = entry["kind_expected"] == "LIVE GROWING"

    # A file is GROWING if it reaches >= expect_growing_to (by date or timestamp).
    is_growing = False
    if entry["date_from"] == "timestamp" and max_date is not None:
        is_growing = str(max_date)[:7] >= entry["expect_growing_to"]
    # year-ending-column inputs are frozen by construction (hardcoded year).

    if expected_growing and is_growing:
        kind = "LIVE GROWING"
        status = "PASS"
        evidence = f"reaches {reaches} >= {entry['expect_growing_to']} (growing); source={present_label}"
    elif expected_growing and not is_growing:
        # Expected growing but evidence says it isn't -> flag for review.
        kind = "FROZEN / STALE"
        status = "REVIEW"
        evidence = (f"expected growing but reaches only {reaches} (< {entry['expect_growing_to']}); "
                    f"source={present_label} -- verify this is the latest run")
    else:
        kind = "FROZEN PLACEHOLDER"
        status = "REVIEW"
        evidence = f"frozen lock at {reaches}; source={present_label}; see {entry['fd']}"

    return {"kind": kind, "evidence": evidence, "reaches": reaches, "status": status}

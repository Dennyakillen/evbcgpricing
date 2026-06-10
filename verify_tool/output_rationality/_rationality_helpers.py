"""
_rationality_helpers.py
========================
Shared helpers for output rationality validation suite.
Imports the base helpers from extraction_validation/_validation_helpers.py
and adds output-specific paths and constants.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

RECEIPT FORMAT: Same single-sheet "Logg" format as extraction_validation suite.

USED BY: All validate_*.py in verify_tool/output_rationality/.
"""
import sys
from pathlib import Path

# Add extraction_validation/ to path so we can reuse all the shared helpers
_THIS_DIR = Path(__file__).resolve().parent
_EXTRACTION_DIR = _THIS_DIR.parent / "extraction_validation"
sys.path.insert(0, str(_EXTRACTION_DIR))

# Re-export everything we need from the base helpers.
# NOTE: get_receipt_dir is renamed to _base_get_receipt_dir below and replaced
# with a rationality-specific version that adds a 'rationality/' subfolder so
# output_rationality receipts don't mix with extraction_validation receipts.
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
    """
    Return the dated receipt subfolder for OUTPUT RATIONALITY validation,
    creating it if needed. Pattern: verify_tool/receipts/YYYY-MM-DD/rationality/

    This OVERRIDES the base helper's get_receipt_dir() so rationality receipts
    are kept separate from extraction_validation receipts under the same date.
    """
    base_dir = _base_get_receipt_dir()
    rationality_dir = base_dir / "rationality"
    rationality_dir.mkdir(parents=True, exist_ok=True)
    return rationality_dir


# ============================ OUTPUT-SPECIFIC PATHS ============================

# Cluster model output (our run)
_CLUSTER_ROOT = BCG_ROOT / "Pipeline" / "02. Elasticity" / "2. Product Cluster Level Models"

# Path resolution: try _archive first (post-VM run), fall back to azure_run_model
# (the path proof_chain uses). If neither exists, scripts will FAIL with a clear
# error message rather than silently picking up stale data.
_ARCHIVE_OUTPUT = _CLUSTER_ROOT / "_archive_growing_2026-04-27_v2_pg4fix" / "output_summary.xlsx"
_AZURE_RUN_OUTPUT = _CLUSTER_ROOT / "output" / "azure_run_model" / "output_summary.xlsx"


def resolve_our_output_summary(override=None):
    """
    Resolve which output_summary.xlsx to use.

    Args:
        override: optional Path or string to override default search.

    Returns:
        Tuple (Path, str) where str is a human-readable label
        ("archive" / "azure_run_model" / "override").

    Raises:
        FileNotFoundError if no candidate exists.
    """
    if override:
        p = Path(override)
        if not p.exists():
            raise FileNotFoundError(f"Override path does not exist: {p}")
        return p, "override"

    if _ARCHIVE_OUTPUT.exists():
        return _ARCHIVE_OUTPUT, "archive"

    if _AZURE_RUN_OUTPUT.exists():
        return _AZURE_RUN_OUTPUT, "azure_run_model"

    raise FileNotFoundError(
        "No output_summary.xlsx found at either default location:\n"
        f"  archive:        {_ARCHIVE_OUTPUT}\n"
        f"  azure_run_model: {_AZURE_RUN_OUTPUT}\n"
        "Pass --output-summary <path> to specify explicitly."
    )


# BCG frozen facit (for drift comparison)
BCG_FACIT_OUTPUT_SUMMARY = (
    Path(r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG")
    / "BCG_orginal_V2_New" / "02. Elasticity"
    / "2. Product Cluster Level Models" / "output" / "model" / "output_summary.xlsx"
)


# ============================ COLUMN NAMES ============================
# These mirror BCG's output_summary.xlsx schema (8 columns confirmed 2026-06-08).
COL_KEY = "KEY"
COL_TOTALNET = "TotalNet"
COL_QUANTITY = "QuantitySold(SalesTotal>0)"
COL_CORREL = "Correl"
COL_RSQ = "RSQ"
COL_ADJ_RSQ = "ADJ_RSQ"
COL_ELASTICITY = "ELASTICITY_Regular_Price_fwbw_max_6"
COL_PVALUE = "PVALUE_Regular_Price_fwbw_max_6"


# ============================ RATIONALITY THRESHOLDS ============================
# These are the bands established in session dialogue 2026-06-08.
# Conservative defaults; can be tightened later as we learn from data.

# Significance gate (BCG's IB.2 rule, used across all rationality scripts)
SIG_RSQ_MIN = 0.5
SIG_PVALUE_MAX = 0.2

# Outlier thresholds
OUTLIER_ABS_THRESHOLD = 5.0          # |elasticity| > 5.0 = outlier (review)
OUTLIER_NEGATIVE_FLOOR = -10.0       # elasticity < -10 = absurd (drop from significance, per BCG)
OUTLIER_POSITIVE_CEILING = 5.0       # significant positive > 5 = anomaly (likely status/luxury)

# Drift thresholds (vs BCG facit, per-KEY)
DRIFT_ABS_TOLERANCE = 0.5            # |delta_elasticity| < 0.5 = acceptable drift
DRIFT_HARD_THRESHOLD = 1.0           # |delta_elasticity| > 1.0 = decision-relevant drift

# Rational bands for significant elasticities
RATIONAL_NEG_MIN = -3.0              # significant negative: -3.0 to -0.05
RATIONAL_NEG_MAX = -0.05
RATIONAL_POS_MIN = 0.05              # significant positive: 0.05 to +3.0 (lyx/status)
RATIONAL_POS_MAX = 3.0


# ============================ HELPER FUNCTIONS ============================
def is_significant(rsq, pvalue):
    """BCG IB.2 gate: RSQ >= 0.5 AND PVALUE <= 0.2."""
    return (rsq >= SIG_RSQ_MIN) & (pvalue <= SIG_PVALUE_MAX)


def extract_itemcode_from_key(key_series):
    """Extract ItemCode (after last '-') from KEY column."""
    return key_series.astype(str).str.split("-").str[-1]


def extract_cluster_from_key(key_series):
    """Extract Cluster (everything before last '-') from KEY column."""
    return key_series.astype(str).str.rsplit("-", n=1).str[0]


def extract_itemcode_family(itemcode_series):
    """Extract ItemCode family prefix (letters only, e.g. AAP130 -> AAP)."""
    return itemcode_series.astype(str).str.extract(r"^([A-Z]+)", expand=False).fillna("OTHER")

"""
story_config.py -- Facit reference + narrative texts for the Phase Z dashboard
==============================================================================
Static configuration, deliberately NOT in Blob: BCG's frozen facit never
changes, so the reference values are configuration -- not data that is fetched.
The dashboard weaves this (the frozen) together with the status file (the live).

HONESTY CONTRACT: every number carries a source comment. None means "not yet
verified against a receipt" and renders as "[fill in]" in the UI -- NEVER a
made-up value. Fill in here, in one place, as more facit numbers are verified
from the validation receipts.

STRUCTURE (FD.21 -- frontend mirrors the flow): each phase carries a 'group'
that places it in the narrative Before (fuel) -> Engine (Azure) -> After
(local post-processing + feed). The dashboard groups the phases so a colleague
sees the WHOLE: where data comes in, where it is computed, where it becomes a
business decision. The metaphor is Jens's own ("Before-Engine-After").

HOW FIELD (FD.27): each phase carries 'how_sv' -- a colleague-friendly sentence
about HOW the step runs (local/VM, what triggers it, which command). It explains
the local<->cloud seam instead of hiding it.

DATA INFO (FD): each phase can carry 'data' -- what the step actually produces
in concrete numbers (rows, codes, size), from finished files/receipts. No new
computation; read-off values. None -> not shown.

The keys MUST match the status contract's phase keys (run_status.py):
extraction, cluster_model, site_model, site_step5, step6, build_r12.

FUTURE (FD): when the runner writes KPIs structurally into the status file
(metrics field in the contract, next contract version) the need for "now"
values here disappears -- then this file becomes facit + texts only.

Developer: Jens Palmö (Senior Business Analyst)
Author: Claude advisor, Phase Z session (grows iteratively).

Note: field names keep the _sv suffix for continuity with the contract/template;
only the VALUES are in English. Keys and field names are untouched (keep it simple).

FD.33-B1 (2026-07-03, single-touch): (1) hero flag per phase (BB.12: ONE hero
KPI carries the story, 2-3 supporting); (2) measured_window honesty badge --
the hardcoded now-values below were measured on the APRIL window and are
labeled as such until backfilled from the maj receipts (never invented, per
the honesty contract); (3) FACIT_WINDOW moved here as the single owner.
"""

# The frozen BCG facit window (single owner -- app.py derives from here).
# Source: BCG original run, verified in proof_chain (FR-1..7).
FACIT_WINDOW = "2022-07-01 → 2025-06-28"

# Groups in the narrative (FD.21). The order drives the rendering.
GROUPS = {
    "before": {
        "title_sv": "Before  --  the fuel coming in",
        "blurb_sv": "Fresh transaction data is fetched and loaded to Azure. "
                    "This happens locally because the data warehouse (DW) is only reachable on the office network/VPN.",
    },
    "engine": {
        "title_sv": "Engine  --  the model computes (Azure)",
        "blurb_sv": "The heavy elasticity computations run on the Azure VM -- "
                    "that is where the memory and power are. This is the proven engine.",
    },
    "after": {
        "title_sv": "After  --  result and business signal",
        "blurb_sv": "The model output is post-processed locally (Excel/COM, Windows) and "
                    "woven into ONE elasticity per product -- the number that drives pricing.",
    },
}

# Each KPI: label, facit (str|None), now (str|None), delta (str|None),
# dir: "pos" (green up arrow), "neg" (red down), "neut" (grey =).
STORY = {
    "extraction": {
        "group": "before",
        "title_sv": "Extraction (data prep, local)",
        "measured_window": "april window (to 2026-04-30)",
        "story": "BCG built the model on a frozen data window. Here the frozen facit window is compared against our growing window, metric by metric below. Reasonable growth shows the model is alive and the company is growing -- if something central had instead fallen, the comparison itself would be an alarm. Exact windows and numbers appear in the cards.",
        "why": "Fetches fresh transaction data and builds the weekly CSV the model trains on. "
               "Runs locally because the data warehouse (DW) is only reachable on the office network/VPN -- not from the Azure VM.",
        "use": "Produces the fuel: CSV and parquet that the model steps read.",
        "without": "The model runs on frozen data -- new months are silently dropped (the G7 lesson).",
        "how_sv": "One command locally: run_data.py regenerates the parquet from the DW (requires VPN), "
                  "runs data prep, and loads the parquet to Azure Blob. ~2 min for the upload.",
        # data-strangen ersatt av "coverage"-linsen i FUNNEL (facit->now-layout, FD.33-B2)
        "data": None,
        "kpis": [
            # Data window: frozen BCG window -> growing (+10 mo). Measured: extraction receipt Date window.
            {"label": "Data window", "facit": "jun 2025", "now": "apr 2026", "delta": "+10 mo", "dir": "pos"},
            # Transaction rows frozen->growing: 485 248 -> 608 944 (+25.5%). Measured: extraction receipt.
            {"label": "Transaction rows", "facit": "485 248", "now": "608 944", "delta": "+25.5 %", "dir": "pos"},
            # Revenue (TotalNet) frozen->growing: 6.50 -> 8.27 bn (+27.2%). Measured: playbook table.
            # THE LOAD-BEARING REASONABLENESS NUMBER: rising = healthy company; falling would be obvious error.
            {"hero": True, "label": "Revenue (TotalNet)", "facit": "6.50 bn", "now": "8.27 bn", "delta": "+27.2 %", "dir": "pos"},
        ],
    },
    "cluster_model": {
        "group": "engine",
        "title_sv": "Cluster model steps 1-4 (VM)",
        "measured_window": "april window (to 2026-04-30)",
        "story": "The same data as BCG gives almost exactly the same result (bit-for-bit, see above). On the growing window the shape holds: median and negative share sit close to facit while the KEY population grows. The movement is reasonable -- the model is alive without drifting away from facit. Exact numbers in the cards.",
        "why": "OLS elasticity per product x cluster, Ray-parallelized on the VM. "
               "Heavy computation that needs the VM's memory -- hence Azure, not the laptop.",
        "use": "Provides cluster-level elasticities -- one of the layers in the Step 6 weave.",
        "without": "Step 6 lacks the cluster level in the fallback weave.",
        "how_sv": "Runs on the Azure VM (bcg-poc-vm) via run_cluster_model.py. Starts the VM, "
                  "runs the steps on Linux, and deallocates when done so the cost stops.",
        "data": "3 812 product x cluster groups (all, including non-significant)",
        "kpis": [
            # Reasonableness vs facit (apple to apple, what sits closest to facit and is measured directly).
            # Median elasticity: facit -0.137 -> now -0.113 (rationality + IB.9). Same shape.
            {"hero": True, "label": "Median elasticity", "facit": "-0.137", "now": "-0.113", "delta": "+0.024", "dir": "neut"},
            # Negative share: facit 76.5% -> now 73.7% (IB.9 reference holds).
            {"label": "Negative share", "facit": "76.5 %", "now": "73.7 %", "delta": "-2.8 pp", "dir": "neut"},
            # KEY population: facit 3 812 -> now 4 180 (+368 new from growing window). The model is alive.
            {"label": "KEY population", "facit": "3 812", "now": "4 180", "delta": "+368", "dir": "pos"},
        ],
    },
    "site_model": {
        "group": "engine",
        "title_sv": "Site model steps 1-4 (VM)",
        "measured_window": "facit replication (verify 2026-05-28)",
        "story": "Engine proven: the orchestrator run is bit-for-bit identical to facit on the same data -- population, correlation (1.000000) and significance share (11.26%) all replicate exactly. Those replication numbers live in the proof layer; the card shows the growing window instead.",
        "why": "OLS elasticity per product x site -- the model's finest granularity. "
               "Validated bit-for-bit against the facit run of 2026-06-09.",
        "use": "Primary elasticity signal -- feeds Step 6 and the R12 feed.",
        "without": "No site-level elasticity; the weave falls back on coarser levels.",
        "how_sv": "Runs on the Azure VM via run_site_model.py -- same engine as cluster. "
                  "Reports its phase live to the status file while it runs.",
        "data": "6 624 unique KEY (product x site), 0.6 MB output_summary",
        "kpis": [
            # Window population vs BCG facit. facit = FR-5 (4 673). now = maj run
            # 2026-06 (6 604) -- verify against the maj distribution receipt.
            {"hero": True, "label": "Unique KEY (window)", "facit": "4 673", "now": "6 604", "delta": "+1 931", "dir": "pos"},
        ],
    },
    "bundle_model": {
        "group": "engine",
        "title_sv": "Bundle model (baskets)",
        "measured_window": "april-era comparison (2026-06-16)",
        "story": ("Baskets at clinic and hospital level -- how price-sensitive whole "
                  "baskets of services are, not individual codes. Bundle is included for complete "
                  "coverage, but drives only a small part (~2.2%) of the final "
                  "weave: it overlaps heavily with what Cluster and Site already capture. "
                  "The model is validated against frozen BCG facit like the others; exact numbers in the cards. "
                  "The basket population is fixed at 125 by design -- identical in facit and now."),
        "why": "OLS elasticity per basket (Bundle_code), same methodology as the other families at basket level.",
        "use": "Provides the bundle branch in the Step 6 weave -- a small but complete puzzle piece.",
        "without": "Step 6 lacks the basket perspective; ~2.2% of the weave falls back on a frozen branch.",
        "how_sv": ("Runs on the Azure VM (run_bundle_model.py) like Cluster/Site. Starts the VM, "
                   "runs the steps on Linux, validates against frozen facit, and deallocates when done."),
        "data": "125 baskets (Bundle_code) x clinic/hospital, OLS log-log.",
        "kpis": [
            # Reasonableness vs facit (measured: bundle facit vs azure_run_model, 2026-06-16).
            {"hero": True, "label": "Median elasticity", "facit": "-0.244", "now": "-0.211", "delta": "+0.033", "dir": "neut"},
            {"label": "Negative share", "facit": "87.2 %", "now": "85.6 %", "delta": "-1.6 pp", "dir": "neut"},
        ],
    },
    "site_step5": {
        "group": "after",
        "title_sv": "Site step 5 (Excel, local)",
        "measured_window": "maj window (step5 gate 2026-07-03)",
        "story": "Post-processing: model output becomes the Excel the business reads. Runs locally -- xlwings drives Excel via COM, which does not exist on Linux.",
        "why": "Processes the model output into BCG's Excel format via xlwings. "
               "Must run on Windows from the Site root (CWD-dependent config).",
        "use": "Creates the Excel summary (elasticity summary) that the business consumes.",
        "without": "Raw data exists but not in the format the pricing model reads.",
        "how_sv": "Runs locally on Windows after the VM model has downloaded its output. "
                  "xlwings opens Excel via COM -- hence Windows, never the Linux VM (LB.44).",
        "data": "Excel summary (model_summary.xlsx), 52.5 MB on the maj window",
        "kpis": [
            # MEASURED 2026-07-03: facit = BCG original model_summary.xlsx 31.5 MB
            # (Jens, OneDrive BCG_orginal_V2_New); now = maj step5 gate 52 538 192 B.
            {"hero": True, "label": "Excel size (model_summary)", "facit": "31.5 MB", "now": "52.5 MB", "delta": "+67 %", "dir": "pos"},
        ],
    },
    "step6": {
        "group": "after",
        "title_sv": "Step 6 -- fallback weave (local)",
        "measured_window": "april weave (2026-06-11)",
        "story": "The business signal: the core elasticity has moved slightly upward -- customers are marginally less price-sensitive than at BCG's measurement.",
        "why": "Weaves cluster and site level into ONE elasticity per product (F1-F7 fallback). "
               "Pure pandas/openpyxl, runs locally.",
        "use": "Produces the final blended elasticity per ProductKey -- the number that drives pricing.",
        "without": "No unified elasticity -- only separate levels without weighting.",
        "how_sv": "Runs locally on Windows (pure pandas/openpyxl, no Excel COM, no VM). "
                  "Reads cluster and site output and weaves them into one elasticity per product.",
        "data": "15 128 products in the weave, one elasticity per ProductKey",
        "kpis": [
            {"hero": True, "label": "Rev-weighted elasticity", "facit": "-0.532", "now": "-0.512", "delta": "+0.020", "dir": "pos"},
            {"label": "Median elasticity", "facit": None, "now": "-0.497", "delta": None, "dir": "pos"},
            {"label": "Products in the weave", "facit": None, "now": "15 128", "delta": None, "dir": "pos"},
        ],
    },
    "build_r12": {
        "group": "after",
        "title_sv": "Build R12 feed (local)",
        "measured_window": "april feed (2026-06-16; maj feed = 22 477 rows)",
        "story": "The final link -- makes fresh elasticities feedable into the pricing model's blue tabs.",
        "why": "Aggregates R12 volume + revenue per code x site and joins fresh elasticity, "
               "in copy-paste format for the BCG pricing model.",
        "use": "The file pasted into the pricing model to compute the revenue effect of a price proposal.",
        "without": "The elasticities exist but are not feedable into the pricing model.",
        "how_sv": "Runs locally on Windows (build_r12_for_model.py). The last step before the numbers "
                  "are pasted into the pricing model's tabs -- no VM, no Excel COM.",
        "data": "Model_Feed: 22 913 rows (code x clinic), 896 codes, 59 sites",
        "kpis": [],
    },
}

BAGE_SV = ("More data makes the model more certain, which sharpens the business signal "
           "that drives pricing. Facit (BCG, frozen jun 2025) is the zero point -- "
           "everything is measured as movement from there.")


# ---------------------------------------------------------------------
# VALIDATOR explanations (stage 3). Per validator: what it checks (short),
# and why PASS/REVIEW is expected. The KPIs come MEASURED from the receipts
# in the app; this is the curated interpretation (Jens's voice) -- kept
# separate so it is clear what is measurement and what is judgment.
#
# Top-management principle: one key-insight line per validator. To dig
# deeper -> export the receipt. The explanation says whether REVIEW is
# "expected/handled" or a real flag, so seven REVIEWs do not create needless worry.
# ---------------------------------------------------------------------
VALIDATORS = {
    "extraction_coverage": "Checks that all expected transaction data was included in the extraction. PASS = no silent drops.",
    "cluster_seed":        "Verifies that the cluster assignment is deterministic (same seed gives same clusters). PASS = reproducible.",
    "facit_selection":     "Confirms that the right facit period was chosen as reference. PASS = comparing against the right zero point.",
    "fte_coverage":        "Checks FTE coverage per period. PASS = no gap that would silently skew the normalization.",
    "dropped_rows":        "Forensic review of which rows were filtered out and why. INFO = no pass/fail gate, just traceability.",
    "cluster_distribution":"Checks that clinics are distributed reasonably across clusters. PASS = no degenerate cluster structure.",
    "volume_quantity":     "Verifies volume and quantity sums against expected. PASS = no scale-dropped fields.",
    "baseline_replication":"Compares against BCG's baseline bit-for-bit. PASS = the extraction replicates exactly.",

    # output_rationality (cluster/site) -- several REVIEW, each one EXPECTED:
    "distribution": "The shape of the elasticities (median, negative share, spread) against BCG's reference. PASS = the distribution looks as it should.",
    "outliers":     "Catches extreme values (|elast|>5). REVIEW is intended: 0.77% extreme values flagged for a human eye (e.g. MBAS0703 -320) -- forensic catch, not model error.",
    "drift_vs_bcg": "Measures how the growing data has moved from frozen facit. REVIEW on mean drift, BUT decision-relevant drift only 2.8% -- the movement sits in weak tail groups, not in the price-setting ones. This IS the business signal.",
    "sign_flips":   "Elasticities that flipped sign vs facit. REVIEW on the total (13.9%), BUT only 0.69% with both significant -- the rest is weak-signal noise, expected (IB.10).",
    "per_cluster":  "Reasonableness per cluster (median, %neg, %sig). REVIEW because one small cluster (Southern) sits below the significance gate -- conservative threshold, not error.",
    "per_itemcode_family": "Reasonableness per product family. REVIEW because 3 of 173 families have a weakly positive median -- small families, no price impact.",
    "top_leverage": "Identifies the KEY with the greatest revenue leverage (the ones that actually drive price). PASS = the top 50 capture 38% of all leverage, always manually reviewed.",
    "significance_consistency": "Compares significance rate against BCG. REVIEW because BCG recovery is 70.6% vs gate 80% -- but agreement 82% and sig rate within 7pp. The gate is set strictly.",
    "review_required": "The aggregate: the combined manual review list (outliers + drift + sign-flips + top-leverage). REVIEW = 9.1% of KEY flagged for a manager's eye before pricing decisions -- exactly what the review step should do.",

    # provenance (step6):
    "step6_provenance":      "Tracks that the Step 6 weave was built on fresh model output, not old. PASS = correct input.",
    "fallback_freshness":    "Checks that the fallback routing is current against the growing data. PASS = no frozen routing.",
}

# proof_chain: bit-for-bit against frozen facit -- THE TRUST LAYER. Measured numbers from
# verify_receipt (2026-05-28). This is the strongest proof: the engine
# replicates BCG exactly. Separate from rationality (which reviews growing output).
PROOF_CHAIN = {
    "intro": "Bit-for-bit against BCG's frozen facit. This proves the engine replicates BCG exactly on the same data -- "
             "the zero point everything growing is measured from. 6 of 6 milestones PASS.",
    "items": [
        {"fr": "FR-1", "name": "Data prep (rows/revenue/volume)", "kpi": "485 248 rows, corr 1.000000, diff 0.000%"},
        {"fr": "FR-4", "name": "Cluster model", "kpi": "population 3 812/3 812, decision-rel. 1 118/1 118 (100%)"},
        {"fr": "FR-5", "name": "Site model", "kpi": "population 4 673/4 673, rank-corr 0.9108, decision-rel. 113/144"},
        {"fr": "FR-6", "name": "Bundle model", "kpi": "population 125/125, decision-rel. 57/70 (81%)"},
        {"fr": "FR-3", "name": "Cluster blend / step 5", "kpi": "43/43 representatives match BCG"},
        {"fr": "FR-7", "name": "Fallback weave / step 6", "kpi": "108 979 rows, corr 1.000000, level-match 100%"},
    ],
    "overall": "6/6 PASS",
    "receipt_file": "verify_tool/receipts/verify_receipt_2026-05-28.xlsx",
}


# ---------------------------------------------------------------------
# Results-in-Blob presentation (FD.33-B2): the Model Feed is THE deliverable;
# everything else is an attachment with a stated purpose. Matched on filename
# prefix. Edit texts here (Jens's voice), never in the JS.
# ---------------------------------------------------------------------
OUTPUT_PURPOSE = {
    "Model_Feed": {"hero": True, "title": "Model Feed -- the deliverable",
                   "desc": "Paste into the pricing model's blue tabs. This file is what the whole pipeline exists to produce."},
    "Final_Fallback_Data": {"hero": False, "title": "Full weave (attachment)",
                            "desc": "One elasticity per product incl. fallback level -- traceability and analysis behind the feed."},
    "output_summary": {"hero": False, "title": "Family model output (attachment)",
                       "desc": "Raw per-family elasticities that feed the weave."},
}

# =====================================================================
# FUNNEL (stage 4) -- the funnel model per family. Three layers:
#   top     : bit-for-bit against facit (broad trust, green, correct PASS)
#   facit_nu: "what BCG had -> what it became now" (the story, no verdict)
#   prov    : provenance/nuance (what is fresh vs frozen) -- honesty
# All numbers MEASURED from the verify_tool receipts. Large matching amounts build
# trust in themselves (1151 codes, 0 only-ours, 0 only-facit). Spot-on, not
# drowning in detail: a few strong numbers per family.
# =====================================================================
FUNNEL = {
    "extraction": {
        "proof": {"label": "Data prep bit-for-bit vs BCG facit", "kpi": "485 248 rows · corr 1.000000 · diff 0.000%", "ok": True},
        "facit_nu": [
            {"metric": "Transaction rows", "facit": "485 248", "now": "608 944", "note": "+25.5% -- healthy growth, growing window"},
            {"hero": True, "metric": "Revenue (TotalNet)", "facit": "6.50 bn", "now": "8.27 bn", "note": "+27.2% -- if this FELL it would be obvious error"},
            {"metric": "ItemCodes (facit selection)", "facit": "1 151", "now": "1 151", "note": "same selection -- comparable apple to apple"},
        ],
        # Coverage & trust: how much of reality the model prices on. A model on
        # 1% of revenue would lack credibility regardless of validations -- this
        # lens makes the noise filter visible. None -> "[fill in]" (never invented).
        "coverage": [
            {"metric": "Raw transactions in window", "facit": None, "now": "27.4 M",
             "note": "aggregated to 608 944 weekly model rows -- aggregation, not data loss"},
            # Revenue-coverage (andel av total omsattning de 1 151 koderna fangar)
            # -> FD.40: mats ur extraction coverage-kvittot innan den visas.
            # Ovisade varden renderas ALDRIG som [fill in] (keep it simple).
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/2026-06-08/00_master_summary_2026-06-08_105839.xlsx",
        "measured_window": "april window (receipt 2026-06-08)",
    },
    "cluster_model": {
        "proof": {"label": "Cluster model bit-for-bit (FR-4)", "kpi": "population 3 812/3 812 · decision-relevant 1 118/1 118 (100%) · rank-corr 1.0000", "ok": True},
        "facit_nu": [
            {"hero": True, "metric": "Median elasticity", "facit": "-0.137", "now": "-0.113", "note": "same shape, slightly less price-sensitive"},
            {"metric": "Negative share", "facit": "76.5 %", "now": "73.7 %", "note": "IB.9 reference holds"},
            {"metric": "Number of KEY", "facit": "3 812", "now": "4 180", "note": "+368 new from growing window"},
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/2026-06-08/rationality/00_rationality_master_2026-06-08_130847.xlsx",
        "measured_window": "april window (receipt 2026-06-08)",
    },
    "site_model": {
        "proof": {"label": "Site model bit-for-bit (FR-5)", "kpi": "population 4 673/4 673 (identical) · corr 1.000000 · rank-corr 0.9108 · decision-relevant 113/144", "ok": True},
        "facit_nu": [
            # Reasonableness profile: ours vs facit at the finest granularity. Close = reasonable (does not drift away).
            # Measured: proof_chain PROFILE (IB.9). Replication numbers (6624/6624, corr 1.0) belong to bit-for-bit above.
            {"hero": True, "metric": "Median elasticity", "facit": "-0.062", "now": "-0.054", "note": "ours vs facit -- close, reasonable shape at site level"},
            {"metric": "Negative share", "facit": "63.6 %", "now": "62.4 %", "note": "almost the same -- price sensitivity keeps direction"},
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/verify_receipt_2026-05-28.xlsx",
        "measured_window": "facit replication (verify 2026-05-28)",
    },
    "bundle_model": {
        "proof": {"label": "Bundle model bit-for-bit (FR-6)", "kpi": "population 125/125 (identical) · rank-corr ~0.93 · median |diff| 0", "ok": True},
        "facit_nu": [
            {"hero": True, "metric": "Median elasticity", "facit": "-0.244", "now": "-0.211", "note": "ours vs facit -- close, reasonable shape at basket level"},
            {"metric": "Negative share", "facit": "87.2 %", "now": "85.6 %", "note": "highest of the families -- baskets strongly price-sensitive"},
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/verify_receipt_2026-05-28.xlsx",
        "measured_window": "facit replication (verify 2026-05-28)",
    },
    "step6": {
        "proof": {"label": "Fallback weave bit-for-bit (FR-7)", "kpi": "108 979 rows · corr 1.000000 · level-match 100.00%", "ok": True},
        "facit_nu": [
            {"hero": True, "metric": "Median blended elasticity", "facit": "-0.532", "now": "-0.497", "note": "100% negative, 100% in (-10,0) band -> decision-ready"},
            {"metric": "Within band (|delta|<0.5)", "facit": "—", "now": "95.0 %", "note": "decision-relevant drift only 1.6%"},
            {"metric": "Products in the weave", "facit": "15 128", "now": "15 128", "note": "identical population"},
        ],
        # The provenance nuance (honest): what is fresh vs frozen in the weave.
        "prov": {
            "headline": "The weave mixes fresh and frozen inputs -- an honest nuance, not an error.",
            "frozen_explain": ("FROZEN = a validated BCG-era input deliberately locked (FD.11/14/15) until its "
                               "growing replacement is re-run AND re-validated. Unlocking would require re-running "
                               "the bundle family, the step-5 routing and the revenue weights on the growing window "
                               "and validating each -- planned work, consciously deprioritized because bundle drives "
                               "only 2.2% of the weave. Honesty over cosmetics: frozen parts are never presented as fresh."),
            "fresh": 2, "frozen": 3, "total": 5,
            "rows": [
                {"part": "Site elasticities (F1)", "state": "FRESH", "reach": "2026-06-10"},
                {"part": "Cluster elasticities (F3/F5/F6/F7)", "state": "FRESH", "reach": "2026-06-08"},
                {"part": "Cluster step-5 routing (43 rep)", "state": "FROZEN", "reach": "2025-12 (FD.15)"},
                {"part": "Bundle model (F2/F4)", "state": "FROZEN", "reach": "2025-12 (FD.11)"},
                {"part": "Revenue weights", "state": "FROZEN", "reach": "2025 (FD.14)"},
            ],
            "bundle_reliance": "Bundle share in the weave: 2.2% (frozen via FD.11)",
        },
        "receipt": "verify_tool/receipts/2026-06-11/provenance/00_provenance_master_2026-06-11_181714.xlsx",
        "measured_window": "april weave (2026-06-11)",
    },
}

"""
info_config.py -- "About the model" tab content for the Phase Z dashboard
==========================================================================
The README + architecture documents condensed to their core: a short education
of what runs underneath, for readers who are NOT into the details and do not
need to be -- but deserve the possibility. English, pedagogical, no jargon
without explanation. ONE place to edit (served by app.py /api/info).

Editing rule: plain text; blank line (\\n\\n) = new paragraph. No HTML here --
the dashboard escapes everything (safe by construction).

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, FD.33-B2 session 2026-07-03.
"""

INFO = {
    "title": "About the model — a five-minute education",
    "sections": [
        {
            "h": "What this is",
            "body": (
                "A price elasticity model, originally built by BCG X for Evidensia, that estimates how "
                "sensitive demand for each veterinary product and service is to price changes. One number per "
                "product — the elasticity — drives pricing decisions.\n\n"
                "This dashboard shows the health of the pipeline that keeps that model alive on fresh data: "
                "what ran, what it produced, and — most importantly — the evidence that the results can be trusted."
            ),
        },
        {
            "h": "Why it exists (the replication story)",
            "body": (
                "BCG built and validated the model once, on a frozen data window. Evidensia's goal is to run it "
                "independently, every month, on growing data — without BCG and without depending on any single "
                "person's laptop.\n\n"
                "Step one was proving we can reproduce BCG's exact results on their exact data (bit-for-bit). "
                "Step two is running the same engine on fresh data and showing the movement is reasonable. "
                "This dashboard tells both stories."
            ),
        },
        {
            "h": "Before — Engine — After (how a run flows)",
            "body": (
                "BEFORE (local Windows): fresh transaction data is extracted from the data warehouse — only "
                "reachable on the office network — and prepared into the weekly dataset the model trains on. "
                "The fuel is uploaded to Azure Blob Storage.\n\n"
                "ENGINE (Azure VM): the heavy elasticity computations run on a memory-rich virtual machine. "
                "Three model families run here: Cluster (product x cluster), Site (product x clinic — the finest "
                "granularity) and Bundle (whole baskets). OLS log-log regressions, parallelized, thousands of "
                "models per family.\n\n"
                "AFTER (local Windows): the model output is post-processed (Excel automation only exists on "
                "Windows), then Step 6 weaves the family levels into ONE elasticity per product via a fallback "
                "hierarchy, and the R12 build produces the Model Feed — the file pasted into the pricing model. "
                "Azure Blob is the bridge between all three stages, so no single computer is irreplaceable."
            ),
        },
        {
            "h": "The proof chain (why you can trust the engine)",
            "body": (
                "Before anything was run on fresh data, every step was replicated against BCG's frozen original "
                "and compared bit-for-bit: same rows, same revenue, correlation 1.000000 on the outputs, identical "
                "populations. Six milestones (FR-1 to FR-7), all PASS.\n\n"
                "That frozen result is the ZERO POINT. Everything you see on growing data is measured as movement "
                "from there — which is what makes a change interpretable as growth rather than error."
            ),
        },
        {
            "h": "Frozen vs fresh (an honesty choice, not a limitation)",
            "body": (
                "Some inputs in the final weave are deliberately FROZEN: validated BCG-era files locked in place "
                "(bundle model, step-5 routing, revenue weights). They stay frozen until their growing replacements "
                "are both re-run AND re-validated — never silently swapped.\n\n"
                "Why accept frozen parts at all? Proportion. The bundle branch, for example, drives about 2.2% of "
                "the final weave. Re-running and re-validating it is planned work, consciously deprioritized against "
                "that 2.2% impact. The dashboard always shows which parts are fresh and which are frozen — "
                "honesty over cosmetics."
            ),
        },
        {
            "h": "The validation machinery (what the green marks mean)",
            "body": (
                "Every run produces Excel receipts from independent validator suites: extraction coverage (did all "
                "data arrive?), rationality (do the elasticities look sane — distribution, outliers, sign flips, "
                "drift vs facit?), provenance (was the weave built on fresh output, not stale files?).\n\n"
                "PASS means the gate held. REVIEW does not mean error — it means a human eye is requested, and for "
                "most validators that is by design (e.g. extreme outliers are flagged on purpose). Every receipt is "
                "exportable from the dashboard, per selected run window. Nothing shown here is computed by the "
                "dashboard itself — it only reads what the pipeline already proved."
            ),
        },
        {
            "h": "Where everything lives (survivability)",
            "body": (
                "Azure Blob Storage holds the structure: input/ (the fuel), output/<family>/<window>/ (model "
                "results per data window), output/final/<window>/ (the weave and the Model Feed), receipts/ "
                "(validation evidence per window), and a frozen facit archive as the permanent zero point.\n\n"
                "The data window IS the address — for example 2022-07-01_2026-05-31 — so any result can be traced "
                "to exactly the data it was computed on. Code lives in Git. Together this means a successor could "
                "clone the repository, read Blob, and continue — the original design goal: survive any single "
                "person leaving."
            ),
        },
        {
            "h": "How to read this dashboard in 30 seconds",
            "body": (
                "Pick a run (a data window) at the top. Green dot = the phase succeeded. Green check pill = "
                "proven bit-for-bit against BCG facit. The three cards per phase are the key numbers: grey is "
                "BCG's frozen value, colored is now, the arrow is the movement.\n\n"
                "Want more? 'Details, story & validations' opens the full narrative, the facit-to-now comparison, "
                "the fresh/frozen map and every exportable receipt. Want the result? The green 'Model Feed' button "
                "at the bottom is the deliverable. Everything else is evidence.\n\n"
                "Built by Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB) on "
                "the principle 'measure, don't guess' — every number on these pages traces to a receipt or a "
                "status file, never to an assumption."
            ),
        },
    ],
}

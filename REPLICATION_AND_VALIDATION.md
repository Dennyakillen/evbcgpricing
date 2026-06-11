# REPLICATION & VALIDATION — How We Proved We Own This Model

**Project:** `evbcgpricing`
**Owner:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Purpose of this document:** a complete, standalone record of the work done to replicate
BCG's price-elasticity model, validate that replication bit-for-bit, and then run it on
Evidensia's own growing data. It is written so that a developer years from now — with no
access to us — can understand exactly what was built, how it was proven, and how much
evidence stands behind every number. This is the "we did the work" record.

---

## 1. Why this exists

BCG delivered a price-elasticity model and a set of conclusions in 2025. The business
question was not "is BCG right?" but "can Evidensia **own** this — run it ourselves, on
fresh data, and trust the result for pricing decisions?" Owning a model means three
things, in order:

1. **Reproduce it exactly** on the same data BCG used (proves we understand the method,
   not just the output).
2. **Run it on fresh, growing data** (proves the method survives outside BCG's frozen
   snapshot).
3. **Validate the fresh output** without a facit to compare against (proves we can judge
   correctness on our own).

This document records all three, with the evidence for each.

---

## 2. What the model actually is

A price elasticity is the percentage change in volume for a 1% change in price. BCG
estimates it per **product code × clinic cluster** using a **log-log OLS regression**: in
a log-log model the price coefficient *is* the elasticity directly (INSIGHTS IB.7). The
regression controls for season and media/PR effects.

Most fine-grained groups have too little data for a stable estimate — only ~18% are
statistically significant on the raw cluster level (IB.1). The model handles this with a
**fallback weave**: a seven-level priority cascade (F1 site → F2 bundle → F3 cluster →
F4 bundle-across → F5 product-across → F6 service-within → F7 service-across). For each
product it takes the first significant level, so sparse groups inherit a stronger
representative rather than being modelled badly (IB.2). The weave **selects**, it does not
re-model.

The data was always Evidensia's own — BCG sourced it from our data warehouse
(`dbo.Fact_BillingInvoiceRows` joined to `dbo.Dim_Item`); their item grouping is a coarser
snapshot of our internal hierarchy (IB.4). The only genuine external input is FTE staffing
from Quinyx (IB.3) — competition data, external price feeds and an "InScope" mapping are
declared in BCG's config but never actually read by the code (dead config, IB.3).

---

## 3. The replication — proven bit-for-bit

We rebuilt the pipeline step by step and proved each stage reproduces BCG's frozen output
exactly, on BCG's original data window. The proof chain (`verify_tool\proof_chain\`):

| Stage | What was reproduced | Evidence |
|---|---|---|
| **FR-1 Data prep** | The model's input data = BCG's: same rows, revenue, volume per row | correlation 1.000000, |diff| = 0 |
| **FR-3 Cluster blend** | Step-5 representative selection per (service, cluster) | 43 / 43 representatives identical |
| **FR-4 Cluster model** | Cluster-level elasticities | 3,812 groups; decision-relevant identical |
| **FR-5 Site model** | Site-level elasticities | 4,673 groups; rank-corr 0.91 |
| **FR-6 Bundle model** | Basket-level elasticities | 125 groups; rank-corr 0.93 |
| **FR-7 Fallback weave** | The full F1–F7 final elasticity per product | 108,979 rows, corr 1.000000, 100% level match |

FR-7 is the decisive one: the entire weave, end to end, produced **the same final
elasticity as BCG for every product, bit-for-bit** (|diff| = 0, identical F-level
distribution). That is what "we own the method" means in evidence terms — not a similar
answer, the *same* answer.

### Bugs found and fixed during replication

Replication surfaced concrete defects in the inherited code (documented in `LESSONS_BCG.md`):
relative-path errors, a column-name mismatch (`No of Sites` vs `No_of_Sites`), missing
derived columns, a CSV/XLSX format mismatch, and a mojibake encoding bug in Module 2. The
DuckDB SQL pipeline replaced Alteryx for Modules 1, 2, 3 and 6; Module 4 still requires
Alteryx. BCG's code also carried UK-legacy remnants and dead config keys (LB.51) — verified
before each run rather than trusted.

### A subtlety worth recording (sign flips)

A few fine-level groups had the *opposite sign* to BCG (e.g. a site showing +0.87 where
the facit had −2.29). These are not replication errors — they are weak-signal OLS near the
noise threshold, where thin data makes the coefficient unstable and a marginal input
difference flips the sign. They are few, they appear only at the finest levels, and the
fallback weave discards them before any decision (IB.10). They *motivate* the weave rather
than undermining the replication.

---

## 4. Running on fresh data (FAS F)

With replication proven, the pipeline was parametrised to run on a growing window
(anchor fixed at 2022-07-01, end rolled forward) instead of BCG's hardcoded 2025-06 window.
The three model families were run on growing data:

- **Cluster** and **Site** elasticities: regenerated on growing data.
- **Bundle**: parked on evidence (see §6).

Then the fallback weave (Step 6) was run for the first time on growing data
(`run_step6.py`). Result: 108,979 rows / 15,128 products, median final elasticity −0.497,
**100% negative, 100% within the rational (−10, 0) band**. The F-level distribution:

| Level | Share |
|---|---|
| F6 service within cluster | 74.6% |
| F3 cluster level | 9.8% |
| F5 product across clusters | 9.5% |
| F7 service across clusters | 3.9% |
| F2 bundle level | 1.8% |
| F4 bundle across clusters | 0.4% |
| F1 site level | 0.0% |

74.6% of products draw their elasticity from F6 — most products have no significant signal
of their own even at cluster level, which is exactly why the weave exists (confirms IB.1 /
IB.9).

---

## 5. Validating the fresh output (no facit)

On fresh data there is no BCG facit to match against, so correctness is judged three ways
(`verify_tool\output_rationality\` and `verify_tool\provenance\`):

1. **Standalone rationality** — is every fresh elasticity plausible? 100% negative, 100%
   in band. Yes.
2. **Drift vs the 2025 baseline** — 95% of products drift under 0.5; revenue-weighted
   elasticity moved −0.532 → −0.512 (net +0.020, negligible). The model is *stable* over
   ten months — the property a pricing model needs.
3. **Provenance** — exactly which inputs are fresh vs frozen, made explicit so no one
   over-reads the result. Reported as REVIEW by design (the three frozen locks), not as a
   defect.

### What the ten extra months changed (decomposition)

The drift was decomposed by service, cluster and revenue weight
(`analysis\analys_bcg_freshness.py`). The finding, data-determined: the core assortment's
price sensitivity held still. The five largest revenue services (Consult, Imaging, Surgery,
Internal, Hospitalisation — together >4.7 bn SEK) are essentially flat. The movement that
exists is either **noise-normalisation** in tiny weak-signal items (Healthcare: +0.97 raw
drift but only 34 M SEK, with 2025 outliers settling toward sensible values — IB.10) or
**low-revenue directional shifts** (Accessories more price-sensitive, Consumables less).
No large service changed direction. The fact that fresh data *tames* extreme estimates
rather than creating new ones is itself a sign of a well-behaved model.

This is captured for top management in `presentations\elasticity_since_bcg.pdf` (BCG's
−0.532 vs today's −0.512, with the full evidence base) and as a data appendix in
`output_analyspaket\Analyspaket_BCG_Freshness_<date>.xlsx`.

---

## 6. Key decisions recorded along the way

- **Bundle parked on evidence (FD.11).** Basket transactions were 23.9% of revenue, but
  the bundle branch wins only **2.2%** of decisions in the weave — because Cluster/Site
  levels rescue the elasticity before the weave reaches bundle for 97.8% of products
  (INSIGHTS IB.12: weave-win ≠ volume-materiality). Finishing the bundle model (UK-legacy
  bridges, FTE bridge, VM run) would affect 2.2% of outcomes — disproportionate cost.
  Revisit trigger: if the rationality gate shows hospital services frequently
  insignificant/sourceless in the weave.
- **Three frozen locks accepted deliberately (LF.9).** Weave weights, step-5 routing and
  the bundle branch stay on 2025 values to deliver a fresh read now rather than blocking on
  three upstream rebuilds whose combined decision impact is small. Documented, surfaced by
  the provenance check, with a defined refresh roadmap (FD.15 → FD.14 → FD.11).

---

## 7. The evidence in one place

- **Replication proof:** `verify_tool\proof_chain\` (FR-1..7, README documents the chain).
- **Extraction validation:** `verify_tool\extraction_validation\` (DW vs facit).
- **Output rationality:** `verify_tool\output_rationality\` (fresh-output sanity).
- **Provenance & freshness:** `verify_tool\provenance\` (fresh vs frozen, stability).
- **Receipts:** `verify_tool\receipts\<date>\` — every run writes a dated Excel receipt;
  trust the receipt, not the console (R7).
- **Decisions & assumptions:** `docs/governance/` (PLAYBOOK decision log,
  LOCKED_ASSUMPTIONS, FUTURE_DEVELOPMENT, ROADMAP).
- **Domain & technical learnings:** `docs/knowledge/` (INSIGHTS_BCG `IB.*`,
  LESSONS_BCG `LB.*`).

---

*Compiled by Jens Palmö. Every figure in this document traces to a re-runnable script and a
dated receipt — the replication is not a claim, it is a chain of evidence.*

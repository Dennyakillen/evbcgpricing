# FD.28 — Blob-struktur som speglar BCG:s mappstruktur (designdokument)

**Utvecklare:** Jens Palmö (Senior Business Analyst)
**Författare:** Claude-rådgivare, Phase Z-session
**Status:** Design (exekverbar i key-läge utan Kent; AAD-övergång gated på FD.29)
**Syfte:** En sammanhållen Blob-struktur i test-resursen som speglar BCG:s
numrerade pipeline-mappar — så input, output, validering och fryst facit
för varje familj får en igenkännbar, dokumenterad plats. Detta är en
**dokumentationsbyggsten**: strukturen ska kunna läsas som en karta över
hela modellen, inte bara vara en teknisk lagringsplats.

---

## 1. Beslut som ligger fast (mätt denna session)

- **VM bor kvar i test-RG** (`ev-openai-swce-rg-test`). Ingen flytt till prod.
  Allt behandlas som "test"-resurs tills top management vill migrera.
- **Hemkonto:** `evbcgpricinginput` (test-RG, där VM:en bor). Namnet säger
  "input" men kontot husar allt — accepterat, namnet byts inte (inte värt
  jobbet; en container-struktur inuti ger ändå tydligheten).
- **Auth: key-läge** (`PRICINGMODEL_AUTH=key`). Fungerar idag: nyckeln läses
  via control-plane-Owner. **Bygget kräver INTE Kent.**
- **ABAC-väggen (mätt 2026-06-16):** Owner-rollen har ett ABAC-villkor som
  blockerar `roleAssignments/write`. Jens kan alltså INTE tilldela sig själv
  Storage Blob Data-rollen. AAD-läget ger `AuthorizationPermissionMismatch`.
  Därför: key-läge tills Kent (eller någon utan ABAC-villkor) tilldelar
  data-rollen. Detta är FD.29 — gated, men blockerar inte FD.28-bygget.

---

## 2. BCG:s lokala struktur (det vi speglar)

Under `C:\Projekt\BCG\Pipeline\02. Elasticity\`:

| BCG-mapp | Roll | Speglas i Blob? |
|---|---|---|
| 1. Dataprep Alteryx Workflow | Dataprep (ersatt av DuckDB lokalt) | Nej — lokalt steg, ej Blob |
| 2. Product Cluster Level Models | Cluster-familj | **Ja** |
| 3. Product Site Level Models | Site-familj | **Ja** |
| 4. Bundle Clinic Data Prep | Bundle-dataprep | **Ja** (under bundle) |
| 5. Bundle Clinic Models | Bundle-familj | **Ja** |
| 6. Fall Back Logic | Step 6-väv | **Ja** |
| Sweden_Elasticity_Data_Prep_SQL | Extraction/dataprep | **Ja** (input) |
| Excel_Outputs | Slutkonsoliderade Excel | **Ja** (output) |

Varje familjs inre mönster (mätt på cluster): `code`, `data` (input),
`output` (resultat) + lokala arkiv/backup/logg (speglas EJ — det är lokal
versionshantering, inte struktur).

---

## 3. Föreslagen Blob-struktur

Azure Blob har inte äkta mappar — "mappar" är prefix i blob-namn. Två
designval: (A) en container per familj, eller (B) en container med
prefix-struktur. **Rekommendation: B — en container `pipeline` med
prefix som speglar BCG-numreringen.** Skäl: enklare behörighet (en
container), och prefixen ger exakt samma visuella mappkänsla i portalen.

```
Container: pipeline
│
├── 00_frozen_facit/                  ← BCG:s frysta 2025-facit (nollpunkten)
│   ├── cluster/output_summary.xlsx
│   ├── site/output_summary.xlsx
│   ├── bundle/output_summary.xlsx
│   ├── blend/final_model_cluster_granularity.xlsx
│   └── fallback/Final_Fallback_Data_20250930.xlsx
│
├── 01_dataprep/                      ← "Sweden_Elasticity_Data_Prep_SQL"
│   ├── input/transaction_data.parquet
│   └── validation/                   ← extraction_validation-kvitton
│
├── 02_cluster/                       ← "2. Product Cluster Level Models"
│   ├── input/                        (data/ hos BCG)
│   ├── output/output_summary.xlsx
│   └── validation/                   ← output_rationality-kvitton
│
├── 03_site/                          ← "3. Product Site Level Models"
│   ├── input/
│   ├── output/
│   └── validation/                   ← proof_chain FR-5
│
├── 04_bundle/                        ← "4+5. Bundle Clinic Data Prep + Models"
│   ├── input/
│   ├── output/
│   └── validation/
│
├── 05_step6/                         ← "6. Fall Back Logic"
│   ├── input/
│   ├── output/Final_Fallback_Data_*.xlsx
│   └── validation/                   ← provenance-kvitton
│
├── 06_r12/                           ← R12-matning
│   └── output/Model_Feed_*.xlsx
│
└── 07_excel_outputs/                 ← "Excel_Outputs" (slutkonsoliderat)
    └── *.xlsx
```

**Status-filer** behåller egen container `runstatus` (orkestreringens
sanning, separat från pipeline-artefakter — det är drift, inte data).

---

## 4. Den bärande principen: facit bredvid växande

Varje familj får `00_frozen_facit/` överst och växande output i sin
familjemapp. Det gör Blob-strukturen till en **direkt facit-vs-nu-karta**:
för varje familj ligger den frysta BCG-nollpunkten och den växande
körningen sida vid sida, redo att jämföras. Det speglar exakt det appens
tratt visar — och gör att en kollega kan navigera strukturen och förstå
"vad hade BCG, vad blev det nu" utan att öppna appen.

---

## 5. Migrationsväg (från dagens spretiga läge)

Idag: input → test-kontot delvis, status/output → prod-kontot (`blob.py`
default `evipricingmodelstprod` i prod-RG). Spretigt.

Steg för att samla i test-kontot (alla i key-läge, ingen Kent):
1. Peka `blob.py` mot `evbcgpricinginput` + `ev-openai-swce-rg-test`
   (två env-vars eller default-ändring). EN ändring.
2. Skapa container `pipeline` i test-kontot.
3. Ladda upp fryst BCG-facit till `00_frozen_facit/` (engångs, överlever
   lokala maskinen — LB.66).
4. Ladda upp befintliga lokala Excel-outputs per familj till respektive
   `output/`.
5. Peka validering/output-uppladdning mot prefix-strukturen.

**Inget av detta kräver Kent** — key-läge räcker. Kent behövs bara för
FD.29 (AAD-övergång), som är "överlever att Jens slutar"-målet, inte bygget.

---

## 6. Vad som är gated på Kent (FD.29)

Enda Kent-beroendet: byte från key-läge till AAD (DefaultAzureCredential)
så uppladdning överlever att Jens tappar Owner-access. När Kent tilldelar
`Storage Blob Data Contributor` till Jens (eller en Managed Identity):
- `blob.py` byter `PRICINGMODEL_AUTH=key` → `aad`. EN env-var, ingen
  kodändring (blob.py är redan förberedd, DefaultAzureCredential).
- Allt annat i strukturen är oförändrat.

Tills dess: key-läge, fullt funktionellt.

---

## 7. Vad detta INTE löser (ärliga gränser)

- **Excel-stegen kan inte köras på Azure** (xlwings/COM, Windows-only,
  LB.44). De körs lokalt och laddas UPP till Blob för bevaring/jämförelse.
  Blob är lagringsplats för dem, inte exekveringsmotor.
- **Strukturen flyttar inte VM:en.** VM bor kvar i test; om top management
  vill migrera till prod är det ett separat infrastrukturbeslut (ny VM i
  prod, inte RG-flytt — VM-migration mellan RG är skör).
- **Proveniens-skulderna (FD.14/15) kvarstår** — väv-vikter och routning är
  frusna 2025 oavsett blob-struktur. Strukturen visar dem ärligt (frozen_facit
  bredvid växande), löser dem inte.

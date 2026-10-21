# OFFBOARDING_KRITISKT — det som inte följer med när utvecklarens dator och konton avvecklas

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB). Läge 2026-10-21. Status: **täckt** = ersatt och verifierat ·
**IT** = kräver beslut eller åtgärd av IT · **öppen** = inte mätt eller inte åtgärdat.*

Koden finns i Azure DevOps, datan i Azure Blob (`docs/ops/DATA_PLACERING.md`). Det här är det som ändå hänger på en person, en dator
eller ett konto.

| # | Det här försvinner | Ersätts av | Status |
|---|---|---|---|
| 1 | **Värdena i `tools/dw/.env`** (DW-server och databas för REGEN) | `tools/dw/.env.example` + värden från DW-förvaltaren. Behövs bara för REGEN; PREP och modellerna kan köras på bränslet i Blob (`input/parquet/`) | **IT** |
| 2 | **Lokal data** (indata, mallar, utdata) | spegeln `spegel/bcg_2026-10-20/` (22 009 filer, sha256-verifierade 2026-10-20) + `tools/spegel/spegel_fran_blob.py` | **täckt** |
| 3 | **Facit i utvecklarens OneDrive** (BCG-originalet) | de nio filer validatorerna använder, byte-exakt i `pipeline/00_frozen_facit/bcg_original/`; resten dokumenterat i `docs/BCG_ORIGINAL_REFERENSER.md`. Bevis: `proof_chain` gav identiskt resultat mot OneDrive-originalet och mot Azure-kopian (2026-10-21) | **täckt** (arkivplats för hela originalet: se referensfilen) |
| 4 | **Git-historiken** (172 commits; GitHub-repot ligger på ett personligt konto) | `git bundle` av hela historiken i Blob: `spegel/historik/evbcgpricing_<datum>.bundle` (`git clone <bundle>` återskapar den) | **täckt** när bundlen är uppladdad och verifierad |
| 5 | **Behörigheter knutna till utvecklaren:** roll på lagringskontot som ger nyckelåtkomst (PIM), DW-läsning via AAD + VPN, åtkomst till VM:en, Azure DevOps-repot | motsvarande roller för förvaltaren. Resurserna ligger i resursgruppen `ev-openai-swce-rg-test`, subscription `ev-lz3-ai (SE)` | **IT** |
| 6 | **SSH-åtkomst till VM:en** (`orchestration/infrastructure/azure_vm.py` använder ssh) | förvaltarens egen nyckel på VM:en, eller `az vm`-baserad åtkomst | **öppen** — var nyckeln ligger och om den är personlig är inte mätt |
| 7 | **Arbetsmiljön** (Python 3.11, Excel för steg 5/6 via xlwings, ODBC Driver 17, Azure CLI) | `install.py` + `verify_setup.py` (kontrollerar allt utom Excel-licensen) | **täckt** |
| 8 | **Förvaltaransvaret** | KRAVSPEC_IT §4: "Vem är förvaltare av modellen efter Jens?" | **beslut: chef + IT** |
| 9 | **Utvecklarens arbetsmetodik** (sessionsverktyg, beslutsfiler, metodfiler) | behövs inte för drift — följer medvetet inte med till DevOps (beslut 2026-10-21) | — |

## Ordning för den som tar över

1. IT ger rollerna i rad 5 (och rad 1 om REGEN ska köras).
2. Ny dator: `README.md`, avsnittet *Ny dator — en gång* (klona → `install.py` → `spegel_fran_blob.py` → `verify_setup.py`).
3. Första körningen: `DRIFT.md`.

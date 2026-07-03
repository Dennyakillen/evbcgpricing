# NAVKARTA — pipelinens bärande stommar och skarvar

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia). Sammanställd 2026-07-03 ur den
breda tvärsnittskontext en enda lång session gav (EFTER-kedjan bevisad e2e + skuldstängning).*

## Hur denna karta ska läsas

**Syfte:** en framtida session (eller kollega) ska snabbt se VAR den bör börja gräva när något
är fel eller ska byggas. Kartan är inte en filförteckning — den listar **nav** (knutpunkter där
det spelar roll) och **skarvar** (där två subsystem möts och fel fortplantar sig).

**Källmärkning per rad — lita olika på olika rader:**
- **[läst källa]** = filens kod lästes i sessionen 2026-07-03. Hög visshet.
- **[sett i referens]** = känd via import/anrop i annan läst kod. Medelvisshet om roll, låg om detaljer.
- **[dok/minne]** = känd via dokumentation eller tidigare sessioner, EJ läst denna session. Verifiera före du litar.

**Tre navtyper (börja gräva i ordning 1→2→3):**
1. **KOPPLINGSNAV** — där två subsystem möts. Fel här fortplantar sig MELLAN system. Gräv här FÖRST.
2. **KONTRAKTSNAV** — definierar en form alla andra rättar sig efter. Ändras ett kontrakt driver allt nedströms.
3. **MOTORNAV** — gör tunga jobbet men mest internt. Fel här är oftast LOKALA. Gräv här SIST.

**Bärande arkitektur-mönster (hela pipelinen i en mening):**
lokal Windows = **FÖRE** (data prep, SQL, DW) → Azure VM = **MOTOR** (modellräkning) →
lokal Windows = **EFTER** (Excel/xlwings, kan ej köra på Linux). **Blob Storage är kopplingslagret**
mellan alla tre. Tre familjer (cluster/site/bundle) delar samma stommar, copy-adapt (FD.34) —
en brist i en familj finns nästan säkert i de andra två (BB.13, horisontell validering).

---

## 1. KOPPLINGSNAV — skarvarna där subsystem möts (gräv här FÖRST)

### `blob.py`  ·  `orchestration/infrastructure/`  ·  [läst källa]
**Det enskilt viktigaste navet.** Kopplingslagret mellan ALLT: FÖRE↔MOTOR↔EFTER går via Blob,
och varje läsning/skrivning passerar här. Bär tre containrar (`runstatus`, `output`, `input` +
`pipeline` för facit) och auth-växeln `PRICINGMODEL_AUTH` (key/aad — FD.29). `_AFTER_INPUTS`-tabellen
(rad ~236) definierar EXAKT vilka filer EFTER-kedjan hämtar och VAR de placeras — det är den enda
källan till sanning för PULL-destinationerna. **Skarvar:** importeras av alla runners + run_after +
webapp + status_ops. **Gräv här när:** något om filplacering, Blob-auth, PULL/PUSH, eller
"filen finns inte där jag väntade". Nattens tre kontamineringar bodde alla i denna fils domän.

### `run_after.py`  ·  `orchestration/runners/`  ·  [läst källa]
EFTER-kedjans dirigent (FD.37): PULL → step6 (subprocess) → build_r12 (subprocess) → PUSH →
finalize. **Skarv mellan tre subsystem:** importerar `run_status` (kontrakt) OCH `blob` (Azure)
OCH kör de lokala step-scripten. Den enda plats där hela EFTER-flödet möts. **Gräv här när:**
något i väven, kvitton, eller run_id-hantering för efterbearbetning strular. Datumlås-patchad
(window.py), men site_step5 ingår EJ i kedjan (medveten FD.37-design).

### `run_data.py`  ·  `orchestration/runners/`  ·  [läst källa]
FÖRE-kedjans dirigent (FD.26): DW-regenerering → parquet → Blob-upload. **Skarv mellan
Business_Analytics (regen-scriptet) och Azure (upload).** `REGEN_SCRIPT`-konstanten pekar på
BA-repots regen (survival-kritiskt: pekar på `_v2`, contract-checked). **Gräv här när:** bränsle-
data (parquet) saknas/är stale, eller FÖRE-ledet ska köras skarpt (juni-fönstret härnäst).

### `run_{cluster,site,bundle}_model.py`  ·  `orchestration/runners/`  ·  [läst källa]
MOTOR-dirigenterna, en per familj (copy-adapt). **Skarv mellan lokal och VM:** deploy config → VM,
launch (detached SSH), poll, fetch outputs, auto-validera, upload till Blob. `EXPECTED_KEYS` styr
KEY-rapportering (cluster=None efter Leverans 2-fix). **Gräv här när:** en familjs VM-körning fallerar,
config-drift repo-vs-VM misstänks, eller output-hämtning strular (BB.9: per-fil-scp, tar-fix pending).
**Horisontell regel:** hittar du en brist i en, kolla de andra två (BB.13).

### `azure_vm.py`  ·  `orchestration/infrastructure/`  ·  [läst källa]
VM-livscykelnavet: start/deallocate, SSH-exec, detached launch (A2-fix: pgrep-verifierad relaunch),
selftest. **Skarv mellan lokal PowerShell och VM Linux.** **Gräv här när:** VM startar inte/hänger,
SSH-tunnel-blink, launch dör efter serie anrop. STÅENDE: deallocate + get-instance-view-verifiering
efteråt (LB.60 — lita inte på loggraden; kostar ~9 kr/h).

### `export_b4b_for_model.py`  ·  Business_Analytics  ·  [dok/minne]
BA-vägens bränsle-export (29 BCG-referenser — mest refererade BA-filen). **Skarv mellan DW och
pipeline.** En av två prep-vägar; bär `No of Sites` (mellanslag) — divergensklassen mot SQL-prep.
**Gräv här när:** rådata-schema eller DW-extraktion. [EJ läst denna session — verifiera schema mot faktisk fil.]

---

## 2. KONTRAKTSNAV — formen alla rättar sig efter (gräv här när nedströms driver fel)

### `run_status.py`  ·  `orchestration/shared/`  ·  [läst källa]
**Statuskontraktet — härledningskällan för hela etappmodellen.** Definierar `window_run_id`
(run_id = datafönster), `PhaseLocation` (vm/local), `default_pipeline` (de 7 faserna),
`finalize` (härleder run-nivå ur faser — heartbeat-spöket dött). **Allt annat härleds härifrån:**
sonder, dashboard, status_ops, all_chain_validator. **Gräv här när:** faser, run_id-format, eller
statuslogik. Ändras detta driver det ALLT nedströms — rör med största respekt.

### `Constant.py`  ·  `Pipeline/.../6. Fall Back Logic/`  ·  [läst källa]
**Step6:s knutpunkt — väver ihop alla tre familjers output.** 7 sökvägar (rad 8/11/14/18 m.fl.):
`blended_model_path` (cluster ready), `prod_site_level_path`, `bundle_cluster_level_path`,
`blended_output_path` (FD.15 frozen). **Skarv där familjerna möts i väven.** OBS: `blended_model_path`
= `output_summary_ready.xlsx` — DET var stub-kanalen nattens cluster-kontaminering bodde i.
**Gräv här när:** step6 väver på fel/stale material, eller en familjs gren saknas i Final_Fallback.

### `config.yml` (per familj)  ·  `.../code/src/`  ·  [läst källa]
Familjespecifikt kontrakt: input-sökvägar (`output_summary_path`, `model_summary_save_path`,
`raw_input_data`), `col_type` (schema-typning — cluster-maj-kraschen bodde här), `cols_to_try`
(feature-kandidater). `module_path: "../.."` styr all sökvägsupplösning. **Gräv här när:** en familjs
schema, feature-urval, eller input-plats. **Tre olika filer** — cluster/site/bundle skiljer sig
(site saknar `src`-mellanmapp: scriptet i `code\`, config i `code\src\`).

### `constants.py` (per familj)  ·  `.../code/src/`  ·  [läst källa]
Fältnamn-kontrakt: `KEY`, `DATE` (week_starting_monday), `KEY_WEEK`, `PVALUE_PREFIX`, `itr`-suffix
(styr mellanfilernas namn), env-läsning (`BCG_START_DATE`/`BCG_END_DATE` — G7 datumstyrning).
**Gräv här när:** kolumnnamn, iterationssuffix, eller datumfönster-parametrisering.

### `01_process.sql`  ·  `.../Sweden_Elasticity_Data_Prep_SQL/scripts/`  ·  [sett i referens]
SQL-prep-vägen (andra prep-vägen): DW → maj-CSV. Bär `No_of_Sites` (understreck) och skapar EJ
`TotalNetXVat` — divergensklassen mot BA-vägen. **Skarv mellan DW och modell-input.** **Gräv här
när:** SQL-prep-schema eller den kanoniska prep-vägens output. [EJ läst i detalj — verifiera kolumner mot fil.]

---

## 3. MOTORNAV — tunga jobbet, mest internt (gräv här SIST, fel är lokala)

### `feature_selection.py`  ·  `.../code/src/`  ·  [läst källa]
Kombinatorisk feature-selektion, Ray-parallelliserad. Bygger delmängder av `cols_to_try` rakt in i
fit UTAN skärning mot df-kolumner (rad ~302) — därför fäller en fantomkolumn hela steget.
`col_type`-astype-loopen (rad ~533) itererar df:s kolumner (extra nycklar ofarliga, saknad = KeyError).
Two-pass control_file-regel. **Gräv här när:** modellsteg 3 kraschar eller feature-urval beter sig fel.

### `model.py`  ·  `.../code/src/`  ·  [läst källa]
OLS log-log-regression per KEY. Namn-agnostisk (refererar inga schema-kolumnnamn direkt).
**Gräv här när:** elasticitetsberäkningen i sig, inte data-in.

### `data_prep_after_model_output.py`  ·  `.../code/`  ·  [läst källa]
**Step 5** (ej i run_after-kedjan — körs via familjens launcher). Läser config CWD-relativt
(`.\output\`-fälla), skriver mellanfiler + uppdaterar 87MB Excel-MALL in-place via xlwings
(named range Model_output/AvP — LB.53-känsligt). **Gräv här när:** Sitecode-summeringen eller
xlwings-mall-skrivningen strular. OBS: mallen är INPUT som modifieras, inte en nyskapad output.

### `regular_price.py` · `data_prepration.py`  ·  `.../code/src/`  ·  [sett i referens]
Launcher-script 1 (regular price) och 2 (data prep) av 5. Bygger `ivc_sweden_price.csv` (regenererbar,
deterministisk ur rådata) och `data_for_model.csv`. **Gräv här när:** pris-transform eller
för-modell-data. [Sett i launcher-sekvensen, ej lästa i detalj.]

### `Fall_Back_Logic.py`  ·  `.../6. Fall Back Logic/`  ·  [läst källa]
Step6-vävens motor (F1–F7 fallback-logik). BCG-original, rörs ej direkt. Läser sina inputs via
`Constant.py`-sökvägarna. Kastar på kosmetisk mall-skrivning men skriver DATA först (LB.53:
[RUN-WARN], treating as success). **Gräv här när:** fallback-logikens innehåll — men rör additivt.

### `launcher.py` (per familj)  ·  `.../code/src/`  ·  [läst källa]
Kör de 5 familjescripten i sekvens (regular_price → data_prep → feature_selection → model →
data_prep_after) via `subprocess.run` UTAN cwd-arg (ärver anroparens CWD — .\output\-fällan).
**Gräv här när:** du vill köra en familjs hela lokala kedja, eller förstå körordningen.

---

## 4. DATA-NAV (parquet/facit — bär tillstånd mellan körningar)

### `transaction_data.parquet`  ·  BA `parquet/`  ·  [dok/minne]
Bränslekällan: DW-transaktioner, regenereras per fönster (LB.50/G7 — MÅSTE regenereras FÖRST
för ny period, annars filtreras ny data tyst bort). **Gräv här när:** modellen "saknar" nya månader.

### `regenerate_transaction_parquet_chunked_v2.py`  ·  Business_Analytics  ·  [dok/minne]
Regen-scriptet run_data anropar (kanonisk efter E.8-städ; övriga varianter arkiverade). Kontrakt:
`--end/--out/--overwrite`. **Gräv här när:** parquet-regenerering. [Trackad i git; kontrakt-verifierad, ej läst i detalj.]

### `sweden_master_data.parquet` · `data_access.py`  ·  Business_Analytics  ·  [dok/minne]
Master-data resp. DW-åtkomstmodul (6 BCG-referenser, dokumenterad i MASTER_AZURE). **Skarv mot DW.**
**Gräv här när:** DW-koppling, master-data-schema. [EJ läst denna session — verifiera roll mot faktisk fil.]

### Frozen facit (Blob `pipeline/00_frozen_facit/`)  ·  [läst via _AFTER_INPUTS]
De frusna låsen EFTER-kedjan väver in: cluster_step5 (FD.15), bundle (FD.11), weave_weights (FD.14),
tx-CSV. Rapporteras alltid REVIEW (ärlighet, ej fel). **Gräv här när:** en frusen komponent ska tinas.

---

## 5. Z-LAGRET (produktionssättning — Phase Z)  ·  [dok/minne, EJ läst denna session]

### `setup_z0_foundation` · `setup_z2_roles` · `preflight_check`
Nämnda i din nav-lista och i Phase Z-planeringen (ROADMAP), men INGEN av dessa lästes i denna
session. **Jag kan inte beskriva vad de gör med visshet.** Trolig roll ur namn + kontext:
Z0 = infrastruktur-grund (resursgrupp/storage/VM-provisionering), Z2 = Azure-rolltilldelning
(sannolikt kopplat till Kent-beroendet/Blob-dataplansrollen), preflight_check = förkörnings-
validering för schemalagd drift. **FÖRSTA ÅTGÄRD nästa gång dessa blir aktuella: läs dem, denna
rad är hypotes.** Phase Z är gated på FAS T (Kents roll) — dessa filer är sannolikt förberedelse
för fire-and-forget-automation som ännu inte är aktiv.

---

## Gräv-här-snabbguide (symptom → nav)

| Symptom | Börja i | Navtyp |
|---|---|---|
| Fil finns inte där koden väntar / stale / stub | `blob.py` (_AFTER_INPUTS) + `input_provenance_probe` | Koppling |
| Väven har fel/tom familjegren | `Constant.py` → familjens output-position | Kontrakt→Motor |
| En familjs VM-körning fallerar | `run_{familj}_model.py` → `azure_vm.py` | Koppling |
| Modellsteg 3 kraschar (KeyError/feature) | familjens `config.yml` → `feature_selection.py` | Kontrakt→Motor |
| Ny månad saknas i output | `transaction_data.parquet` + regen (LB.50) | Data |
| Status/faser/run_id fel | `run_status.py` | Kontrakt |
| Blob-auth / behörighet | `blob.py` (_AUTH_MODE) + PIM/Kent | Koppling |
| Step 5 / Sitecode-summering / xlwings | `data_prep_after_model_output.py` | Motor |
| Kvitton följer inte vald period | Blob-struktur (FD.33) + webapp | (Blob-passet) |

## Metodnot till framtida sessioner
Denna karta har tre vissheter (källmärkta). **Innan du litar på en [dok/minne]- eller [sett i
referens]-rad: läs filen.** Nattens dyraste läxa (2026-07-03) var att gissa filers placering och
roll i stället för att läsa källan — fyra sökvägsgissningar, tre kontamineringar. Kartan pekar VAR
du ska gräva; den ersätter inte spaden. A.9b: källa före hypotes.

# evbcgpricing

Replikering, validering och drift av BCG:s prissättningsmodell för Evidensia Djursjukvård AB.

**Utvecklare:** Jens Palmö (Senior Business Analyst)
**Status (2026-05-27):** **Hela replikeringen (FR-1..7) är KLAR och bit-för-bit bevisad.** Steg 6
(`Fall_Back_Logic.py`, F1–F7-väv) validerades mot BCG:s facit: korrelation 1,000000, |diff|=0,
F1–F7-fördelning identisk, 100 % nivåmatch över 108 979 rader. Därmed är *hela* BCG-kedjan
(dataprep → cluster → site → bundle → blend → fallback) reproducerad och verifierad. Nästa: FAS V
(`verify_tool` — repeterbart bevis-bibliotek), sedan färsk-data-fasen. Se `ROADMAP.md` (fas-/mognadsvy)
och `BCG_PRICING_PLAYBOOK.md` (auktoritativt riktningsblock; fas-status där uppdateras till FR-7-stängt
i nästa städsteg).

---

## Project Status — Milestone Tracker (for decision-makers)

**One-line status:** We have proven we fully own BCG's pricing method — every stage reproduces BCG's own
results, the final stage to the decimal. The remaining work is running that proven method on current
data, in a managed environment.

### Achieved

| # | Milestone | What it proved (business terms) | Status |
|---|---|---|---|
| 1 | Source of truth established | BCG's model was always built on *our* data (`Fact_BillingInvoiceRows` + `Dim_Item`) — confirmed code-by-code (median ratio 1.0000, corr 0.989). No external dependency we don't control. | ✅ |
| 2 | Revenue & volume definitions locked | Settled which numbers the model uses: revenue = gross incl. VAT, volume = `SoldQuantity`. Earlier assumptions were wrong; data decided, not column names. | ✅ |
| 3 | Data-prep golden reference | BCG's data preparation reproduced through an independent engine and validated bit-for-bit against BCG's frozen file. We can regenerate the model's input ourselves. | ✅ |
| 4 | Code-level baseline | A grouping-independent baseline (13,223 codes) future data builds validate against — so re-grouping never breaks comparability. | ✅ |
| 5 | DW schema confirmed | Every field BCG's method needs exists in our data warehouse. The build is ours to run — no consultant, no missing data. | ✅ |
| 6 | Cluster model replicated | 3,812 product×cluster elasticities; significance 18.0% ≈ BCG's own 17.8% — faithful replication, not weaker results. | ✅ |
| 7 | Site model replicated | 4,673 product×site elasticities reproduced and validated. | ✅ |
| 8 | Bundle model replicated | 125 basket-level elasticities reproduced and validated. | ✅ |
| 9 | Cluster blend (step 5) replicated | Representative-selection logic that makes sparse groups usable, proven piece-by-piece (43/43). | ✅ |
| 10 | Fallback weave (step 6) replicated | Full 7-level fallback assigning a final elasticity to every product — proven **bit-for-bit**: correlation 1.000000, zero difference, 100% level match across 108,979 rows. | ✅ |
| 11 | **Full replication closed (FR-1..7)** | **The entire BCG pipeline reproduces BCG's results exactly on the original data. We demonstrably own the method.** | ✅ |

### Ahead

| Phase | Milestone | What it will prove (business terms) | Status |
|---|---|---|---|
| V | Proof library (`verify_tool`) | Independent, re-runnable checks — one per model part — so any result can be re-verified live on demand (e.g. when a decision-maker questions quality). Turns "trust us" into "watch us prove it." | 🟢 Next, ready |
| T | Technical-debt brief to IT | A structured ask so the pipeline lives in a managed environment, not only on one analyst's machine. Prerequisite for production. | 🟢 Ready (no code) |
| F | Fresh-data run | Run the proven method on current 2026 data — *the actual product*. Requires parametrizing a hard-coded date window (today it silently drops post-2025 data) and building the SQL data-prep on our DW. | 🟡 Partly ready |
| A | Robust Azure environment | Move the cleaned structure into a managed, repeatable (optionally scheduled) environment — runnable by more than one person. | 🔴 Blocked on T + F |

**What this means:** The value is not in re-deriving insights BCG already delivered on old data — it is in
running that same method on fresh data, with differences small enough not to flip a top-line price decision
(`IB.6`). The fresh-data run (phase F) is the next substantive step toward business value; phases V and T
de-risk and prepare it.

---

## Dokumentkarta — var saker bor

Projektet följer en **trelagersmodell** för att hålla dokumentationen ren mellan två parallella projekt
(detta + `Business_Analytics`):

| Lager | Filer | Innehåll |
|---|---|---|
| **Universellt** (alla projekt) | `KÄRNPRINCIPER.md`, `NEXT_SESSION_TEMPLATE.md` | Principer, arbetssätt, mallar — projektoberoende |
| **Stack-master** (per teknik) | `MASTER_PYTHON.md`, `MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md` | Tekniska lärdomar som gäller oavsett projekt (token, compute, encoding) |
| **Projektspecifikt** (detta repo) | se nedan | BCG-replikeringens egna lärdomar, insikter, nuläge |

**Projektspecifika navfiler (detta repo):**

| Fil | Roll |
|---|---|
| `BCG_PRICING_PLAYBOOK.md` | **Navet.** Fullständigt nuläge: riktningsblock (auktoritativt), beslut, faser, FR-definition, risker. Läs riktningsblocket först. |
| `ROADMAP.md` | **Fas-/mognadsvy** (V→T→F→A) för beslutsfattare — var står vi, vad är moget. Kompletterar playbookens riktningsblock. |
| `LESSONS_BCG.md` | Tekniska lärdomar (`LB.1`–`LB.23`), Symptom→Rotorsak→Regel. Befordras till MASTER_* när universella. |
| `INSIGHTS_BCG.md` | Affärs-/domäninsikter (`IB.1`–`IB.9`) om BCG:s modell och vår data. Skilt från tekniska lärdomar. |
| `TECHNICAL_PREREQUISITES.md` | Spår B (DW-native / SQL data prep): förutsättningar, omsvängning, valideringsgrind, modellkontrakt. |
| `NEXT_SESSION.md` | Kall-start för nästa arbetspass — konkret mål, pre-flight, blockerare. |
| `UBUNTU_AZURE_VM.md` | Linux/bash-handhavande, encoding-fällor, tmux, driftkort. |

> **Princip:** En lärdom föds projektspecifikt (`LESSONS_BCG.md`) och **befordras** uppåt till en
> stack-master när den visar sig gälla fler projekt än BCG. Det håller den projektspecifika listan kort
> och master-filerna auktoritativa. Tre ytor, tre syften, ingen dubblering: README = "vad är läget" (utåt),
> ROADMAP = "vart bär det och hur moget", playbook = "vad gör vi härnäst och varför".

---

## Syfte

Ett externt konsultbolag (BCG X) byggde en priselasticitetsmodell vars input produceras av en
Python-pipeline ovanpå SQL-städad data. Excel-prismodellen behöver uppdaterad input, och målet
är att Evidensia ska kunna **drifta hela flödet själv**. Detta repo håller vårt arbete med att
först *replikera* konsulternas flöde verbatim, *validera* det mot deras frusna facit, och på sikt
*migrera* SQL-prepningen till egna DW-vyer.

Repot innehåller **våra** artefakter (playbook, dokumentation, verktygsscript) samt pipelinens
**recept** (kod, config, control-filer, kurerade inputs) — men inte den datatunga outputen eller
GB-tunga rådata, som lever i källan (V2_New) och på Azure.

**Affärsmålet (det som räknas till slut):** köra den nu facit-validerade modellen på **färsk (refreshad)
data**, med diffar små nog att inte flippa ett top-line-prisbeslut (`IB.6`). Replikeringsarbetet är
grundläggning — det bevisar att vi äger logiken; produkten är den färska körningen.

---

## Arkitektur (dataflöde)

```
Rådata (transaktioner, dimensioner)
  + klustermappning (01. Clustering)
  + produktiv tid
        |
        v
  SQL data prep (DuckDB, ersätter Alteryx)  -->  weekly_model_data
        |
        v
  Modellsteg 2/3/5 (OLS per produktgrupp, Ray-parallell, feature-selection)
        |                                          |              |
        v                                          v              v
  Cluster-modell (folder 2)              Site-modell      Bundle-modell
        |                                 (folder 3)       (folder 5)
        v                                     |                |
  Steg 5: blended_logic (representant-väljare) |                |
        |   -> final_model_cluster_granularity |                |
        +-------------------+------------------+----------------+
                            v
  Steg 6: Fall Back Logic (F1–F7, combine_first-prioritet)  -->  final_elasticity
                            |
                            v
  BCG Pricing Model vFinal.xlsx (CALC_Elasticity, VTL)  <-- slutkonsument
```

Beräkningskärna: OLS-regression per produktgrupp (`statsmodels`), priskoefficienten = elasticitet
(log-log → koefficienten ÄR elasticiteten, `IB.7`). Parallellisering via Ray. Glesa grupper hanteras
via **steg 5** (cluster-representant-väljare, `IB.2`) och **steg 6** (F1–F7-fallback över
site/bundle/cluster-nivåer). Allt config-styrt (`config.yml`).

---

## Replikeringen — vad som körts och validerats

Hela kedjan är reproducerad och verifierad mot BCG:s frusna facit. Sammanfattning per familj/steg:

| Familj / steg | FR | Grupper / rader | Median elasticitet | Neg-andel | p<0,05 | Facit-validering |
|---|---|---:|---:|---:|---:|---|
| Cluster (produkt×kluster) | FR-4 ✅ | 3812 | −0,138 | 76,5 % | 18,0 % | ≈ BCG 17,8 % (`IB.1`) |
| Site (produkt×site) | FR-5 ✅ | 4673 | −0,054 | 62,4 % | 9,3 % | körd + verifierad (`IB.9`) |
| Bundle (varukorgar/klinik) | FR-6 ✅ | 125 | −0,211 | 85,6 % | 22,4 % | körd + verifierad (`IB.9`) |
| Steg 5 (cluster-blend) | FR-3 ✅ | 43/43 repr. | — | — | — | bit-för-bit (618/1276 rescue) |
| Steg 6 (F1–F7-väv) | FR-7 ✅ | 108 979 / 15 128 PK | — | — | — | **korr 1,0, \|diff\|=0, 100 % nivåmatch** |

**Tolkning (se `IB.9`):** Grövre granularitet → starkare/renare elasticitet. Cluster:s 18,0 % rå
signifikans matchar BCG:s frusna 17,8 % (`IB.1`) — trogen replikering bekräftad. Site:s svaga tal är
väntade (finast nivå, tunnast data per grupp); det är just därför fallback (steg 6) finns. Bundle är
renast (grövst, naturlig prisvariation, inga svansextremer).

**Steg 6-stängningen (FR-7, 2026-05-27):** BCG:s original kördes orört i en trogen arbetskopia mot BCG:s
egen input; vår output jämfördes per rad-grain (`ProductKey + SiteCode + Clusters`) mot BCG:s facit.
Path-"mismatchen" som tidigare antogs visade sig vara ett dokumentationsspöke — `Constant.py` var korrekt;
filerna behövde bara ligga där den orörda koden läser. Verktyg + lärdomar (`LB.21`–`LB.23`, `IB.2`-korr.)
committade. Se `LESSONS_BCG.md` / `INSIGHTS_BCG.md`.

**Plattformslärdomar (se `LB.17`–`LB.23`):** VM-passet bar Windows/stor-maskin-rester som scannades och
fixades i förväg (`C:\ray_spill`, `ray: memory/cpus` kalibrerade för fel hårdvara). Steg 5/6:s xlwings-steg
är icke-körbart på Linux men onödigt för validering (`output_summary.xlsx` produceras före det, och
dv8/dashboard-skrivningen är kosmetisk). Execution policy blockerar osignerade `.ps1` (`LB.21`) → leverera
kommandoblock eller `.py`.

---

## Roadmap

Fas-/mognadsvyn (V→T→F→A) bor i `ROADMAP.md`. Replikeringssidan (FR-1..7) är **stängd**; nedan är
kvarvarande faser i sammandrag. Där detaljer krockar gäller `BCG_PRICING_PLAYBOOK.md`s riktningsblock.

| Fas | Innehåll | Status |
|---|---|---|
| FR-1..7 | Hela replikeringen (dataprep → cluster → site → bundle → blend → fallback) | ✅ **Klar — bit-för-bit bevisad** |
| **V** | `verify_tool` — bibliotek av oberoende, repeterbara verifierare per modelldel | 🟢 **Nästa — moget, allt finns** |
| **T** | Teknisk skuld → IT (varför VM, AppLocker, blob-roller, execution policy, G7) | 🟢 Redo (parallellt, ingen kod) |
| **F** | Färsk data: G7-datumparametrisering + output-rimlighetsgrind + SQL data prep (B.4b) + FTE Väg 2 | 🟡 Delvis — SQL-bygget återstår |
| **A** | Robust Azure-miljö — flytta städad struktur dit, körbar/schemalagd | 🔴 Beror på T + F |

> **\"Full replikering så långt det är relevant\"** definierades som FR-1..7 i playbookens riktningsblock.
> **Samtliga FR-1..7 är nu klara.** Den kvarvarande vägen mot affärsmålet (`IB.6`) är färsk data (FAS F).

---

## Innehåll i repot

**Dokumentation:** `README.md` (denna), `BCG_PRICING_PLAYBOOK.md`, `ROADMAP.md`, `LESSONS_BCG.md`,
`INSIGHTS_BCG.md`, `TECHNICAL_PREREQUISITES.md`, `NEXT_SESSION.md`, `UBUNTU_AZURE_VM.md`.

**Verktygsscript (våra):**

| Fil | Roll |
|---|---|
| `verify_fallback.py` | **Steg 6-verifierare (FR-7).** Jämför vår F1–F7-output mot BCG-facit per rad-grain (population → F1–F7-fördelning → elasticitetskorr → nivåmatch). Fröet till `verify_tool` (FAS V). |
| `setup_step6_run.ps1` | Karta över steg 6:s arbetskopia (geometri + path-ankare). Dokumentation, körs ej (`LB.21`). |
| `patch_step6_xlwings.py` | Gör xlwings valfri i arbetskopian (idempotent) så steg 6 körs utan Excel-COM (`LB.23`). |
| `fallback_blend.py` | Steg 5-replikering (model_output + blended_logic), facit-validerad |
| `verify_output.py` | Rimlighetskoll av `output_summary.xlsx` (rader, kolumner, elasticitet min/median/max, neg-andel, p<0.05). Tar sökväg som argument; körs per familj. |
| `inventory_for_gitignore.py` | Read-only inventering: listar data/config med storlek + klass (recept vs output) |
| `map_bcg_source.py` | Read-only källkartläggning (kod i sin helhet, xlsx-struktur, skip-logik) |
| `inspect_fallback_source.py` | Read-only dump av steg 5-källa + dashboard-formler |
| `make_smoke_control.py` | Bygger rökstest-control-fil (N grupper `RUN=YES`, resten `NO`) |
| `compare_to_facit.py` | Validerar model `output_summary.xlsx` mot facit (KPI/population/kolumner) |
| `compare_features_to_facit.py` | Validerar feature_selection mot facit |
| `fix_config_encoding.py` | Strippar BOM från config.yml (PS-redigerings-fälla, `LB.10`) |
| `Scan-BCGFolder.ps1` | Kartlägger källmappens struktur |
| `Build-Structure.ps1` | Speglar V2_New:s mappstruktur till ren arbetsfolder |
| `Copy-Sources.ps1` | Kopierar kod/SQL/config/input verbatim till strukturen |

> **FAS V (nästa):** `verify_fallback.py`, `verify_output.py` m.fl. samlas i en `verify_tool\`-mapp —
> ett bevis-bibliotek där varje modelldel kan re-verifieras live på begäran, med README per verifierare
> (vad/mot vad/kommando/förväntat). Se `NEXT_SESSION.md`.

**Pipelinens recept (versionsstyrs):** `Pipeline/` + `Elasticity/`-trädens kod (`.py`), config
(`.yml`/`.yaml`), control-filer, SQL och kurerade inputs (mappningar, item-beskrivningar, FTE).

**Versionsstyrs INTE** (se `.gitignore`): Excel-output (`*.xlsx`/`*.xls`), tunga rådata/output-CSV:er
(>50 MB), `parquet/`, `output/`-mappar, `_step6_run/` (steg 6:s arbetskopia), körutfall/loggar, venv,
`__pycache__`. Strukturen är återskapningsbar: receptet finns, det tunga regenereras genom att köra
pipelinen.

---

## Daglig drift — Azure-VM (driftkort)

VM:en (`bcg-poc-vm`, 128 GB RAM) kostar **~8–10 kr/timme igång, nära noll deallokerad**.
Disken består vid deallocate — omstart bygger inte om något. Mönster: starta → jobba →
**deallokera så fort den inte används aktivt** (CZ.2 — vanligaste dyra missen).

Alla kommandon nedan körs i **PowerShell på Windows** om inget annat anges.

### Starta en arbetsdag

```powershell
az login --scope https://management.core.windows.net//.default
```
```powershell
az account set --subscription "ev-lz3-ai (SE)"
```
Aktivera PIM-rollen Contributor på `ev-openai-swce-rg-test` (Portal → PIM) om utgången. **OBS:** PIM-roll
OCH az-token kan båda gå ut mitt i ett långt pass (`AuthorizationFailed` på `deallocate` = PIM utgången;
`AADSTS70043` = token utgången). Återaktivera PIM i portalen → `az login` → kör om. För riktig drift:
Managed Identity (CZ.3) som inte löper ut.

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
ssh azureuser@172.18.148.4
```

På VM:en (bash): aktivera venv innan arbete. tmux-sessioner överlever **inte** en
deallocate/start-cykel. En NY tmux-session startar ett nytt skal → venv-aktiveringen måste göras om
inne i tmux (`LB.13`).

```
source ~/bcg/cluster/.venv/bin/activate
```

> **VM-disklayout:** `~/bcg/cluster/`, `~/bcg/site/`, `~/bcg/bundle/` (alla tre körklara, fixade),
> `~/bcg/_old_runs_20260521/` (undanflyttade gamla körningsrester), `~/verify_output.py` (rimlighetskoll).
> Cluster-venv (`~/bcg/cluster/.venv`, Python 3.11.9) återanvänds för alla tre familjer.

### Köra en lång körning frikopplad (tmux)

```
tmux new -s bcgrun
```
Inne i sessionen:
```
source ~/bcg/cluster/.venv/bin/activate
cd ~/bcg/cluster/code
python launcher.py 2>&1 | tee ~/run_log_PC_full.txt
```
Koppla loss: `Ctrl+B` (släpp) sedan `D`.

> **Notera:** modellstegens tunga körningar (Cluster/Site/Bundle) görs på VM. Steg 6 (F1–F7-väv) är lätt
> och körs lokalt på Windows (`_step6_run\`-arbetskopia) — se `LESSONS_BCG.md` (`LB.23`) och NEXT_SESSION.

### Kolla status utifrån

```powershell
ssh azureuser@172.18.148.4 "pgrep -af launcher.py | grep -v bash; echo '---'; grep -E 'Running|Finished|Error|Pipeline completed' ~/run_log_PC_full.txt; echo '---'; ls ~/bcg/cluster/output/model/automl/*.xlsx 2>/dev/null | wc -l; free -h | head -2"
```
> För feature_selection-progress: `ls automl/*.xlsx | wc -l` (antal körda grupper) är pålitligare än
> loggraden, som buffras (`LB.14`).

### Hämta hem resultat

```powershell
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/output_summary.xlsx "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx"
```
> `scp`/`ssh`/`az` körs ALLTID från PowerShell-sidan, ALDRIG inifrån VM:en (self-ssh-fälla, CZ.6).
> Skapa mål-mappen först om den saknas (`New-Item -ItemType Directory -Force -Path ...`).

### Avsluta (KRITISKT — annars tickar kostnaden)

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" --output tsv
```
→ Ska visa `VM deallocated`.

> **Token-utgång (E.3/CZ.3):** `az login`-token dör efter 4 h (Conditional Access, `AADSTS70043`).
> Logga in igen vid behov. Körningen på VM:en påverkas inte (lokala filer). För riktig drift: Managed Identity.

### Vid sessionsslut i repot

```powershell
git add <ändrade filer>
git commit -m "<imperativ engelsk fras>"
git push
```
Uppdatera `NEXT_SESSION.md` med ny startpunkt, `LESSONS_BCG.md`/`INSIGHTS_BCG.md` med nya lärdomar/insikter,
och relevanta MASTER_*.md om en lärdom befordrats.

---

## Miljönoteringar (Evidensia IT)

- **Inga `.exe`** i lösningen (AppLocker) — allt via `python -m`; duckdb = `pip install duckdb` på Linux.
- **Inga publika IP:n** (tenant-policy) — Azure-VM nås via privat IP från kontorsnätet.
- **Execution policy** blockerar osignerade `.ps1` (`LB.21`) — leverera flerstegsoperationer som
  inklistringsbara kommandoblock eller `.py` (körs AppLocker-rent via `python`), inte `.ps1` att anropa.
- **Windows-konsol-encoding:** script som dumpar källkod tvingar stdout UTF-8 (`LB.11`); PS-sidan
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` före körning (cp1252 kraschar på å/ä/ö, pilar).
- **Tre skal i spel vid VM-arbete:** PowerShell (`PS C:\`, kör `ssh`/`scp`/`az`), cmd (`C:\`, undvik —
  `&&` och PowerShell-cmdlets fungerar ej), bash på VM (`azureuser@bcg-poc-vm`, kör pipeline). Kolla
  alltid prompten innan ett kommando körs.
- Azure-detaljer, behörigheter och PIM: se `MASTER_AZURE.md` / `MASTER_AZURE_COMPUTE.md`.
- Linux/bash-handhavande för VM:en: se `UBUNTU_AZURE_VM.md`.

---

*README omstrukturerad 2026-05-27 efter FR-7-stängning: engelsk milstolpstabell (beslutsfattare) tillagd
överst; status-stycke, replikeringstabell, roadmap, dokumentkarta och verktygslista synkade till FR-1..7
klart + FAS V→A; LB-referens uppdaterad till LB.1–23; ROADMAP.md + verify_tool/setup/patch inlagda.
Driftkortet (Azure-VM) bevarat. Playbookens riktningsblock uppdateras till FR-7-stängt i nästa städsteg.*

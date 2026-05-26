# evbcgpricing

Replikering, validering och drift av BCG:s prissättningsmodell för Evidensia Djursjukvård AB.

**Utvecklare:** Jens Palmö (Senior Business Analyst)
**Status (2026-05-26):** Full replikering är klar till och med steg 5 (fallback / `blended_logic`,
facit-validerad bit-för-bit: 43/43 representanter, 618/1276 signifikanta). Det enda som återstår för
"full replikering" är ett **VM-körningspass** (Cluster full + Site + Bundle → tre `output_summary.xlsx`)
följt av steg 6-vävningen (F1–F7). Därefter färsk-data-fasen. Se `BCG_PRICING_PLAYBOOK.md` (riktningsblock
överst) för den auktoritativa nulägesbilden.

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
| `BCG_PRICING_PLAYBOOK.md` | **Navet.** Fullständigt nuläge: riktningsblock (auktoritativt), beslut, faser, FR-definition av "full replikering", risker. Läs riktningsblocket först. |
| `LESSONS_BCG.md` | Tekniska lärdomar (`LB.1`–), Symptom→Rotorsak→Regel. Befordras till MASTER_* när de visar sig universella. |
| `INSIGHTS_BCG.md` | Affärs-/domäninsikter (`IB.1`–) om BCG:s modell och vår data. Skilt från tekniska lärdomar. |
| `NEXT_SESSION.md` | Kall-start för nästa arbetspass — konkret mål, pre-flight, blockerare. |
| `SESSION_2026-05-25_STEG5_STEG6.md` | Sessionslogg: steg 5-validering + steg 6-kartläggning. |
| `UBUNTU_AZURE_VM.md` | Linux/bash-handhavande, encoding-fällor, tmux, driftkort. |

> **Princip:** En lärdom föds projektspecifikt (`LESSONS_BCG.md`) och **befordras** uppåt till en
> stack-master när den visar sig gälla fler projekt än BCG. Det håller den projektspecifika listan kort
> och master-filerna auktoritativa.

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
  Steg 6: Fall Back Logic (F1–F7, np.select-prioritet)  -->  final_elasticity
                            |
                            v
  BCG Pricing Model vFinal.xlsx (CALC_Elasticity, VTL)  <-- slutkonsument
```

Beräkningskärna: OLS-regression per produktgrupp (`statsmodels`), priskoefficienten = elasticitet
(log-log → koefficienten ÄR elasticiteten, `IB.7`). Parallellisering via Ray. Glesa grupper hanteras
via **steg 5** (cluster-representant-väljare, `IB.2`) och **steg 6** (F1–F7-fallback över
site/bundle/cluster-nivåer). Allt config-styrt (`config.yml`).

---

## Roadmap

Statusen nedan är synkad med playbookens riktningsblock (`BCG_PRICING_PLAYBOOK.md`). Där detaljer krockar
gäller playbooken.

| Fas | Innehåll | Status |
|---|---|---|
| 0 | Orientering, struktur-scan, källval, rotorsaksanalys | ✅ Klar |
| 1 | Replikera struktur + kopiera källor verbatim | ✅ Klar |
| 2 | Bygga miljö (venv + requirements) | ✅ Klar (lokalt + Azure-VM) |
| 3 | Ray-config + feature_selection (brute-force) | ✅ Klar (Azure, validerad mot facit) |
| 8 | Azure-motor: VM, miljö, modellkörning | ✅ Klar (tunga steg körda fullt) |
| 4 (model) | OLS-regression per grupp | ✅ Klar (bit-för-bit-match mot facit) |
| 7 | Validera output mot facit (KPI, population, features) | ✅ Klar |
| 4 (input) | regular_price + data_prepration → `data_for_model.csv` | ✅ Klar (bit-för-bit identisk med BCG:s) |
| 5 | `data_prep_after_model` / `blended_logic` (cluster-fallback) | ✅ Klar — facit-validerad bit-för-bit (43/43, 618/1276) |
| — | **VM-körningspass: Cluster full + Site + Bundle** | 🔴 **Nästa — enda kvarvarande för full replikering** |
| 6 | Fall Back Logic (F1–F7 multi-model-blend) | 🔴 Kartlagd; blockerad av VM-passet |
| 4 (SQL prep) | SQL data prep (duckdb via Python, ej exe) | ⬜ Egen fas (DW-migrering) |
| — | Output-rimlighetsgrind | 🔴 Färsk-data-fasen — byggs mot färdig baslinje, ej nu |
| — | Färsk data: parametrisera datumfönster (G7) + FTE Väg 2 | 🔴 Senare |
| 9 | Git-baslinje (detta repo) | ✅ Klar — receptet pushat, output/tungt/Excel utestängt |
| B | DW-vyer + Blob input-folder (drift) | ⬜ Senare |

> **"Full replikering så långt det är relevant"** är definierad som en checklista (FR-1..7) i playbookens
> riktningsblock. FR-1..3 är klara; FR-4..7 = VM-passet + steg 6. Det är den kvarvarande kritiska vägen.

### Vad som validerades 2026-05-25 (steg 5 — fallback)

- ✅ **`fallback_blend.py`** (fristående replikering av `model_output` + `blended_logic`) körd på
  **BCG:s egen fulla `output_summary.xlsx`** (3812 KEY) → **43/43 representanter identiska** med
  BCG:s `final_model_cluster_granularity.xlsx`. `Significant?`-flagga 43/43. PASS.
- ✅ **Rescue-effekten bekräftad:** `pre-blend 1541/3812` → `post-blend 618/1276`. Fallback =
  representant-väljare (ingen ommodellering, `IB.2`); `Significant?` = `RSQ≥0.5 & p≤0.2` (inte p<0.05).
- ✅ **Site-modell (folder 3) bekräftad strukturellt identisk med Cluster** — samma pipeline-filer,
  samma `output_summary.xlsx`-format. Ingen ombyggnad krävs; körs som Cluster (`LB.4`).
- ✅ **Steg 6-kontrakt känt:** `Fall_Back_Logic.py` läser tre `output_summary.xlsx` (cluster/site/
  bundle) + vår steg 5-output, väver F1–F7 via `np.select`-prioritet. Ny logik enbart i vävningen.

**Detaljerad sessionslogg + lärdomar:** se `SESSION_2026-05-25_STEG5_STEG6.md`.
**Detaljerad bash/Linux-handhavande och driftkort:** se `UBUNTU_AZURE_VM.md`.

---

## Innehåll i repot

**Dokumentation:** `README.md` (denna), `BCG_PRICING_PLAYBOOK.md`, `LESSONS_BCG.md`, `INSIGHTS_BCG.md`,
`NEXT_SESSION.md`, `SESSION_2026-05-25_STEG5_STEG6.md`, `UBUNTU_AZURE_VM.md`, `TECHNICAL_PREREQUISITES.md`.

**Verktygsscript (våra):**

| Fil | Roll |
|---|---|
| `fallback_blend.py` | Steg 5-replikering (model_output + blended_logic), facit-validerad |
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

**Pipelinens recept (versionsstyrs):** `Pipeline/` + `Elasticity/`-trädens kod (`.py`), config
(`.yml`/`.yaml`), control-filer, SQL och kurerade inputs (mappningar, item-beskrivningar, FTE).

**Versionsstyrs INTE** (se `.gitignore`): Excel-output (`*.xlsx`/`*.xls`), tunga rådata/output-CSV:er
(>50 MB), `parquet/`, `output/`-mappar, körutfall/loggar, venv, `__pycache__`. Strukturen är
återskapningsbar: receptet finns, det tunga regenereras genom att köra pipelinen. `inventory_for_gitignore.py`
listar de tunga filerna så de är spårade i strukturen även utan att ligga i Git.

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
Aktivera PIM-rollen Contributor på `ev-openai-swce-rg-test` (Portal → PIM) om utgången.

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
ssh azureuser@172.18.148.4
```

På VM:en (bash): aktivera venv innan arbete. tmux-sessioner överlever **inte** en
deallocate/start-cykel.

```
source ~/bcg/cluster/.venv/bin/activate
```

### Köra en lång körning frikopplad (tmux)

```
tmux new -s bcgrun
```
Inne i sessionen:
```
source ~/bcg/cluster/.venv/bin/activate
cd ~/bcg/cluster/code
python model.py 2>&1 | tee ~/run_log_PC_full.txt
```
Koppla loss: `Ctrl+B` följt av `D`.

> **Nästa VM-pass (steg 6-input):** kör Cluster full + Site (folder 3) + Bundle (folder 5) → varje
> producerar sin `output_summary.xlsx`. Alla tre är VM-uppgifter (lokalt OOM). Verifiera först vad som
> ligger på VM:en (se `NEXT_SESSION.md`).

### Kolla status utifrån

```powershell
ssh azureuser@172.18.148.4 "pgrep -af model.py; grep -c 'Model running for' ~/run_log_PC_full.txt"
```
```powershell
ssh azureuser@172.18.148.4 "tail -3 ~/run_log_PC_full.txt; free -h"
```

### Hämta hem resultat

```powershell
scp -r azureuser@172.18.148.4:~/bcg/cluster/output/model "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\output\azure_run_model"
```

### Avsluta (KRITISKT — annars tickar kostnaden)

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" --output tsv
```
→ Ska visa `VM deallocated`.

> **Token-utgång (E.3/CZ.3):** `az login`-token dör efter 4 h (Conditional Access, `AADSTS70043`).
> Logga in igen vid behov. Körningen på VM:en påverkas inte. För riktig drift: Managed Identity.

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
- **Windows-konsol-encoding:** script som dumpar källkod tvingar stdout UTF-8 (`LB.11`); PS-sidan
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` före körning (cp1252 kraschar på å/ä/ö, pilar).
- Azure-detaljer, behörigheter och PIM: se `MASTER_AZURE.md` / `MASTER_AZURE_COMPUTE.md`.
- Linux/bash-handhavande för VM:en: se `UBUNTU_AZURE_VM.md`.

---

*README synkad 2026-05-26 mot playbookens riktningsblock + dokumentstruktur-omtaget (LESSONS_BCG,
INSIGHTS_BCG, trelagersmodell). Roadmap speglar full-replikering-checklistan (FR-1..7).*

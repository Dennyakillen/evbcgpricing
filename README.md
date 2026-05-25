# evbcgpricing

Replikering, validering och drift av BCG:s prissättningsmodell för Evidensia Djursjukvård AB.

**Utvecklare:** Jens Palmö (Senior Business Analyst)
**Status:** Hela den VM-körbara pipelinen (regular_price → data_prepration → feature_selection →
model) validerad bit-för-bit mot BCG:s frusna facit. **Steg 5 (fallback / `blended_logic`) nu också
facit-validerat bit-för-bit** (43/43 representanter, 618/1276 signifikanta). Steg 6 (F1–F7
multi-model-blend) är kartlagt; dess input (Site- + Bundle-modellernas output) återstår att köra på VM.

---

## Syfte

Ett externt konsultbolag (BCG X) byggde en priselasticitetsmodell vars input produceras av en
Python-pipeline ovanpå SQL-städad data. Excel-prismodellen behöver uppdaterad input, och målet
är att Evidensia ska kunna **drifta hela flödet själv**. Detta repo håller vårt arbete med att
först *replikera* konsulternas flöde verbatim, *validera* det mot deras frusna facit, och på sikt
*migrera* SQL-prepningen till egna DW-vyer.

Repot innehåller **våra** artefakter (playbook, dokumentation, verktygsscript) — inte BCG:s
datatunga pipeline, som lever i källan och i Azure.

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

Beräkningskärna: OLS-regression per produktgrupp (`statsmodels`), priskoefficienten = elasticitet.
Parallellisering via Ray. Glesa grupper hanteras via **steg 5** (cluster-representant-väljare) och
**steg 6** (F1–F7-fallback över site/bundle/cluster-nivåer). Allt config-styrt (`config.yml`).

---

## Roadmap

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
| **5** | **`data_prep_after_model` / `blended_logic` (cluster-fallback)** | ✅ **Klar — facit-validerad bit-för-bit (43/43, 618/1276)** |
| 4 (SQL prep) | SQL data prep (duckdb via Python, ej exe) | ⬜ Egen fas (DW-migrering) |
| — | **Full Cluster-körning (1311+ grupper) på VM** | ⬜ **Nästa (lokalt OOM)** |
| — | **Site-modell (folder 3) körning på VM** | ⬜ **Matar steg 6 F1** |
| — | **Bundle-modell (folder 5) körning på VM** | ⬜ **Matar steg 6 F2/F4** |
| **6** | **Fall Back Logic (F1–F7 multi-model-blend)** | ⬜ Kartlagd; blockerad av Site/Bundle-körning |
| — | Output-rimlighetsgrind | ⬜ Byggs **sist**, mot färdig baslinje |
| — | Färsk data: parametrisera datumfönster (G7) | ⬜ Senare |
| 9 | Git-baslinje (detta repo) | ✅ Pågår |
| B | DW-vyer + Blob input-folder (drift) | ⬜ Senare |

### Vad som validerades 2026-05-25 (steg 5 — fallback)

- ✅ **`fallback_blend.py`** (fristående replikering av `model_output` + `blended_logic`) körd på
  **BCG:s egen fulla `output_summary.xlsx`** (3812 KEY) → **43/43 representanter identiska** med
  BCG:s `final_model_cluster_granularity.xlsx`. `Significant?`-flagga 43/43. PASS.
- ✅ **Rescue-effekten bekräftad:** `pre-blend 1541/3812` → `post-blend 618/1276` — exakt de 618
  dokumenterade. Fallback = representant-väljare (ingen ommodellering); `Significant?` = `RSQ≥0.5 &
  p≤0.2` (inte p<0.05).
- ✅ **Site-modell (folder 3) bekräftad strukturellt identisk med Cluster** — samma pipeline-filer,
  samma `output_summary.xlsx`-format. Ingen ombyggnad krävs; körs som Cluster.
- ✅ **Steg 6-kontrakt känt:** `Fall_Back_Logic.py` läser tre `output_summary.xlsx` (cluster/site/
  bundle) + vår steg 5-output, väver F1–F7 via `np.select`-prioritet. Ny logik enbart i vävningen.
- 📌 **Nästa = VM-körningspass** (Cluster full + Site + Bundle) för att producera steg 6:s input.

**Detaljerad sessionslogg + lärdomar:** se `SESSION_2026-05-25_STEG5_STEG6.md`.
**Detaljerad bash/Linux-handhavande och driftkort:** se `UBUNTU_AZURE_VM.md`.

---

## Innehåll i repot

| Fil | Roll |
|---|---|
| `README.md` | Denna — syfte, arkitektur, roadmap, daglig drift |
| `BCG_PRICING_PLAYBOOK.md` | Fullständigt nuläge: beslut, faser, risker, lärdomar |
| `NEXT_SESSION.md` | Kall-start för nästa arbetspass |
| `SESSION_2026-05-25_STEG5_STEG6.md` | Steg 5-validering + steg 6-kartläggning + lärdomar |
| `UBUNTU_AZURE_VM.md` | Linux/bash-handhavande, encoding-fällor, tmux, driftkort |
| `fallback_blend.py` | **Steg 5-replikering (model_output + blended_logic), facit-validerad** |
| `map_bcg_source.py` | Read-only källkartläggning (kod i sin helhet, xlsx struktur, skip-logik) |
| `inspect_fallback_source.py` | Read-only dump av steg 5-källa + dashboard-formler |
| `make_smoke_control.py` | Bygger rökstest-control-fil (N grupper `RUN=YES`, resten `NO`) |
| `compare_to_facit.py` | Validerar model `output_summary.xlsx` mot facit (KPI/population/kolumner) |
| `compare_features_to_facit.py` | Validerar feature_selection mot facit |
| `Scan-BCGFolder.ps1` | Kartlägger källmappens struktur |
| `Build-Structure.ps1` | Speglar V2_New:s mappstruktur till ren arbetsfolder |
| `Copy-Sources.ps1` | Kopierar kod/SQL/config/input verbatim till strukturen |

Versionsstyrs **inte** (se `.gitignore`): `Pipeline/` (BCG:s verbatim-kod + GB data), venv,
parquet/csv/xlsx, körutfall (`blended_output*.csv`, `*_log.txt`, `bcg_map_*.txt`).

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
> producerar sin `output_summary.xlsx`. Site-input är 130 MB; alla tre är VM-uppgifter (lokalt OOM).

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
Uppdatera `NEXT_SESSION.md` med ny startpunkt, och relevanta MASTER_*.md med nya lärdomar.

---

## Miljönoteringar (Evidensia IT)

- **Inga `.exe`** i lösningen (AppLocker) — allt via `python -m`; duckdb = `pip install duckdb` på Linux.
- **Inga publika IP:n** (tenant-policy) — Azure-VM nås via privat IP från kontorsnätet.
- **Windows-konsol-encoding:** script som dumpar källkod tvingar stdout UTF-8; PS-sidan
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` före körning (cp1252 kraschar på å/ä/ö, pilar).
- Azure-detaljer, behörigheter och PIM: se `MASTER_AZURE.md` / `MASTER_AZURE_COMPUTE.md`.
- Linux/bash-handhavande för VM:en: se `UBUNTU_AZURE_VM.md`.

---

## Statusuppdatering 2026-05-25 — Steg 5 facit-validerat, steg 6 kartlagt

**Vad som är klart:** Steg 5 (`blended_logic` / cluster-fallback) replikerat fristående
(`fallback_blend.py`) och bevisat bit-för-bit mot BCG:s facit (43/43 representanter, 618/1276
signifikanta, alla fyra `New_cluster`-nivåer). Steg 6 (`Fall_Back_Logic.py`, F1–F7) kartlagt —
kontraktet känt, Site/Bundle bekräftade som samma pipeline (ingen ombyggnad).

**Korrigerade missförstånd:** fallback = representant-väljare (ej omklustring); `Significant?` =
`RSQ≥0.5 & p≤0.2` (ej p<0.05); rescue sker i blenden före flaggan räknas.

**Nästa:** VM-körningspass (Cluster full + Site + Bundle) → producerar steg 6:s tre `output_summary`-
input. Sedan steg 6-replikering, därefter rimlighetsgrind (sist) + färsk data. Se
`SESSION_2026-05-25_STEG5_STEG6.md` och `NEXT_SESSION.md` för full handoff.

# NEXT_SESSION — BCG Pricing (input-fasen)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_AZURE.md`,
`MASTER_AZURE_COMPUTE.md`. Linux/bash-handhavande: `UBUNTU_AZURE_VM.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git
- **Lokal arbetsrot:** `C:\Projekt\BCG`
- **Källa (facit):** `C:\Projekt\BCG\Elasticity\Product_Cluster\...` samt V2_New i OneDrive
- **Azure-VM:** `bcg-poc-vm` i `ev-openai-swce-rg-test` (sub `ev-lz3-ai`), privat IP `172.18.148.4`
- **Status:** VM **deallocated**. Allt arbete består på disken.
- **Azure-resultat hämtat lokalt** (gitignorerat):
  - `...\output\azure_run_model\` (model: output_summary, model_summary, model_results)
  - `...\output\azure_run_automl\` (feature_selection: 3812 _All_itrs + results/)

---

## Status vid sessionsstart

**Modell-delen är klar och validerad mot facit. Nästa front är input-stegen.**

- ✅ feature_selection + model körda i full skala på Azure (3812 grupper).
- ✅ Validerade mot facit: model bit-för-bit (elasticitet korr 1,0, max diff 0); feature_selection
  troget (93,1% identiskt feature-val, elasticitet/Adj R2 i praktiken identisk — avvikelser är
  gränsfallsfeatures utan resultatpåverkan).
- ✅ OOM avskriven: 128 GB, Ray-spill till `/tmp/ray_spill`, `Swap 0B` genomgående.
- ⛔ **Blockerat:** input-stegen kräver `InScope Mapping.xlsx` (O3 bekräftad) — saknas lokalt.
- 📌 Steg 5 (`data_prep_after_model`) är Windows/Excel (xlwings), ej VM-arbete (D14).

---

## Mål för denna session

### Primärt: input-fasen — köra och validera regular_price + data_prepration

**Blockerare först:** skaffa `InScope Mapping.xlsx` från Kent eller V2_New-källan. Utan den
dör `regular_price.py` direkt. Bekräfta även competitor-fil (`0619_*_competitors.xlsx`) och
icke-tom `date_to_month_year_mapping.csv`.

**Leveranser (kräver VM igen):**
1. Få upp de saknade input-filerna på VM:en (scp).
2. Kör `regular_price.py` → `ivc_sweden_price.csv`.
3. Kör `data_prepration.py` → vår egen `data_for_model.csv`.
4. **Validera vår `data_for_model.csv` mot BCG:s mellanfil** (population, kolumner, summor).
   Stänger cirkeln: om vår input-prep ger samma mellanfil, ger den samma modellresultat (redan validerat).

**Insikt:** Detta kräver VM (input-stegen är inte triviala lokalt). Starta → kör i tmux →
validera → **deallokera**. Samma mönster som modellstegen 2026-05-21.

### Separat spår (Windows): steg 5

`data_prep_after_model_output.py` körs på din Windows-maskin med Excel installerat (xlwings).
Inte VM-arbete. Tas när modell-/input-flödet är helt validerat.

---

## Pre-flight (kall start) — se README "Daglig drift" för fullständigt driftkort

```powershell
az login --scope https://management.core.windows.net//.default
```
```powershell
az account set --subscription "ev-lz3-ai (SE)"
```
PIM Contributor på `ev-openai-swce-rg-test` om utgången.
```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
Vänta ~1 min (annars `Connection refused`), sedan:
```powershell
ssh azureuser@172.18.148.4
```
På VM:en: `source ~/bcg/cluster/.venv/bin/activate`. tmux-sessioner är borta efter deallocate.

**Vid slut (KRITISKT):**
```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```

---

## Validering — tee:ad logg, dela aldrig rådata

```bash
python <script>.py 2>&1 | tee ~/run_log_<steg>.txt
```
```bash
grep -E "Running|Finished|Shape|\([0-9]+, ?[0-9]+\)|Error|Traceback|Saved|completed" ~/run_log_<steg>.txt
```
**R7:** verifiera output-filen (storlek/tidsstämpel), aldrig loggraden.

---

## Standarder särskilt relevanta nu

- **R7:** lita aldrig på "Pipeline completed".
- **Kostnad:** deallokera så fort VM:en inte används aktivt (CZ.2).
- **Token (E.3):** `az`-token dör efter 4 h; logga in igen.
- **D13:** plattformsanpassningar (hårdkodade Windows-sökvägar) är tillåtna minimalt, loggas §9.
- **L.14:** läs källan/verifiera encoding (`xxd`) innan fix.

## Öppna / blockerare

| # | Fråga | Behöver |
|---|---|---|
| O1 | Owner på RG | Kent — dataroller/Blob |
| O3 | `InScope Mapping.xlsx` | Bekräftad krävs — hämta från källa/Kent (blockerar input-fasen) |
| O4 | Blob + DW-vyer | Efter input-fasen |

*Skapad 2026-05-21 vid avslut av modellvalideringssessionen.*

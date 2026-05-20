# NEXT_SESSION — BCG Pricing PoC (Azure-körning)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_AZURE.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git
- **Lokal arbetsrot:** `C:\Projekt\BCG`
- **Replikerad pipeline (lokalt):** `C:\Projekt\BCG\Pipeline\02. Elasticity\...`
- **Källa (sanning):** `...\OneDrive\...\BCG\BCG_orginal_V2_New`
- **Azure-VM:** `bcg-poc-vm` i `ev-openai-swce-rg-test` (sub `ev-lz3-ai`), privat IP `172.18.148.4`
- **Status:** VM är **deallocated** (kostar inget). Måste startas för att jobba.

---

## Status vid sessionsstart

**Replikeringen är byggd och miljön verifierad lokalt; full körning kräver Azure (lokal OOM).**

- ✅ Fas 0–2 klara: struktur replikerad, källor kopierade verbatim, venv byggd lokalt.
- ✅ Ray-config löst: `config.yml` `ray:`-sektion (`cpus`/`memory`) — kodfri fix.
- ⚠️ Fas 3 lokalt: körningen OOM:ade på 31 GB RAM → flyttad till Azure.
- 🔄 Fas 8: Azure-VM byggd och nåbar via SSH från kontorsnätet. **Ingen körning gjord än.**
- ⛔ Blockerat: Blob-uppladdning väntar dataroll/Owner från Kent (ej nödvändigt för VM-PoC).

**Referensvärden:**
- VM: `Standard_E16s_v5`, 16 vCPU / 128 GB RAM, Ubuntu 22.04, 124 GB disk.
- Ray lokalt: `cpus: 12`, `memory: 8`. **På VM (128 GB): sätt `cpus: 14`, `memory: 32`.**
- Modellsteg 2 ensamt: ~2450 modellgrupper, 120+ min lokalt (kraschade).
- Facit att validera mot: BCG:s frusna `output\model\output_summary.xlsx`.

---

## Mål för denna session

### Primärt: Fas 8 — första validerade körningen på Azure-VM

**Syfte:** Få klusternivå-steget att köra hela vägen på VM:en och producera `output_summary.xlsx`.

**Leveranser:**
1. Python 3.11 + venv på VM:en, `requirements.txt` installerad (Linux → duckdb trivialt).
2. Kod + data uppe på VM:en (kod liten; data ~4 GB — välj metod: scp / azcopy / git+manuell data).
3. `config.yml` `ray:` satt för 128 GB (`cpus:14`, `memory:32`).
4. `launcher.py` körd med **tee:ad logg** (se nedan) → `output_summary.xlsx`.
5. Jämförelse mot BCG:s frusna facit (population, kolumner, summa, KPI).

**Datakälla:** `2. Product Cluster Level Models` (interim `0828_*` CSV:er, D6).

---

## Pre-flight (kall start)

```powershell
az login --scope https://management.core.windows.net//.default
```
```powershell
az account set --subscription "ev-lz3-ai (SE)"
```
Aktivera PIM-rollen Contributor på `ev-openai-swce-rg-test` (Azure Portal → PIM) om utgången.

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
ssh azureuser@172.18.148.4
```
Förväntat: Ubuntu-prompt `azureuser@bcg-poc-vm:~$`.

**Vid slut / paus (KRITISKT — annars tickar kostnaden):**
```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```

---

## Validering — tee:ad logg (spar tokens, dela aldrig rådata)

Kör pipelinen så loggen hamnar i fil, filtrera fram bara strukturrader:

```bash
python launcher.py 2>&1 | tee ~/run_log_PC.txt
```
```bash
grep -E "Running|Finished|Starting|Shape|\([0-9]+, ?[0-9]+\)|Error|Traceback|Saved|completed|stopping" ~/run_log_PC.txt
```
Skicka **bara** grep-utskriften + filfaktumet (tidsstämpel/storlek på `output_summary.xlsx`).
Aldrig rådata.

---

## Filer att ladda upp vid sessionsstart

| # | Fil | Syfte |
|---|---|---|
| 1 | `KÄRNPRINCIPER.md` | Universella principer |
| 2 | `MASTER_PYTHON.md` | Python-kontext |
| 3 | `MASTER_AZURE.md` (+ sektion 11–12) | Azure-kontext |
| 4 | `BCG_PRICING_PLAYBOOK.md` | Hela projektets nuläge och faser |
| 5 | Denna `NEXT_SESSION.md` | Startpunkt |

Vid behov (för metodaudit, ej replikering): `model.py`, `regular_price.py`,
`data_prepration.py` — stänger frågorna om regressionsform och endogenitet.

---

## Vid sessionsslut

1. `az vm deallocate` — bekräfta att VM:en är stoppad.
2. Committa playbook/README-uppdateringar, pusha till `evbcgpricing`.
3. Uppdatera denna fil: nytt status, nästa startpunkt.
4. Nya lärdomar → relevant MASTER_*.md.

---

## Standarder särskilt relevanta nu

- **R7:** lita aldrig på "Pipeline completed" — verifiera filen.
- **Kostnad:** `deallocate` så fort VM:en inte används aktivt.
- **exe dött:** allt via Python; duckdb = `pip install duckdb` på Linux.
- **L.14:** läs källan, verifiera filversion med `Select-String`/`grep` innan fix.

*Skapad 2026-05-20 vid avslut av Azure-PoC-sessionen.*

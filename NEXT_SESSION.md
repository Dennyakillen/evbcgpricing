# NEXT_SESSION — VM-körningspass (Cluster full + Site + Bundle → steg 6-input)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på Evidensia
Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md`,
`MASTER_PYTHON.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`
(läs riktningsblocket överst först). Lärdomar: `LESSONS_BCG.md` (`LB.N`). Insikter: `INSIGHTS_BCG.md` (`IB.N`).

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel) i
> `LESSONS_BCG.md`, eller ny insikt i `INSIGHTS_BCG.md`. Befordra till MASTER_* om generell.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Senaste commit på origin/main:** `85cd33f` — *Stop tracking generated run output and pipeline logs; extend gitignore*
- **Branch:** `main`
- **Repot innehåller nu hela receptet** (kod/config/control/kurerade inputs ur Pipeline/ + Elasticity/),
  Excel + tung output + körutfall utestängt. Strukturen är återskapningsbar.
- **Azure-VM:** `bcg-poc-vm`, `Standard_E16s_v5` (16 vCPU / 128 GB RAM), privat IP `172.18.148.4`,
  **deallocated** (disken består). Subscription `ev-lz3-ai (SE)`, RG `ev-openai-swce-rg-test` (PIM Contributor).
- **DW-script-venv** (om FTE Väg 2 berörs): `C:\Projekt\Business_Analytics\.venv` (`data_access.py`).

---

## Status vid sessionsstart

**Full replikering är klar t.o.m. FR-3 (steg 5 facit-validerad). Det enda kvarvarande för "full
replikering" är detta VM-pass + steg 6.**

- ✅ Klart: input-steg, model, feature_selection, steg 5-fallback — alla facit-validerade (FR-1..3).
- 🔴 Detta pass: kör Cluster full + Site + Bundle på VM → tre `output_summary.xlsx` (FR-4..6).
- 🔴 Blockerat tills detta pass klart: steg 6 (`Fall_Back_Logic.py`, F1–F7-väv) — FR-7.
- 📌 Cluster-koden + data ligger kvar i `~/bcg/cluster/` sedan förra körningen (Jens 2026-05-26).
- ⚠️ **Osäkert:** ligger Site (folder 3) + Bundle (folder 5) kod+data på VM:en? **Verifieras som
  första steg** — antas inte (CZ.6: disken består men inget bekräftat uppladdat; LB.1: läs, gissa inte).

**Referensvärden (facit, för rimlighetskoll av VM-output):**
- Cluster steg 5: 43/43 representanter, 618/1276 `Significant?=1`, 4 `New_cluster`-nivåer.
- BCG rå signifikans: 227/1276 (17,8 %) — icke-signifikans på fin nivå är normaltillstånd (`IB.1`).

---

## Mål för denna session

### Primärt: VM-körningspass — producera steg 6:s tre input-filer

**Syfte:** Köra de tre modellfamiljerna på VM:en så att steg 6 (`Fall_Back_Logic.py`) får sin input
(tre `output_summary.xlsx`: cluster, site, bundle). Detta stänger FR-4..6 och låser upp FR-7.

**Leveranser:**
1. `output_summary.xlsx` från **Cluster full** (folder 2) — hämtad hem till repo-strukturen.
2. `output_summary.xlsx` från **Site** (folder 3) — körd som Cluster (`LB.4`: samma pipeline).
3. `output_summary.xlsx` från **Bundle** (folder 5).
4. Kort rimlighetskoll av varje output (negativ elasticitet, trovärdiga band — *inte* full
   rimlighetsgrind, den hör till färsk-data-fasen, `IB.6`).

**Datakälla:** VM-disk `~/bcg/` (Cluster bekräftad; Site/Bundle verifieras steg 1).

---

## Steg (ett i taget, verifiera mellan steg)

> **OBS:** Steg 1 är en VM-VERIFIERING, inte en körning. Anta aldrig vad som ligger på en deallokerad
> disk (CZ.6/LB.1). Vad som följer efter steg 2 avgörs av vad steg 1 visar.

### Steg 0 — Pre-flight (PowerShell, Windows)
```powershell
cd "C:\Projekt\BCG"
```
```powershell
git log --oneline -5
git status
```
Förväntat: senaste commit `85cd33f`, working tree clean.

```powershell
az login --scope https://management.core.windows.net//.default
```
```powershell
az account set --subscription "ev-lz3-ai (SE)"
```
Aktivera PIM Contributor på `ev-openai-swce-rg-test` om utgången (Portal → PIM).

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
Vänta ~1 min efter start före ssh (CZ.6: `Connection refused` direkt = sshd ej vaken, inte fel).

### Steg 1 — Verifiera VM-innehåll (KRITISKT första steg)
```powershell
ssh azureuser@172.18.148.4 "ls -la ~/bcg/; echo '---'; ls -d ~/bcg/*/ 2>/dev/null; echo '---'; du -sh ~/bcg/* 2>/dev/null"
```
Tolka: finns bara `cluster/`, eller även `site/` + `bundle/` (eller motsv.)? Detta avgör steg 2–4.
- **Bara cluster** → Site+Bundle måste laddas upp (steg 2b).
- **Alla tre** → hoppa till körning (steg 3).

### Steg 2a — Kör Cluster full (om koden finns, vilket den ska)
```powershell
ssh azureuser@172.18.148.4 "ls ~/bcg/cluster/code/model.py; ls ~/bcg/cluster/output/ 2>/dev/null"
```
I tmux på VM:en (bash):
```
tmux new -s bcgrun
source ~/bcg/cluster/.venv/bin/activate
cd ~/bcg/cluster/code
python model.py 2>&1 | tee ~/run_log_PC_full.txt
```
Detacha: `Ctrl+B` följt av `D`. Kolla utifrån (PowerShell):
```powershell
ssh azureuser@172.18.148.4 "pgrep -af model.py; tail -3 ~/run_log_PC_full.txt; free -h"
```

### Steg 2b — Ladda upp Site + Bundle (ENDAST om steg 1 visar att de saknas)
> Site-input är tung (~130 MB enligt tidigare not). Verifiera storlek + ev. Blob-blockerare innan
> uppladdning (O1: Blob-roll kräver Owner — om scp inte räcker, flagga). Föredra scp till VM-disk
> (PoC-mönstret, D11) framför Blob tills rollen är löst.
```powershell
scp -r "C:\Projekt\BCG\Pipeline\02. Elasticity\3. Product Site Level Models" azureuser@172.18.148.4:~/bcg/site
```
```powershell
scp -r "C:\Projekt\BCG\Pipeline\02. Elasticity\5. Bundle Clinic Models" azureuser@172.18.148.4:~/bcg/bundle
```
> Efter scp: `chmod -R u+w ~/bcg/site ~/bcg/bundle` på VM:en (CZ.4 — Windows-rättigheter följer med).
> Skapa venv + installera requirements per modell (som Cluster gjordes). Verifiera `sys.executable` (LB.13).

### Steg 3 — Kör Site + Bundle (samma mönster som Cluster, LB.4)
Site och Bundle är strukturellt identiska med Cluster — samma pipeline-filer, samma launcher-ordning
(regular_price → data_prepration → feature_selection → model). Kör var för sig i tmux med tee.

### Steg 4 — Hämta hem de tre output_summary.xlsx
```powershell
scp azureuser@172.18.148.4:~/bcg/cluster/output/model/output_summary.xlsx "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx"
```
(Motsvarande för site + bundle till deras output-mappar.)

### Steg 5 — Deallokera (KRITISKT, CZ.2)
```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" --output tsv
```
→ Ska visa `VM deallocated`.

---

## Standarder särskilt relevanta nu

- **CZ.6** — tmux för run-to-completion; tmux överlever ej deallocate; vänta ~1 min efter start före ssh.
- **CZ.2** — deallokera direkt efter (vanligaste dyra missen). VM ~8–10 kr/h igång.
- **CZ.4** — scp bär Windows-rättigheter → `chmod -R u+w` på egen mapp efter uppladdning.
- **CZ.8 / LB.16** — verifiera output mot FIL (`ls -la`, storlek>0, färsk tidsstämpel), ej loggrad.
- **LB.1** — verifiera VM-innehåll (steg 1) före antagande; läs, gissa inte.
- **LB.13** — verifiera `sys.executable` före varje körning; `cd` byter inte venv.
- **LB.14** — tee + grep strukturella rader (Running/Finished/Shape/Saved/Error); aldrig rådata.
- **E.3/CZ.3** — token dör efter 4 h; VM-körningen påverkas ej (lokala filer). Logga in igen vid behov.

---

## Efter detta pass (förberedelse, ej denna session)

Med de tre `output_summary.xlsx` på plats blir **steg 6** (`Fall_Back_Logic.py`, F1–F7) nästa steg —
DÅ läses `creating_one_df` + F1–F7-vävfunktionerna i detalj (LB.3: ej före input finns). Därefter
färsk-data-fasen: output-rimlighetsgrind + G7-datumparametrisering + FTE Väg 2.

---

## Vid sessionsslut

1. Committa ev. ändrade verktyg/dokumentation och pusha (output_summary.xlsx går INTE in — Excel,
   utestängt av `.gitignore`; det är OK, det är genererat och regenererbart).
2. `git status` — ska vara rent.
3. Bekräfta `VM deallocated`.
4. Uppdatera denna fil: ny SHA + nästa mål (steg 6-replikering).
5. Nya lärdomar → `LESSONS_BCG.md`; nya insikter → `INSIGHTS_BCG.md`; befordra till MASTER_* om generella.
6. Uppdatera playbookens riktningsblock (FR-4..6 → ✅) och README:s roadmap.

---

*Skapad 2026-05-26 vid dokumentstruktur-omtaget. Riktad mot VM-körningspasset (FR-4..6). VM-läge bekräftat
med Jens: Cluster uppe, Site/Bundle verifieras + laddas upp som första steg.*

# NEXT_SESSION — Cluster-maj: rotorsak LÖST, fix kvarstår (vattentät)

**Skapad:** 2026-06-23 (session-slut). **Ersätter:** NEXT_SESSION_cluster_maj_blockerad.md (föråldrad — skrevs före sond 3).
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia). **Författare:** Claude-rådgivare.
**Status:** Cluster-maj blockerad. ROTORSAK BEVISAD (sond 3). Fix kvarstår — kräver ett BESLUT (se §3).

> ⚠️ Denna fil bär den FÄRDIGA diagnosen. Återupptäck den INTE. Tidigare prompter
> (_blockerad.md) bar en delvis felaktig mellanversion (ProductGroupL4Name "saknas/ny" —
> FEL, den finns i båda vägarna). Lita på DENNA fil.

---

## 0. Sessionsstart (KÄRNPRINCIPER §6.1)

```powershell
cd "C:\Projekt\BCG"
git log --oneline -5          # senaste: 5ab3a4e (diagnos-svit). Matchar STATE? annars uppdatera STATE.
git status                    # ska vara rent
git branch --show-current     # main
```
Azure (VM deallokerad igår — startas av runnern vid relaunch):
```powershell
az account show --query name -o tsv                              # MÅSTE: ev-lz3-ai (SE)
az login --scope https://management.core.windows.net//.default  # token dör var 4h (E.3)
```

---

## 1. ROTORSAKEN (bevisad av sond 3 — detta är FAKTA, ej hypotes)

Cluster-maj kraschade 2x i feature_selection (steg 3), `KeyError: 'No_of_Sites'`
på `feature_selection.py:532` (`df[col].astype(config['col_type'][col])`).

**INTE two-pass** (control_file.xlsx finns, giltig — pass 2 kom förbi den).

**Sond 3 (probe_3_dataprep_provenance.py) bevisade: TVÅ prep-vägar med OLIKA scheman.**

| | **BA-vägen** (april-CSV) | **SQL-prep-vägen** (maj-CSV) |
|---|---|---|
| Fil | `Business_Analytics/export_b4b_for_model.py` | `Sweden_Elasticity_Data_Prep_SQL/scripts/01_process.sql` |
| No of Sites | `:195` `"No of Sites"` (MELLANSLAG) | `:306,:325` `AS No_of_Sites` (UNDERSTRECK) |
| TotalNetXVat | `:197` `TotalNetXVat=("SalesExVAT","sum")` SKAPAS | SKAPAS ALDRIG (saknas i maj-CSV) |
| ProductGroupL4Name | `:194` finns | `:85,:147...` finns (FINNS I BÅDA — ej problemet) |

April byggde rent för att april-CSV kom från BA-vägen, vars schema config.yml är
skriven för. Maj-CSV kom från SQL-prep-vägen → annat schema → krasch.

**config.yml förväntar BA-schemat:** `:72` `No of Sites : 'float64'`, `:109` `TotalNetXVat : 'float64'`.
**constants.py:82** `NO_OF_SITES = "No of Sites"` (mellanslag — BA-schemat).
**replicate_dataprep.py:63** har redan alias `{"No of Sites": "No_of_Sites"}` (känner driften).

Två konkreta mismatchar mellan maj-CSV och config/constants:
1. **No_of_Sites** (understreck i maj-CSV) vs **No of Sites** (mellanslag i config+constants). Namn-drift.
2. **TotalNetXVat** finns i config men SAKNAS i maj-CSV (SQL-prep skapar den aldrig). Genuint saknad kolumn.

---

## 2. KÖR SOND 4 FÖRST (enda öppna mätningen — avgör fixens omfång)

Allt annat är mätt. Den enda öppna frågan: **biter den saknade TotalNetXVat
nedströms** (model.py/steg5/Step6)? Sond 4 svarar. VM måste vara uppe.

```powershell
cd "C:\Projekt\BCG\tools\diagnos"
$env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
# VM måste vara igång för sond 4 (ssh). Starta om nödvändigt:
#   az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
py -3.11 probe_4_downstream_impact.py
```
- **Sond 4 = PASS** (TotalNetXVat refereras EJ nedströms) → fixen är liten (§3 väg A).
- **Sond 4 = REVIEW** (TotalNetXVat läses i model.py/Step6) → TotalNetXVat måste TILLBAKA i maj-CSV (§3 väg B).

(Sond 1+2 kan köras för att bekräfta, men deras svar är redan känt ur sond 3 ovan.)

---

## 3. BESLUTET som måste fattas (detta är kärnan — inte bara en config-lapp)

Frågan är ARKITEKTONISK: **vilken prep-väg ska vara kanonisk framåt?**

- **BA-vägen** (`export_b4b_for_model.py`) matade april. Schema: `No of Sites` + TotalNetXVat.
- **SQL-prep-vägen** (`01_process.sql`) matade maj. Schema: `No_of_Sites`, ingen TotalNetXVat.
- PROJEKTMÅLET (README/ROADMAP) är DW-native via SQL-prep → SQL-prep BÖR vara framtiden.

### Väg A — gör koden tolerant mot SQL-prep-schemat (om sond 4 = PASS)
Snabbast, additivt. SQL-prep blir kanonisk; config/constants anpassas till dess namn.
```yaml
# config.yml col_type (~rad 57+) — LÄGG TILL understreck-varianten (behåll mellanslag):
    No_of_Sites : 'float64'
```
```python
# constants.py:82 — gör tolerant ELLER byt till understreck om SQL-prep är kanonisk.
# Säkrast additivt: NO_OF_SITES_VARIANTS = ["No of Sites", "No_of_Sites"] och prova båda.
```
TotalNetXVat: om sond 4 = PASS behövs den inte → ta bort `TotalNetXVat` ur config col_type
ELLER lämna (ofarlig: loopen rör bara df:s faktiska kolumner, saknad nyckel för
icke-existerande kolumn smäller inte). VERIFIERA detta innan relaunch.

### Väg B — lägg tillbaka TotalNetXVat i SQL-prep (om sond 4 = REVIEW)
Om nedströms LÄSER TotalNetXVat måste SQL-prep skapa den. Lägg till i `01_process.sql`
(samma logik som BA-vägen `:197`: `SUM(SalesExVAT)` per grupp), regenerera maj-cluster-CSV
lokalt, scp om till VM. PLUS namn-fixen ovan. Större jobb — men gör SQL-prep schema-komplett.

### Rekommendation
Kör sond 4. PASS → väg A (snabb, SQL-prep kanonisk för cluster). REVIEW → väg B.
Oavsett: fixa i REPOT (config.yml + ev. 01_process.sql) → committa → tillämpa VM
(annars dator-unikt, mot survival-tesen).

---

## 4. Tillämpa, relauncha, validera

```powershell
# 1. Fixa i repot (config.yml ev. + constants.py ev. + 01_process.sql) via skript, UTF-8 utan BOM
cd "C:\Projekt\BCG"
git add <fixade-filer>
git commit -m "config/SQL-prep: hantera No_of_Sites (understreck) + TotalNetXVat-schema (cluster-maj, two-prep-väg-glapp)"
git push origin main

# 2. Tillämpa config (+ ev. regenererad CSV) på VM
#    Om VÄG B: regenerera maj-cluster-CSV lokalt FÖRST (SQL-prep med TotalNetXVat), scp till VM:
#      scp "<maj-CSV>" azureuser@172.18.148.4:'~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv'
#    Config till VM:
scp "<lokal config.yml>" azureuser@172.18.148.4:'~/bcg/cluster/code/src/config.yml'
ssh azureuser@172.18.148.4 'grep -n No_of_Sites ~/bcg/cluster/code/src/config.yml'   # verifiera

# 3. Relauncha cluster (tee + filtrera — Jens klistrar ej rådata)
cd "C:\Projekt\BCG\orchestration"
$env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
py -3.11 runners\run_cluster_model.py --keep-vm 2>&1 |
    Tee-Object "$env:TEMP\cluster_maj_v3.log" |
    Select-String -Pattern 'Running|Finished|Total|Models built|launch|poll|fetch|upload|Blob|finalize|SUCCESS|Error|deallocate'

# KRITISK SIGNAL: passerar feature_selection 5-min UTAN Error -> fixen höll.
# Förväntat: ~49-55 min -> "Total Models built: 4180" -> Steg 5 kraschar (väntat, xlwings LB.44).

# 4. rationality på maj-cluster (maj-fönstret får kvitto) + verifiera cluster grön i appen.

# 5. DEALLOKERA VM
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --no-wait
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[1].displayStatus" -o tsv
```

---

## 5. LÄGE vid session-slut 2026-06-23 (sant nu)

- Maj-cluster-CSV på VM: `~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv`
  (617651 rader, SQL-prep-schema: No_of_Sites understreck, INGEN TotalNetXVat).
- April-CSV arkiverad på VM: `.pre_maj_<stamp>` (BA-schema: No of Sites + TotalNetXVat).
- control_file.xlsx finns (377K, 17/6, giltig).
- **Site-maj VALIDERAD** (rationality 3 PASS/6 REVIEW strukturella, 6604 KEY).
- **Tre fönster i appen:** facit (grön), april (motor grön + efter pending, körtider 49/68/1 min),
  maj (site grön, cluster SPÖKE-"running", rest pending).
- VM DEALLOKERAD (bekräftat). All kod pushad (5 commits, senaste 5ab3a4e).

**SPÖKE:** cluster_model fast "running" i maj-statusfilen (pollning mot död körning).
Patchas när relaunch lyckas (finalize), ELLER manuellt via tools/fix_maj_timing.py-mönster.

**Diagnos-svit:** tools/diagnos/ (probe_1..4 + run_cluster_maj_diagnosis.py). Sond 3 = lokal,
gav rotorsaken. Sond 1/2/4 = VM. Kör hela: `py -3.11 run_cluster_maj_diagnosis.py`.

---

## 6. Ej blockerande (ta vid tillfälle)

- **Fäst dagens tekniska lärdomar i LESSONS_BCG** (gör TIDIGT nästa session, färskt):
  scp-trailing-slash escapar citattecken; facit-CSV latin-1 / SQL-prep-CSV UTF-8;
  spöke = tunnel-tapp/krasch före finalize (sätt finished_at från KÄND körtid, ej "nu");
  TWO-PREP-VÄG-GLAPPET (BA-export vs SQL-prep, olika scheman — denna sessions huvudlärdom).
- **RUNNER-BUGGAR** (eget pass): (a) two-pass-relaunch ej automatisk; (b) krasch/observationsförlust
  → ingen finalize → spöke. Runnern bör auto-relaucha feature_selection pass 1 + finalize i krasch-väg.
- **BLOB-struktur:** förena BLOB_MALSTRUKTUR.md (familj/fönster) + BLOB_STRUCTURE_DESIGN_FD28.md
  (BCG-prefix) innan migrering. Eget pass.
- **LEVERANS 2** (efter Blob-omstrukt): kvitton per fönster + appens 5 kvitto-funktioner per run_id
  + periodmedvetna KPI:er (story_config "now" hårdkodad april/facit).
- **LESSONS-delning + NEXT_SESSION-städning:** 7 NEXT_SESSION-filer finns (se §7) — rensa till EN.

---

## 7. STÄDA NEXT_SESSION-RÖRAN (gör detta nästa session)

7 NEXT_SESSION-filer existerar 2026-06-23 — förvirrande. Behåll EN sanning:
- Repot: `NEXT_SESSION.md` (15/6, gammal allmän kö), `_blockerad.md` (FÖRÅLDRAD — radera),
  denna fil, `NEXT_SESSION_TEMPLATE.md` (mall — behåll).
- Downloads: 4 till (dubbletter/gamla — rensa).
PLAN: gör DENNA fil till `NEXT_SESSION.md` (skriv över den gamla), radera _blockerad.md
och Downloads-dubbletterna. En NEXT_SESSION.md + en TEMPLATE = sanning.

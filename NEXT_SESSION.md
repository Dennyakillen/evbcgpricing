# NEXT_SESSION — Cluster-maj: rotorsak LÖST, fix kvarstår (vattentät)

**Skapad:** 2026-06-23 (session-slut). **Uppdaterad:** 2026-06-26 (valideringslager-sidospår invävt §5.5, lärdomar fästa).
**Ersätter:** NEXT_SESSION_cluster_maj_blockerad.md (föråldrad — skrevs före sond 3).
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia). **Författare:** Claude-rådgivare.
**Status:** Cluster-maj blockerad. ROTORSAK BEVISAD (sond 3). Fix kvarstår — kräver ett BESLUT (se §3).
**Sidospår 2026-06-26:** valideringslager byggt + pushat (se §5.5) — påverkar INTE cluster-maj-blockeringen.

> ⚠️ Denna fil bär den FÄRDIGA diagnosen. Återupptäck den INTE. Tidigare prompter
> (_blockerad.md) bar en delvis felaktig mellanversion (ProductGroupL4Name "saknas/ny" —
> FEL, den finns i båda vägarna). Lita på DENNA fil.
> **Primärt mål nästa session = cluster-maj (§2-§4).** §5.5 är avslutat sidospår (kontext, ej att göra).

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

## 5.5 SIDOSPÅR 2026-06-26 — valideringslager runt motorn (AVSLUTAT, pushat)

> Detta är KONTEXT, inte en att-göra-lista. Ett parallellt spår som byggdes klart och
> pushades samma session. Påverkar INTE cluster-maj-blockeringen. Läs för att veta vad som
> nu FINNS att använda — flera av dessa verktyg är direkt nyttiga för cluster-maj-arbetet (se "Hur det hjälper").

### Vad vi gjorde
Byggde, körde och pushade ett **additivt valideringslager** runt den orörda BCG-motorn — "limmet"
som bevisar att hela röret (FÖRE→MOTOR→EFTER) håller på växande data utan tyst tapp tvärs familjer,
och som synliggör vävens avsiktliga filter. BCG-kärnan orörd (additivt only). Pushat i två commits
(`ad446e4` verktyg + `57b28ca` dok), 7da30b9..57b28ca.

Sju verktyg i `verify_tool/`:
- **pipeline_contracts.py** — boundary-kontrakt för Step 6:s inputs (form/volym/invariant, blockerande).
- **prefilter_unpriced.py** — gör icke-prissatt bortfall (Natrium Catalyst) explicit före väven.
- **window_coherence.py** — tvärs-familje-grind: alla MOTOR-familjer klara+färska mot samma fönster
  före EFTER. Offline default, `--via-blob` striktare, AZ.7-tolerant (token-död degraderar mjukt).
- **dry_run_full_pipeline.py** — strukturell dry-run tvärs hela röret (24 OK/0 FAIL).
- **run_smoke_facit.py** — end-to-end rök-test mot frozen facit, HELT OFFLINE.
- **conservation.py** — population per skarv (skarv 1 parquet-tillväxt; skarv 2-3 ramverk).
- **valve_map.py** — ventilkarta: var vävens filter sitter, hur mycket de släpper, vad som rann ut.

Frozen-facit blessad som referens: **108 979 rader / 15 128 keys / median −0.4968**
(`verify_tool/frozen_facit_reference.json`, versionshanterad — drift mot den är spårbar).

### Vad mätningen avslöjade (verkliga fynd)
- **Step 6-vävens fyra avsiktliga ventiler uppmätta** (valve_map, LB.83): V1 Fee (släpper 5),
  V2 service-join, V3 signifikans (släpper **77.4%** av cluster-modellerna — PVALUE 2166/RSQ 1428/
  tecken 1100/orimlig 10, överlappande), V4 min-sites. V1/V3 EXAKT; V2/V4 APPROX (ej kalibrerade).
- **Natrium Catalyst (LB.84):** df_all_product bär ~20 icke-prissatta poster utan ItemCode som
  faller ur väven tyst via inner join (instans av KÄRN P.3). Nu explicit via prefilter_unpriced.
- **Schema-drift (LB.82):** parqueten bär DW-namn (`ID_Item`), inte nedströms (`ItemCode`).
  *Detta är samma klass som cluster-majs two-prep-väg-glapp (§1) — namn-drift mellan led.*

### Vad vi INTE gjorde (öppet, ej brådskande — se §6)
- V2/V4 i valve_map är APPROXIMATIONER, ej kalibrerade mot vävens faktiska tal.
- conservation.py skarv 1 har samma schema-bugg som LB.82 (frågar `ItemCode`, ska vara `ID_Item`).
- Verktygen är EJ inkopplade i run_step6/run_after preflight (additivt, gjort när tid finns).
- window_coherence `--via-blob` oprövad mot live token.

### Hur det hjälper framåt (även cluster-maj DIREKT)
- **dry_run_full_pipeline.py + run_smoke_facit.py** = kör FÖRE varje varm cluster-maj-relaunch.
  Fångar sökvägs-/fönster-/schema-glapp KALLT på sekunder i stället för i minut 50 av en VM-körning.
- **valve_map.py V3** ger dig nu en BASLINJE för hur mycket väven normalt avlättar — den dag en
  ventils utflöde avviker på oförändrad data vet du var röret börjat läcka (felsöknings-startpunkt).
- **Mönstret (LB.85 / KÄRN-kandidat):** two-prep-väg-glappet (§1) och schema-drift (LB.82) är SAMMA
  bug-klass. Principen "härled, deklarera inte två gånger" + "validatorn minst lika feltålig som
  systemet" gäller cluster-majs fix: en tolerant schema-hantering (väg A) är att HÄRLEDA kolumnnamn,
  inte deklarera dem på två ställen som glider isär. Återanvänd `PROMPT_hitta_validera_cementera.md`.

### Lärdomar att fästa (STATUS 2026-06-26)
- **LESSONS_BCG.md** (BCG-repot): LB.82-85 inklistrade (CP1252). Råmaterial: docs/INKLISTRING_FINAL.md.
- **KÄRNPRINCIPER.md** (C:\Projekt\masters — EGET repo): principen "validatorn minst lika feltålig
  som systemet" inklistrad (UTF-8). Övriga föreslagna AVVISADE som instanser av P.1/P.3 (§6.6-prövat).
- Om någon av ovan EJ är klar när du läser detta: docs/INKLISTRING_FINAL.md har exakt text + kodning.

### Masters-städning kvar (lågprioriterat, ej blockerande)
- `Personalrabatt_html.txt` (107 KB) i masters — troligen ej universell, avgör hemvist/arkivera.
- `PROMPT_arkitektur_mognadsanalys.md` i masters — BCG-specifik + mojibake-skadad → laga kodning,
  flytta till BCG\docs\. (Är projektspecifik, hör ej i masters per README-grinden.)
- `MASTER_AZURE.md` + `MASTER_AZURE_COMPUTE.md` båda i masters — avgör om de ska slås ihop (versionsskew).

---

## 5.6 SIDOSPÅR 2026-06-26 (kväll) — kunskapsbas-räddning + kompass + repo-städning (AVSLUTAT)

> Fortsättning samma kväll som §5.5. Allt nedan KLART och pushat om ej annat anges.

### Vad som gjordes och är KLART (pushat)
- **LESSONS_BCG dubbelkodnings-räddning:** filen var dubbelkodad (1942 mojibake-sekvenser
  `C3 83 C2 A4`, UTF-8→CP1252→UTF-8) — orsak: VS Code öppnade UTF-8-fil med fel kodning + auto-save.
  Lagad byte-rent (läs UTF-8 → CP1252-bytes → WriteAllBytes). 90517→84961 bytes, ren. Committad SEPARAT
  före lärdomar. **LB.86** fäst (editorn + PS-mätinstrument båda hot mot filintegritet).
- **LB.82-86 fästa** i LESSONS_BCG (DW-namn, vävens fyra ventiler, Natrium Catalyst, valid>lager, kodning).
- **KÄRNPRINCIPER P.6-P.13 + kompass** i masters (nu Master-Bibliotek): P.6 validator-feltålig,
  P.7 grain, P.8 schema-on-write, P.9 atomära skrivningar (proportionerat), P.10 idempotens,
  P.11 tests-vs-validation, P.12 property-based, P.13 cross-row-invarianter. + tio-signalers kompass överst.
- **io_safe.py + idempotens_audit.py** committade i BCG. Audit mätte 164 skrivningar, ~3-4 relevanta
  (run_step6, build_r12, fallback_blend) — resten BCG-kärna (rör ej) el kvitton (lågprio).
- **docs/ sorterad:** rotfiler → sessions/ prompts/ knowledge/ (git mv, historik bevarad).
  UBUNTU_AZURE_VM (identisk dubblett) + COMMIT_GUIDE + TILLAGG_governing_docs borttagna. Downloads rensat.
- **Repo masters → Master-Bibliotek** omdöpt: GitHub-namn + lokal remote + lokal mapp, alla verifierade.

### KVAR — parkerat medvetet (kräver pigg + filåtkomst, gör i Claude Code)
- **KRITISK — MASTER_AZURE.md merge:** BCG-kopian (`docs/ops/`, 512 rader) är RIKARE än masters-kopian
  (327 rader) med 386 unika rader (konton, Phase Z-resurser) MEN dubbelkodad. "masters trumfar" gällde
  UBUNTU (identisk) men EJ denna (BCG rikare) — mät delta, lita ej på samma namn. Uppgift: (1) laga
  BCG-kopians kodning först, (2) avgör universellt-vs-projektspecifikt rad-för-rad, (3) smält universellt
  → Master-Bibliotek (ren mot ren — smält ALDRIG dubbelkodad text in i ren fil), behåll projektspecifikt
  i BCG. (4) verifiera båda byte-rent.
- **BRA — BCG\docs UTF-8-konvertering:** TECHNICAL_PREREQUISITES, KRAVSPEC_IT, README_VALIDERING m.fl. är
  CP1252 (vissa dubbelkodade). Master-Bibliotek är ren UTF-8. Konvertera hela BCG-doc-sviten → UTF-8 så
  CP1252-fällan försvinner (roten till kvällens korruptioner, LB.86).
- **KRITISK — referenser efter repo-namnbyte:** masters→Master-Bibliotek på 3 tekniska nivåer, men
  DOKUMENTATIONEN släpar (fjärde kartan). Sök/ersätt i ALLA filer: `C:\Projekt\masters` →
  `C:\Projekt\Master-Bibliotek` OCH `Dennyakillen/masters` → `Dennyakillen/Master-Bibliotek`
  (STATE.md, README:er, governing-docs, ev skript). Gör i Claude Code (söker hela trädet).

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

**Valideringslager (sidospår §5.5/§5.6 — lägst risk först, ej brådskande):**
- [KLART 2026-06-26: LB.82-86 fästa, KÄRN P.6-P.13 i Master-Bibliotek, io_safe+audit committade.]
- Fix conservation.py skarv 1: byt `ItemCode` → `ID_Item` i DuckDB-frågan (LB.82). En rad. Trivialt. (KVAR)
- Kalibrera valve_map V2/V4: print-satser finns i valve_map.py-huvudet → klistra i Fall_Back_Logic.py
  temporärt, kör väven, jämför, uppgradera APPROX→EXAKT. Öppen fråga: V4 99.6% sant eller approx-fel?
- Koppla in i preflight (additivt): run_step6 (prefilter→contracts), run_after (window_coherence).
- Verifiera window_coherence `--via-blob` mot färsk token (mjuk degradering).
- Fäst LB.82-85 (LESSONS_BCG) + KÄRN-kandidat (masters, eget repo). CP1252. Råmaterial: docs/TILLAGG_governing_docs.md.

---

## 7. STÄDA NEXT_SESSION-RÖRAN (gör detta nästa session)

7 NEXT_SESSION-filer existerar 2026-06-23 — förvirrande. Behåll EN sanning:
- Repot: `NEXT_SESSION.md` (15/6, gammal allmän kö), `_blockerad.md` (FÖRÅLDRAD — radera),
  denna fil, `NEXT_SESSION_TEMPLATE.md` (mall — behåll).
- Downloads: 4 till (dubbletter/gamla — rensa).
PLAN: gör DENNA fil till `NEXT_SESSION.md` (skriv över den gamla), radera _blockerad.md
och Downloads-dubbletterna. En NEXT_SESSION.md + en TEMPLATE = sanning.

**Valideringslager-dokument (sidospår §5.5 — INTE NEXT_SESSION-filer, ska EJ raderas):**
docs/ har nu SESSION_2026-06-26, README_VALIDERING, ARKITEKTUR_MOGNADSANALYS, PROMPT_hitta_validera_
cementera, COMMIT_GUIDE, TILLAGG_governing_docs. De fyra första är varaktig dok (behåll). COMMIT_GUIDE
+ TILLAGG är arbetsmaterial — kan arkiveras/raderas NÄR lärdomarna är inklistrade (§5.5) och commit klar.

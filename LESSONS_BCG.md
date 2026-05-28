# LESSONS_BCG — Tekniska lärdomar, BCG Pricing-replikering

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG` (detta repo). Helt skild från Business_Analytics `PROJECT_LESSONS.md`.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Senast uppdaterad:** 2026-05-28

---

## Vad detta dokument är (och inte är)

`LESSONS_BCG.md` är den **kumulativa, numrerade listan över tekniska lärdomar** specifika för
BCG-replikeringen — pipeline-mekanik, plattformsfällor, replikeringsmetod, körningsdisciplin.
Varje lärdom har ett stabilt `LB.N`-ID så att README, playbook och NEXT_SESSION kan referera den
utan att upprepa innehållet.

**Detta är inte:**
- **Affärs-/domäninsikter** om BCG:s modell eller Evidensias data → de bor i `INSIGHTS_BCG.md` (`IB.N`).
- **Universella principer** (gäller alla projekt) → de bor i `KÄRNPRINCIPER.md`.
- **Stack-lärdomar** som gäller oavsett projekt (token var 4:e timme, UTF-16-filer, compute får aldrig
  idla) → de bor i `MASTER_PYTHON.md` / `MASTER_AZURE.md` / `MASTER_AZURE_COMPUTE.md`.

**Befordringsregeln (viktig):** En BCG-lärdom *föds* här. Visar den sig vara **generell** (sann för fler
projekt än BCG) **befordras** den till rätt MASTER_*.md, och raden här ersätts av en pekare dit. Det
håller den projektspecifika listan ren och master-filerna auktoritativa. Kolumnen "Befordran" nedan
markerar kandidater.

**Format:** Varje lärdom följer KÄRNPRINCIPER §7: Symptom → Rotorsak → Regel.

---

## Snabbindex

| ID | Rubrik | Kategori | Befordran |
|---|---|---|---|
| LB.1 | Läs källan/facit FÖRE hypotesdrivet bygge (A.9 skärpt) | Replikeringsmetod | Nej — kärna i detta projekt |
| LB.2 | Kör VÅR kod på KONSULTENS input — billig logik-grind | Replikeringsmetod | Kandidat → KÄRNPRINCIPER |
| LB.3 | Bygg ALDRIG mot input som inte finns | Replikeringsmetod | Kandidat → KÄRNPRINCIPER |
| LB.4 | Läs KONSUMENTEN för kontraktet, inte hela producenten | Replikeringsmetod | Kandidat → KÄRNPRINCIPER |
| LB.5 | Elasticitet svag ≠ pipeline trasig | Pipeline-mekanik | Nej — domännära |
| LB.6 | feature_selection FÖRE model (pipeline-ordning) | Pipeline-mekanik | Nej |
| LB.7 | Control-filens feature-kolumner är aktiveringsflaggor (VALUE==1) | Pipeline-mekanik | Nej |
| LB.8 | VIF är efterdiagnostik, inte elasticitet | Pipeline-mekanik | Nej |
| LB.9 | Smoke-KEY väljs på pris-CV, inte veckoantal | Pipeline-mekanik | Nej |
| LB.10 | Config-encoding: VS Code, aldrig PS `Set-Content -Encoding UTF8` | Encoding/plattform | Kandidat → MASTER_PYTHON |
| LB.11 | Tvinga stdout UTF-8 i script som dumpar källkod | Encoding/plattform | Kandidat → MASTER_PYTHON |
| LB.12 | Hårdkodade Windows-sökvägar dödar Linux-körning | Encoding/plattform | ✅ Redan i MASTER_AZURE_COMPUTE (CZ.5) — pekare |
| LB.13 | venv-disciplin: verifiera `sys.executable` före körning | Disciplin | Kandidat → MASTER_PYTHON |
| LB.14 | Tee + strukturell filtrering, aldrig rådata | Disciplin | Kandidat → KÄRNPRINCIPER |
| LB.15 | Ett kartläggningsscript > tio fil-frågor | Disciplin | Kandidat → KÄRNPRINCIPER |
| LB.16 | Verifiera utfall mot FIL, inte mot loggrad | Disciplin | ✅ Redan i MASTER_AZURE_COMPUTE (CZ.8) — pekare |
| LB.17 | Rensa output: radera filer, behåll mappstruktur | Encoding/plattform | Kandidat → MASTER_AZURE_COMPUTE |
| LB.18 | control_file.xlsx är INPUT, inte bara output | Pipeline-mekanik | Nej |
| LB.19 | Ny modellfamilj bär ALLA ofixade Windows/maskin-värden | Replikeringsmetod | Kandidat → MASTER_AZURE_COMPUTE |
| LB.20 | Steg 5 (xlwings) icke-körbart på Linux men onödigt | Pipeline-mekanik | Nej |
| LB.21 | .ps1 vägras av execution policy (som AppLocker) | Körningsdisciplin | Kandidat → MASTER_PYTHON |
| LB.22 | Kartesisk self-join: merge på fullt rad-grain | Replikeringsmetod | Kandidat → KÄRNPRINCIPER |
| LB.23 | xlwings valfri för logikvalidering (try/except) | Pipeline-mekanik | Nej |
| LB.24 | Validera mot fryst original, aldrig arbetskopian | Replikeringsmetod | Nej — kärna |
| LB.25 | Misstänk korr 1,0 tills källoberoende bekräftat | Replikeringsmetod | Kandidat → KÄRNPRINCIPER |
| LB.26 | verify-wrappers ärver sys.executable → py -3.11 | Körningsdisciplin | Nej |
| LB.27 | Windows Store python3.13-alias är interpreter-fälla | Körningsdisciplin | Kandidat → MASTER_PYTHON |
| LB.28 | Hel-fil-kopia mellan modeller farligt — mät hash | Replikeringsmetod | Kandidat → KÄRNPRINCIPER |

---

## Replikeringsmetod

### LB.1 — Läs källan/facit FÖRE hypotesdrivet bygge (A.9 skärpt)
**Symptom:** Byggde hel FTE-pipeline + två smoke-omgångar på hypotesen att FTE var den saknade biten
för signifikans. Bad upprepat användaren välja designval (hur Service hanteras, vilken fil blenden äter)
istället för att läsa `model.py` / `data_prep_after_model_output.py` som redan definierade svaret.
**Rotorsak:** Otålighet — ville bygga/fråga innan hela kedjan lästs. BCG:s `Model_output` + assumptions-
flik visade på 30 sekunder att BCG också är icke-signifikant på OVR0001 och att bara 18 % är rått
signifikanta. Att läsa facit FÖRST hade omdirigerat från "jaga signifikans" till "förstå fallback".
**Regel:** När en fil-/kolumn-/sekvensfråga uppstår OCH källkoden eller facit finns — läs källan FÖRST.
Dashboardens output ÄR källa (= facit), precis som koden. `ask_user_input` på designval som koden redan
avgjort är förtäckt gissning. Default: begär källfil / kör läs-script. Användarens "se instruktionerna,
kolla facit" var rätt varje gång.

### LB.2 — Kör VÅR kod på KONSULTENS input för billig logik-grind
**Symptom:** Frestelse att vänta på en full VM-körning för att facit-validera steg 5 (fallback).
**Rotorsak:** Förväxlade "kör på vår data" med "räknar rätt" — två olika frågor. Logik-trohet kräver
inte vår egen körning.
**Regel:** Bevisa logik-trohet billigast genom att köra repliken på konsultens EGEN input och matcha
deras output bit-för-bit (kräver ingen ny tung körning). Samma princip som golden reference. "Kör på vår
data" är en SEPARAT, senare fråga (kräver VM). *(Bevisat: `fallback_blend.py` på BCG:s egen
`output_summary.xlsx` → 43/43 representanter identiska.)*

### LB.3 — Bygg ALDRIG mot input som inte finns
**Symptom:** Frestelse att läsa/bygga steg 6:s F1–F7-väv innan Site/Bundle-modellerna körts. Samma
mönster som FTE-pipelinen (byggd på hypotes innan facit lästs).
**Rotorsak:** Ett steg vars input inte existerar ännu *känns* som nästa steg men är i själva verket
blockerat.
**Regel:** Ett steg vars input inte finns är inte "nästa steg" — det är blockerat. Identifiera
blockeraren (här: tre oskörda modeller → tre saknade `output_summary.xlsx`) och kör DEN först.
Detaljläsning av det blockerade steget väntar tills input finns. *(2026-05-26: blockeraren upplöst —
alla tre `output_summary.xlsx` finns nu. Steg 6 kan läsas i detalj.)*

### LB.4 — Läs KONSUMENTEN för kontraktet, inte hela producenten
**Symptom:** Frestelse att läsa Site/Bundle-pipelinekoden rad för rad för att veta vad den måste leverera.
**Rotorsak:** Site/Bundle är samma beprövade pipeline som Cluster — låg risk för gömd nyhet. Att läsa
producenten i sin helhet var överarbete.
**Regel:** För att veta vad ett uppströmssteg måste LEVERERA, läs nedströmssteget (konsumenten) som
definierar kontraktet. `Fall_Back_Logic.py`:s `__main__` avslöjade att Site/Bundle bara behöver producera
`output_summary.xlsx` i Cluster-format — utan att läsa deras pipeline alls. *(2026-05-26 bekräftat:
Site/Bundle var strukturellt identiska med Cluster — samma åtta `.py`-filer, samma launcher-kedja.
Endast plattforms-/resursvärden skilde, se LB.19.)*

---

## Pipeline-mekanik

### LB.5 — Elasticitet svag ≠ pipeline trasig
**Symptom:** 0 signifikanta elasticiteter på smoke-grupper tolkades först som ett fel i pipelinen.
**Rotorsak:** OVR0001 ("Other sales, store only") är en oelastisk samlingskod; BCG fick samma svaga tal.
Rå signifikans är 18 % även hos BCG. Fallback (omklustring till representant) är hur de når 48 %.
**Regel:** Bedöm egna elasticiteter mot BCG:s output PÅ SAMMA KOD, inte mot en absolut "borde vara
signifikant"-förväntan. Icke-signifikans på fin nivå är normaltillstånd; fallback hanterar det.
*(Se IB.1 för domäninsikten bakom. 2026-05-26 bekräftat på full körning: Cluster 18,0 % rått signifikant
— praktiskt taget identiskt med BCG:s 17,8 %.)*

### LB.6 — feature_selection FÖRE model (pipeline-ordning)
**Symptom:** Svaga elasticiteter med ett fast 2-feature-set.
**Rotorsak:** Körde `model.py` direkt utan `feature_selection`. BCG:s control-fil visar per-grupp-features
(olika per grupp), inte ett globalt set.
**Regel:** Replikera ordningen: `feature_selection` (skriver control-filen med per-grupp-features) →
`model` läser den. Körordning per launcher: regular_price → data_prepration → feature_selection → model
→ data_prep_after_model_output. *(2026-05-26: `launcher.py` orkestrerar exakt denna kedja via
`subprocess.run(check=True)`, stannar på första fel.)*

### LB.7 — Control-filens feature-kolumner är aktiveringsflaggor (VALUE==1)
**Symptom:** `model_summary` VARIABLE = bara CONST; intercept-only-modell; VIF-krasch.
**Rotorsak:** Smoke-control satte features till NaN. `utils.py` (rad ~278) väljer features där VALUE==1;
NaN ≠ 1 → tom ind_var-lista.
**Regel:** Control-filen BÄR feature_selection-outputen. Features = 1 för de som ska användas. OBS:
`cols_needed` tvingas in av koden oavsett control-fil (`feature_selection.py` rad ~310:
`features = cols_needed + list(subset)`).

### LB.8 — VIF är efterdiagnostik, inte elasticitet
**Symptom:** `model.py` kraschar i VIF ("zero-size array") trots korrekt OLS.
**Rotorsak:** `utils.py` återanvänder `X_temp` (params-skalad) för baseline → VIF körs på en singulär
matris på vår data.
**Regel:** Elasticiteten beräknas i `df_coef` FÖRE VIF. Skydda VIF-steget (try/except, NaN på fel) så
körningen lever. Verbatim BCG-kod får kirurgisk PoC-fix — markerad + backup
(`utils_BCG_verbatim.py.bak`). Loggas i playbookens §9 mot konsult. *(2026-05-26: samma backup-disciplin
tillämpad på Site/Bundle plattformsfixar — `.bak` före varje sed-ändring av verbatim-kod.)*

### LB.9 — Smoke-KEY väljs på pris-CV, inte veckoantal
**Symptom:** Veckoantal-urval gav prisstabila serier (CV 0,0004) → absurd +15,0 elasticitet.
**Rotorsak:** Elasticitet kräver prisVARIATION, inte historik-längd. En kod såld 156 veckor till samma
pris är värdelös för elasticitet.
**Regel:** Rökstest-urval = högst pris-CV bland full-historik-grupper. Veckoantal är fel optimeringsmål.
*(2026-05-26 sett i full körning: rå-elasticitetskolumnen har extrema svansvärden (Cluster min −820 /
max +64, Site min −232 / max +1204) just från prisstabila grupper — kapas/hanteras nedströms av
`get_adjusted_elasticity` [-5,0] + fallback. Bundle, med naturlig prisvariation i varukorgar, saknar
dessa extremer (min −1,33 / max +1,21) — renaste outputen.)*

---

## Encoding & plattform

### LB.10 — Config-encoding: VS Code, aldrig PS `Set-Content -Encoding UTF8`
**Symptom:** `config.yml` kraschar PyYAML ("mapping values not allowed", line 2) efter PowerShell-redigering.
**Rotorsak:** PowerShell 5.1 `Set-Content -Encoding UTF8` skriver UTF-8 BOM (EF BB BF); PyYAML tål ej
ledande BOM.
**Regel:** Redigera YAML/config i VS Code (bevarar encoding). Om BOM ändå smyger in: strippa (läs bytes,
ta bort EF BB BF) — `fix_config_encoding.py` finns för detta. *(Kandidat för befordran till MASTER_PYTHON
— gäller all PS-redigering av config.)*

### LB.11 — Tvinga stdout UTF-8 i script som dumpar källkod
**Symptom:** `map_bcg_source.py` dog på `UnicodeEncodeError '\u2192'` (pil i docstring) i PS 5.1.
**Rotorsak:** Default Windows-konsolencoder = cp1252; kan inte encoda Unicode i BCG-källan (pilar, å/ä/ö).
**Regel:** Script som skriver godtycklig källkod till stdout ska ha
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` överst + per-rad ascii-fallback i `log()`.
PS-sidan: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` före körning.

### LB.12 — Hårdkodade Windows-sökvägar dödar Linux-körning
**Status:** ✅ Befordrad — bor i `MASTER_AZURE_COMPUTE.md` som **CZ.5**. Behållen här som pekare.
**Kort:** `C:\ray_spill` (feature_selection.py rad 43) → `/tmp/ray_spill` på Linux (D13). Sök
`Select-String "C:\\"` / `grep 'C:'` före Linux-körning; skapa output-mappar med `mkdir -p` i förväg
(inkl. de med mellanslag). Plattformsanpassning, ej logikändring. *(2026-05-26: LB.19 skärper detta —
sökvägar kan vara `.\code\...` relativa Windows-sökvägar som EJ fångas av en `C:`-grep.)*

---

## Körningsdisciplin

### LB.13 — venv-disciplin: verifiera `sys.executable` före körning
**Symptom:** Pipelinekörning mot fel paketuppsättning.
**Rotorsak:** `cd` byter inte venv. Pipeline-venv och DW-script-venv är skilda. Vidare: en NY tmux-session
startar ett nytt skal → venv-aktiveringen följer INTE med, måste göras om inne i tmux.
**Regel:** Verifiera ALLTID `sys.executable` FÖRE pipelinekörning. Pipeline-venv:
`~/bcg/cluster/.venv` (3.11.9) — återanvänds för Site/Bundle (samma requirements, bevisat). Systemets
`python3` är 3.10 och saknar paketen → aktivera alltid venv (`source ~/bcg/cluster/.venv/bin/activate`),
verifiera `(cluster)` i prompten. Ge full aktiveringssökväg överst i varje körblock (Jens uttryckliga
önskan). *(Kandidat → MASTER_PYTHON.)*

### LB.14 — Tee + strukturell filtrering, aldrig rådata
**Symptom:** Risk att paste:a rådatarader tillbaka och bränna kontext.
**Rotorsak:** Pipeline-validering genererar mycket output; bara strukturella rader bär signal.
**Regel:** Tee:a all körning till logg och filtrera strukturella rader: PowerShell `Select-String`,
bash `grep` på `Running` / `Finished` / `Shape` / `Unique` / `KEY` / `(N,N)` / `Saved` / `Error` /
`Traceback`. Paste aldrig rådata. *(2026-05-26: för feature_selection är `ls automl/*.xlsx | wc -l`
[antal körda grupper] det pålitligaste progress-måttet — loggen buffras och kan se "stilla" ut medan
Ray mal. Process (`pgrep`) + automl-räknare > loggrad.) (Kandidat → KÄRNPRINCIPER.)*

### LB.15 — Ett kartläggningsscript > tio fil-frågor
**Symptom:** Bad om "en fil till" upprepade gånger ur den stora BCG-foldern; varje runda kostade.
**Rotorsak:** Behövde flera filer ur en >50 000-fils-folder utan att veta vilka i förväg.
**Regel:** När flera filer ur en stor folder behövs, bygg ETT read-only script (`map_bcg_source.py`) som
dumpar all kod i sin helhet + spreadsheet-STRUKTUR (ej rådata), med skip-logik för genererade mappar.
`--subdir` + `--code-only` håller utskriften hanterbar. *(Kandidat → KÄRNPRINCIPER.)*

### LB.16 — Verifiera utfall mot FIL, inte mot loggrad
**Status:** ✅ Befordrad — bor i `MASTER_AZURE_COMPUTE.md` som **CZ.8**. Behållen här som pekare.
**Kort:** "Pipeline completed" / ren retur ≠ output skrevs. Efter varje körning: `ls -la` på output-mapp
(storlek > 0, färsk tidsstämpel). Vid validering, jämför värden i fil (pandas normaliserar radslut); CRLF
vs LF gör `diff` falsk-positiv — bekräfta med `xxd` att skillnaden bara är `0d0a` vs `0a`. *(2026-05-26:
körde `verify_output.py` mot varje `output_summary.xlsx` — rader, kolumner, elasticitet min/median/max,
neg-andel, p<0.05 — innan filen togs som giltig. `ls -la` storlek + tidsstämpel före verifiering.)*

---

## VM-körning av nya modellfamiljer (Site/Bundle) — 2026-05-26

### LB.17 — Rensa output: radera filer, BEHÅLL mappstrukturen
**Symptom:** feature_selection föll på `OSError: Cannot save file into a non-existent directory:
.../output/model/automl`.
**Rotorsak:** Vi flyttade undan hela `output/model/` för "ren proveniens". Men BCG-koden `mkdir`:ar
inte själv (CZ.5) — den förutsätter att output-undermapparna redan finns. Att radera output-mappen tog
med sig mappträdet koden skriver till.
**Regel:** Vid ren omkörning, radera/flytta *filer* men återskapa den tomma mappstrukturen
(`mkdir -p`) före körning: `output/model/automl/details`, `output/model/automl/results`,
`output/model/'model objects'`, `output/'regular price'`. Verifiera mot en tidigare lyckad körnings
struktur (`find <gammal_output> -type d`). *(Befordringskandidat → MASTER_AZURE_COMPUTE, skärper CZ.5.)*

### LB.18 — control_file.xlsx är INPUT till feature_selection, inte bara output
**Symptom:** `AttributeError: 'NoneType' object has no attribute 'melt'` i feature_selection.
**Rotorsak:** Vi flyttade bort `control_file.xlsx` i tron att feature_selection regenererar den.
`load_or_create_feature_control_file` skapar då bara en tom mall, skriver "please update file" och
returnerar `None` — nästa anrop (`check_nulls`) kraschar på `None.melt()`.
**Regel:** Behåll (eller seeda) en ifylld `control_file.xlsx` FÖRE launcher-körning. Den är *input*
till feature_selection, inte enbart dess output — den regenereras inte från scratch i ett svep.
Verifiera seed innan körning:
`python -c "import pandas as pd; df=pd.read_excel(path); print(len(df), (df['RUN']=='YES').sum())"`
(förväntat: full population, alla `RUN=YES`).

### LB.19 — En modellfamilj som aldrig körts på Linux bär ALLA ursprungliga Windows/stor-maskin-värden
**Symptom:** Cluster (tidigare Linux-fixad) körde rent. Site och Bundle, som aldrig körts på VM:en,
föll i tur och ordning på fyra olika rester: hårdkodad `C:\ray_spill` i feature_selection.py;
`constants.py` rad 2 med `open(r".\code\src\config.yml")` (relativ Windows-sökväg); `ray: memory: 80`
(→ 85,9 GB object store > /dev/shm 67,5 GB → `ValueError`); `ray: cpus: 50` (VM:en har 16 vCPU).
**Rotorsak:** Cluster var "ren" bara för att den fixats under en TIDIGARE körning. CZ.5-fixar gäller
PER modellfamilj, inte per VM — varje familjs `code/` är BCG:s orörda Windows/stor-kluster-original.
**Regel:** Innan en ny modellfamilj körs på VM:en, scanna OCH fixa i förväg (EN runda, inte krasch för
krasch):
- `grep 'directory_path' feature_selection.py` → ray_spill (`C:\` → `/tmp/ray_spill`)
- `grep 'config.yml' constants.py` → `.\code`-sökväg (fångas EJ av en `C:`-grep!) → `Path(__file__)`-metod
- `grep -A3 'ray:' src/config.yml` → memory/cpus mot VM:ens kapacitet (→ `memory: 32`, `cpus: 14`)
- control-fil finns och är ifylld (LB.18)
- output-mappstruktur (LB.17)
Fixa med backup (LB.8), byt till Cluster:s bevisade värden. Importtest av `constants.py` före körning
(`python -c "import constants; print(constants.START_DATE)"`) fångar config-sökvägsfel tidigt.
*(Befordringskandidat → MASTER_AZURE_COMPUTE.)*

### LB.20 — Launcherns steg 5 (data_prep_after_model_output.py) är icke-körbart på Linux men behövs inte
**Symptom:** Alla tre familjer dog i sista steget på `ModuleNotFoundError: No module named 'xlwings'`.
**Rotorsak:** Steg 5 importerar `xlwings` (Excel-COM, Windows-only) för rapportgenerering — fungerar
inte på Linux (ingen Excel att styra). `pip install xlwings` hjälper inte; importen kan lyckas men
funktionen faller när den försöker öppna Excel. (Cluster antogs tidigare ha gått hela vägen — men föll
sannolikt också här, oupptäckt, eftersom `output_summary.xlsx` redan fanns.)
**Regel:** Behandla xlwings-kraschen som FÖRVÄNTAD och OFARLIG. `output_summary.xlsx` (steg 6:s input)
produceras av model-steget FÖRE steg 5, och steg 5:s `blended_logic` är redan facit-validerad
fristående (`fallback_blend.py`, LB.2). Läs `output_summary.xlsx` direkt från `output/model/`; ignorera
steg 5-felet i launcher-loggen. *(Domänkoppling: IB.2.)*

## → LESSONS_BCG.md
### LB.21 — .ps1-script vägras av execution policy (samma familj som AppLocker)
**Symptom:** `.\script.ps1` vägras med "is not digitally signed / UnauthorizedAccess".
**Rotorsak:** IT-miljöns execution policy blockerar osignerade script — samma restriktionsfamilj
som AppLocker (.exe / pip.exe).
**Regel:** Leverera flerstegsoperationer som inklistringsbara kommandoblock, eller som `.py` (körs
AppLocker-rent via `python script.py`). Aldrig `.ps1` att anropa. Behåll ev. `.ps1` enbart som
dokumentation/karta. Ändra aldrig execution policy bara för att köra ett kopieringssteg.

### LB.22 — Kartesisk self-join i validering: merge på fullt rad-grain, aldrig delnyckel
**Symptom:** Valideringskorr 0,95 / nivåmatch 90,7 % trots att population + F1-F7-fördelning var
bit-identiska (sum |diff| = 0). Worst-10 visade symmetriska speglade par (A->B = B->A). "Rows
compared" 3,9 M mot källa på 108 979 rader.
**Rotorsak:** merge på `ProductKey` ensam, men dv8-raden är unik först på
`ProductKey + SiteCode + Clusters`. Self-join exploderade till kartesiska par som korsparade en
nyckels egna värden -> falsk diff.
**Regel:** Merge alltid på det fulla rad-grainet som gör en rad unik. Läs nyckeln ur konsumentkoden
(dv1/dv2 i creating_one_df), gissa den inte. Diagnossignatur: symmetriska speglade disagreements +
radantal som vida överstiger källans = kartesisk self-join, inte logikfel. (Efter fix: korr
1,000000, |diff| = 0, nivåmatch 100 %.)

### LB.23 — xlwings görs valfri för logikvalidering (Windows-lokalt)
**Symptom:** `import xlwings as xw` (top-level) kraschar vid filstart om paketet saknas, trots att
xlwings bara används i sista kosmetiska dashboard-skrivningen (efter att dv8 sparats).
**Rotorsak:** Top-level-import körs oavsett om funktionen anropas.
**Regel:** Patcha arbetskopian (aldrig originalet): `try/except ImportError` -> `xw = None`, wrappa
anropet i `if xw is not None`. Installera inte tunga COM-beroenden för en kosmetisk artefakt.
Leverera patch som idempotent `.py` (CRLF-exakt matchning), inte `.ps1`.

### LB.24 — Validera mot FRYST original, aldrig mot arbetskopian
**Symptom:** `verify_dataprep` mot `Pipeline\...\data\0828_*.csv` gav DuckDB-krasch ("not latin-1")
och en P_CH-fil på 179 byte (bara header). Facit verkade trasigt.
**Rotorsak:** Den katalogen är inte facit — den skrivs av `export_b4b_for_model.py` (överskrevs
2026-05-25): P_C om-encodades UTF-8, P_CH tömdes. Det orörda facit ligger i OneDrive-originalet
(53,8 MB P_C, latin-1, dec 2025).
**Regel:** Validera alltid mot det frusna originalet (`BCG_orginal_V2_New\...`), aldrig mot en katalog
som pipelinen själv skriver till. Alla verify_tool-defaults pekar på OneDrive-originalet. Symptom som
"om-encodad" eller "header-only-fil" = du tittar på en arbetskopia som drivit, inte på facit.

### LB.25 — Misstänk korr 1,0 tills källoberoende är bekräftat
**Symptom:** Data prep gav korr 1,000000 mot facit. Frestande att lita på direkt.
**Rotorsak:** Perfekt korrelation kan vara ett cirkelbevis — om vår "output" i hemlighet läser samma fil
som facit, matchar de trivialt utan att bevisa något.
**Regel:** Innan du litar på korr 1,0, bekräfta att källorna är oberoende. Här: verifierat att
`00_read.sql` läser rå `transaction_data.parquet` + DW-dimensioner, INTE BCG:s 0828-fil. Belägg för
äkta oberoende: olika sorteringsordning, olika kolumnantal (vår 11 / facit 13, facit har extra
`TotalNetXVat`/`Productive_time_per_site`), olika talformatering. Korr 1,0 + oberoende källor = äkta
match. Korr 1,0 + samma källa = inget bevis.

### LB.26 — verify-wrappers ärver `sys.executable` — kör med rätt interpreter
**Symptom:** `verify_dataprep`/`verify_blend` kraschade med `ModuleNotFoundError: No module named 'duckdb'`
när de kördes från `.venv`. Verktyget var rätt, miljön fel.
**Rotorsak:** Wrappers anropar `replicate_dataprep.py`/`fallback_blend.py` med SAMMA interpreter som kör
wrappern (`sys.executable`). Beroendena (duckdb/pandas) lever i **global Python 3.11**, inte i `.venv`
och inte i 3.13.
**Regel:** Kör hela verify_tool-sviten med `py -3.11` explicit. `.venv` saknar duckdb; global 3.11 har
allt (duckdb 1.5.3, pandas 3.0.1, openpyxl, numpy). Dokumenterat i verify_tool README:s Environment-sektion.
*(FAS T-skuld: miljön bor i global Python, ej isolerad venv — ej reproducerbar för efterträdare.)*

### LB.27 — Windows Store `python3.13.exe`-aliaset är en interpreter-fälla
**Symptom:** `python script.py` plockade `C:\Users\...\WindowsApps\python3.13.exe` (Store-aliaset) i
stället för rätt 3.11. `--excel`-kvittot skapades aldrig, för 3.13 saknar både duckdb och openpyxl.
**Rotorsak:** Windows lägger ett `python3.13.exe`-alias högt i PATH via WindowsApps. Skriver man bara
`python` får man det, inte den interpreter pipelinen behöver.
**Regel:** Använd alltid `py -3.11` (launchern väljer rätt explicit), aldrig bara `python`. Samma
interpreter-disciplin-familj som venv-fällan (LB.13/LB.26) i ny förklädnad.

### LB.28 — Hel-fil-kopia mellan modellfamiljer är farligt — mät hash, kopiera aldrig blint
**Symptom:** Vid G7-fixen frestande att kopiera cluster:s nya `constants.py` rakt över site + bundle
(de "är ju samma kod, olika data").
**Rotorsak:** De är INTE identiska. SHA256 skilde site från bundle. Bundle har `Product_Code_var='Bundle_code'`,
`Cluster_Granularity='Clusters'` (plural) + extra `Cluster_Granularity2`; cluster/site har `ItemCode`/`Cluster`.
Dessutom laddar site/bundle `constants.py` `config.yml` vid import (`import yaml`); cluster:s gör inte.
En hel-fil-kopia hade tyst skrivit över bundles granularitet och brutit modellen.
**Regel:** Jämför `Get-FileHash` innan du kopierar en fil mellan modeller. Skiljer de sig → applicera
fixen kirurgiskt (bara de rader som ska ändras), bevara varje fils särart. Verifiera efteråt att det
unika står kvar (bundle ska fortfarande visa `Bundle_code`/`Clusters`). Mät, gissa inte — igen.

---

## → INSIGHTS_BCG.md

### IB.2 — KORRIGERING: signifikansflaggan har ETT TREDJE villkor
Befintlig IB.2 (och NEXT_SESSION) anger flaggan `Significant ?` / `significant_<level>` som
`RSQ ≥ 0.5 AND PVALUE ≤ 0.20`. **Källan (`df_cleanup`, rad 377) har ett tredje villkor:**
```
significant_<level> = (round(RSQ,2) >= 0.5)
                    & (round(PVALUE_PRICE,2) <= 0.20)
                    & (ELASTICITY_PRICE < 0)
                    & (ELASTICITY_PRICE > -10)
```
Alltså: elasticiteten måste vara **negativ och inte mer extrem än −10** för att räknas som signifikant.
Ekonomiskt rimligt (en "signifikant" positiv elasticitet är brus, inte en priseffekt; <−10 är instabil
svans). **Konsekvens:** Halvsann dokumentation rättad — flaggan filtrerar även på elasticitetens tecken
och magnitud, inte bara RSQ/PVALUE. Detta påverkar inte den validerade outputen (replikering bit-identisk),
men är relevant för färsk-data-fasen: nya extremvärden utanför (−10, 0) faller automatiskt ur signifikans.

---

## Faktanot för dokumentation (inte lärdom, men korrigerar återkommande missförstånd)

**"Alteryx" i steg 6 är en print-etikett, inte ett beroende.** `read_excel_data` skriver
*"Shape of Product dataframe output from Alteryx"* — men koden läser en **statisk** `Complete_Product_Data.xlsx`
(en gång producerad av Alteryx, sedan arkiverad i `input_data\`). Vi kör ingen Alteryx och behöver ingen.
I färsk-data-fasen ersätts den filen av DW/SQL-prepen (modellkontraktet, TECHNICAL_PREREQUISITES §8) utan
att `read_excel_data` ändras — etiketten är kosmetisk och kan döpas om då.


---

## Hur listan växer

Ny lärdom läggs till **i samma session** den uppstår (KÄRNPRINCIPER §7 förbättringsloop), med nästa lediga
`LB.N`. Vid sessionsslut: överväg om någon LB-lärdom nu är generell nog att **befordras** till en MASTER_*.
Vid befordran — flytta innehållet, ersätt raden här med en pekare (som LB.12/LB.16), behåll ID:t.

---

*Skapad 2026-05-26 vid dokumentstruktur-omtaget. Extraherad ur NEXT_SESSION.md (PoC-2), SESSION_2026-05-25,
BCG_PRICING_PLAYBOOK §3/§10. LB.17–20 tillagda 2026-05-26 efter VM-körningspasset (Cluster full + Site +
Bundle → tre output_summary.xlsx).*

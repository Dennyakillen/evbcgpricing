# NEXT_SESSION — FAS F: förutsättningar för färsk körning (facit-isolering, DW-källa, datagrind)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på Evidensia
Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md`,
`MASTER_PYTHON.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`
(läs riktningsblocket överst). Lärdomar: `LESSONS_BCG.md` (`LB.N`). Insikter: `INSIGHTS_BCG.md` (`IB.N`).
Fasöversikt: `ROADMAP.md` (V→T→F→A). G7-fixen: `FAS_F_G7.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel) i
> `LESSONS_BCG.md`, eller ny insikt i `INSIGHTS_BCG.md`. Befordra till MASTER_* om generell.

> **Miljödisciplin:** Varje kommandoblock etiketteras med miljö. **PowerShell** (`PS C:\`). Kör pipeline
> + verify_tool med **`py -3.11`** (global Python har duckdb/pandas/openpyxl/numpy/yaml — `.venv` och 3.13
> saknar dem; Windows Store `python3.13`-aliaset är en fälla, **LB.26/LB.27**). Inga `.ps1` att anropa
> (execution policy, **LB.21**) — leverera kommandoblock eller `.py`.

> **Princip (hårt bekräftad gång på gång):** Vår egen dokumentation kan ha halva sanningen. Det vi
> upptäcker mot källan (`BCG_orginal_V2_New` + körande kod) trumfar alltid anteckningarna. Läs källan,
> gissa aldrig. Räddade oss flera gånger denna session: SQL-injektionspunkten, constants.py-skillnaderna
> mellan modeller (LB.28), `'2025-06-23'`-gåtan (W-MON-rundning).

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **origin/main:** `824c265` — *verify_tool: run_all orchestrator (+Excel receipt) and verify_infra
  structure audit; document both* (FAS V komplett, pushad)
- **Arbetsbranch:** `fas-f-fresh-data` @ `3e758b2` — *FAS F / G7: parametrize date window across pipeline*
- **Interpreter:** global Python 3.11 (`py -3.11`) — duckdb 1.5.3, pandas 3.0.1, openpyxl 3.1.5,
  numpy 2.4.2, pyyaml 6.0.3. INTE `.venv` (saknar duckdb), INTE 3.13.
- **Originalmapp (facit):** `C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New`

---

## Status vid sessionsstart

**FAS V är KLAR och pushad till main** (`824c265`): verify_tool-sviten (fem fristående verifierare +
run_all-orkestrerare + Excel-kvitto + verify_infra struktur-revision), hela kedjan FR-1..7 bevisad
6/6 PASS mot fryst facit.

**G7 är KLAR och pushad till branchen** (`3e758b2`, se `FAS_F_G7.md`): datumfönstret är env-overridable
tvärs hela pipelinen — `constants.py` (×3), `data_prepration.py` (cluster), och SQL via in-memory-injektion
i `replicate_dataprep.py`. **Default (inga env-vars) = fruset fönster, bit-identiskt** (bevisat:
verify_dataprep utan env → corr 1,0, ingen [G7]-rad). Override bevisad (BCG_END_DATE=2026-04-30 → SQL
omskriven, loggad).

**Återgång till gammalt facit:** `git checkout main`, eller kör branchen utan env-vars.

---

## Mål för denna session: de TRE förutsättningarna före en riktig färsk körning

G7 gör fönstret *settbart*. Det räcker inte för giltiga färska resultat — tre saker måste på plats,
i ordning (dokumenterat i FAS_F_G7.md "What's left"):

### 1. Isolera facit till skrivskyddad referens (FÖRST — billigast, störst skydd)
En färsk körning skriver till kataloger där BCG:s facit ligger oskyddat (2026-05-25-driften visade
risken, **LB.24**). Kopiera BCG-originalet till en read-only referensmapp INNAN någon färsk körning rör
de katalogerna. Detta är förutsättningen för all rimlighetsvalidering — utan fryst facit finns inget att
mäta mot.

### 2. Färsk källa, inte bara färskt fönster (Spår B)
`00_read.sql` läser fortfarande BCG:s frusna `transaction_data.parquet`. Ett färskt fönster över en
frusen källa har ingen färsk data att hämta. DW-native-läsningen måste byggas/verifieras så pipelinen
läser *aktuella* transaktioner för det valda fönstret. Se modellkontrakt §8, B.4b. Enda genuina
uppströms-input är FTE (Quinyx, IB.3) — Väg 2 = aggregera DW-vy, inte replikera BCG:s rådata-pipeline.

### 3. Datafullständighets-grind (Nivå 1-säkerhet)
Innan auto-körning av "senaste stängda månad": verifiera att DW faktiskt har komplett data för hela
fönstret. Att köra en ofullständig senaste månad = tyst fel. Detta är grinden som gör månatliga
auto-körningar säkra. (Auto-beräkning av "senaste stängda månad" är ETT steg bortom env-override — bygg
grinden först, auto-beräkningen sen.)

**Efter dessa tre:** en kontrollerad färsk körning, följd av rimlighetsvalidering mot det isolerade facit
(IB.6 — diffar små nog att inte flippa ett top-line-prisbeslut).

---

## Vision (förvaltning framåt — bekräftad denna session)

Slutmålet: modellen kör senaste stängda månads data automatiskt; månadsuppdatering = bara kör skriptet,
inga filändringar; på sikt i Azure utan Jens dator, körbart av kollegor utan Python-kunskap. Sekvens:
env-override (KLART) → auto-beräkna senaste månad + datagrind (NÄSTA) → Azure-automation (FAS A, långt
senare). Växande fönster med fast ankare 2022-07-01 (rullande trender = medvetet senare analytiskt steg,
inte nu).

---

## Standarder särskilt relevanta nu

- **LB.24** — validera mot fryst original, aldrig arbetskopia pipelinen skriver till.
- **LB.25** — misstänk korr 1,0 tills källoberoende bekräftat (cirkelbevis-risk).
- **LB.26/LB.27** — kör `py -3.11`, aldrig bara `python` (venv/Store-alias-fällor).
- **LB.28** — mät hash före fil-kopia mellan modeller; de skiljer sig (bundle `Bundle_code`/`Clusters`).
- **KÄRNPRINCIPER** — läs källan före bygge; grindar som rapporterar; mät, gissa inte.

---

## FAS T (tech-debt, parallellt — kräver ingen kod, kräver IT)

Strukturera skuldregistret till IT så miljön inte bara bor i repot:
- **Miljö i global Python 3.11**, inte isolerad venv — ej reproducerbar (nu även pyyaml där). Pinnad
  venv + requirements.txt behövs (förutsättning för FAS A).
- **Relativa sökvägar i site/bundle `constants.py`** (`.\code\src\config.yml`) — körning platsberoende,
  kraschar från fel katalog.
- AppLocker (.exe/pip.exe), execution policy (LB.21), blob-roll-blockering (Storage Blob Data
  Contributor, kräver Owner), lokal OOM på Stage 2 (varför VM behövs).

---

## Vid sessionsslut

1. Committa på `fas-f-fresh-data` (inte main förrän färsk körning är bevisad). Inga `.bak-g7` med.
2. `git status` — rent.
3. Uppdatera denna fil: ny SHA + nästa mål.
4. Nya lärdomar → `LESSONS_BCG.md`; insikter → `INSIGHTS_BCG.md`.
5. Städa `.bak-g7` ENDAST efter att hela G7-vägen körts färskt end-to-end (de är rollback tills dess).

---

*Skapad 2026-05-28 vid FAS F / G7-passets slut (branch fas-f-fresh-data @ 3e758b2). FAS V klar på main
(824c265). G7 klar på branchen — datumfönstret parametriserat, default bit-identiskt, override bevisad.
Nästa: de tre förutsättningarna (facit-isolering → DW-källa → datagrind) före en riktig färsk körning.*

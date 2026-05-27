# NEXT_SESSION — FAS V: bygg `verify_tool` (oberoende, repeterbara bevis per modelldel)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på Evidensia
Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md`,
`MASTER_PYTHON.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`
(läs riktningsblocket överst). Lärdomar: `LESSONS_BCG.md` (`LB.N`). Insikter: `INSIGHTS_BCG.md` (`IB.N`).
Fasöversikt: `ROADMAP.md` (V→T→F→A).

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel) i
> `LESSONS_BCG.md`, eller ny insikt i `INSIGHTS_BCG.md`. Befordra till MASTER_* om generell.

> **Miljödisciplin:** Varje kommandoblock etiketteras med miljö. **PowerShell** (`PS C:\`, lokal venv
> `.venv`) — kontrollera att prompten visar `PS`, inte bara `C:\`. Inga `.ps1` att anropa (execution
> policy blockerar, **LB.21**) — leverera kommandoblock eller `.py` (körs AppLocker-rent via `python`).

> **Princip (session 8, hårt bekräftad):** Vår egen dokumentation kan ha halva sanningen. Det vi
> upptäcker mot källan (`BCG_orginal_V2_New` + körande kod) trumfar alltid anteckningarna. Läs källan,
> gissa aldrig. Detta sänkte oss inte i session 8 — det räddade oss tre gånger (path-spöke, IB.2-villkor,
> Alteryx-etikett).

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Senaste commit på origin/main:** `96fe7a3` — *Validate step 6 fallback weave bit-for-bit against BCG
  facit (FR-7 done); add verify/patch/setup tools, LB.21-23, IB.2 correction*
- **Branch:** `main`
- **Venv:** `.venv` (Python 3.11; pandas 3.0.3, numpy 2.4.4, openpyxl 3.1.5 — xlwings ej installerat, ej nödvändigt)
- **Originalmapp (facit):** `C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New`
  (struktur: `...\BCG_orginal_V2_New\02. Elasticity\...`, INGET `Pipeline\`-led — repot har `...\BCG\Pipeline\02. Elasticity\...`).

---

## Status vid sessionsstart

**HELA replikeringen FR-1..7 är KLAR och bit-för-bit bevisad. Steg 6 (F1–F7-väv) validerades 2026-05-27
mot BCG:s facit: korr 1,000000, |diff|=0, F1–F7-fördelning identisk, 100 % nivåmatch.** Replikeringsfasen
är stängd. Vi går in i FAS V: paketera bevisen så de kan repeteras på begäran.

**Referensvärden (bevisade, för verifierarnas förväntade utfall):**

| Del | Grupper | Median elast. | Neg-andel | p<0,05 | Facit-match |
|---|---:|---:|---:|---:|---|
| Cluster | 3812 | −0,138 | 76,5% | 18,0% | ≈ BCG 17,8% (IB.1) |
| Site | 4673 | −0,054 | 62,4% | 9,3% | (IB.9) |
| Bundle | 125 | −0,211 | 85,6% | 22,4% | (IB.9) |
| Steg 6 (F1–F7) | 108 979 rader / 15 128 ProductKeys | — | — | — | korr 1,0, |diff|=0, 100 % nivåmatch |

---

## Mål för denna session

### Primärt: Bygg `verify_tool\` — ett bibliotek av oberoende, repeterbara verifierare

**Syfte (förtroende, inte orchestrering):** Ett bevis-bibliotek där varje modelldel valideras av ett
**fristående** script som kan köras på begäran och live visa *vad som jämförs mot vad* och att det
stämmer. Användningsfall: en beslutsfattare ifrågasätter kvaliteten på en specifik del → Jens kör just
den verifieraren live → skärmen visar grupper/elasticiteter/diff mot facit → tvivlet besvaras konkret.
**Inte** en monolitisk orchestrator (spröd, svartlåda). Granulariteten ÄR trovärdigheten.

**Designprinciper (bär dessa genom bygget):**
- Varje verifierare står själv, körs ensam, kräver inga andra.
- Var och en skriver i lager (population → kolumner/struktur → KPI), och **rapporterar avvikelser** i
  stället för binär PASS/FAIL (KÄRNPRINCIPER: grindar som rapporterar slår ja/nej). Mönstret är redan
  satt av `verify_fallback.py`.
- Var och en pekar explicit på *vår output* vs *BCG-facit* med sökväg, så det syns vad som jämförs.
- Lätt: lokalt, sekunder, ingen VM. Validerar **producerade outputfiler** mot facit — kör INTE om
  pipelinen (tung körning hör till FAS A / VM, och bevisades redan på VM-passet).
- ASCII-rena filer/ID; svenska i dokumentation, engelska i kod (KÄRNPRINCIPER §3).

**Leveranser:**
1. **Inventering FÖRST (blockerare — se nedan):** lokalisera alla befintliga `verify_*`-script på disk
   och i Git. Vi vet inte säkert vilka som finns (`verify_output.py` nämns för FR-4..6; `verify_fallback.py`
   committad idag). `verify_tool` ska VÄVA IHOP det som finns, inte återuppfinna det (LB.1).
2. `verify_tool\` skapad med en verifierare per modelldel:
   - `verify_cluster.py` — Cluster-output vs facit (3812 grupper, elasticitetsfördelning, signifikans).
   - `verify_site.py` — Site-output vs facit (4673 grupper).
   - `verify_bundle.py` — Bundle-output vs facit (125 grupper).
   - `verify_fallback.py` — steg 6 F1–F7-väv vs facit (flyttas/kopieras hit; redan klar & bevisad).
   - (Ev. `verify_blend.py` — steg 5 blend/representant-arv, om facit finns; jfr IB.2.)
3. `verify_tool\README.md` — listar varje verifierare: vad den bevisar, mot vilket facit (sökväg),
   exakt körkommando, förväntat utfall (referensvärdena ovan). Detta är skillnaden mellan "några script"
   och "en valideringssvit du kan visa upp".
4. (Valfritt, om tid) `run_all.py` — kör samtliga i följd och skriver en samlad rapport. Men de enskilda
   är primära; en run-all är bekvämlighet, inte beviset.

**Datakälla:** Era redan producerade outputs (hemtagna från VM, IB.9) + BCG-facit i originalets
respektive `output\`/`output_data\`. Lokalt, Windows, `.venv`.

---

## KÄRNPROBLEM att lösa FÖRST — inventering (LB.1)

Innan en rad skrivs: kartlägg vad som finns. Gissa inte att `verify_output.py` ser ut på ett visst sätt.

### Steg 0 — Pre-flight (PowerShell, .venv)
```powershell
cd "C:\Projekt\BCG"
git log --oneline -5
git status
```
Förväntat: senaste commit `96fe7a3`, working tree clean.

### Steg 1 — Inventera befintliga verifierare (disk + Git)
```powershell
cd "C:\Projekt\BCG"
Get-ChildItem -Recurse -Filter "verify_*.py" | Select-Object FullName, Length
git ls-files | Select-String "verify"
```
Mål: veta exakt vilka verifierare som finns, var, och om de är committade. Det avgör vad som flyttas in
i `verify_tool\` vs byggs nytt.

### Steg 2 — Lokalisera varje dels facit + vår output (mot disk, inte minne)
För Cluster/Site/Bundle: var ligger VÅR hemtagna output, och var ligger BCG-facit att matcha mot? (Steg 6
är redan löst: vår `_step6_run\...\output_data\Final_Fallback_Data_*.xlsx` vs originalets
`...\6. Fall Back Logic\output_data\Final_Fallback_Data_20250930_091648.xlsx`.) Bekräfta sökvägar med
`Test-Path` + storlek innan verifierare byggs. Facit finns en prompt bort — be om filerna ur originalet
om en sökväg är oklar.

---

## Steg (ett i taget, verifiera mellan steg)

1. **Inventering** (KÄRNPROBLEM ovan) — kartlägg, rapportera, besluta vad som flyttas vs byggs.
2. **Skapa `verify_tool\`** + flytta in `verify_fallback.py` (redan klar). Verifiera att den kör från nya
   platsen (absoluta/argument-sökvägar — platsoberoende, bekräfta).
3. **Bygg en verifierare i taget** (Cluster → Site → Bundle), var och en mot sin facit, lager + rapport.
   Kör + bekräfta förväntade referensvärden INNAN nästa byggs (fail-fast, isolera fel per enhet, A.3).
4. **`README.md`** — dokumentera sviten: per verifierare vad/mot vad/kommando/förväntat.
5. **Commit per verifierad enhet** (inte en stor klump, A.3). `.gitignore`: tunga outputs trackas ej —
   verifierarna läser dem, committar dem inte.

---

## Standarder särskilt relevanta nu

- **LB.1 / "facit en prompt bort"** — inventera och läs källan innan bygge; gissa aldrig sökväg/format.
- **LB.22** — merge alltid på fullt rad-grain (det som gör en rad unik), aldrig delnyckel. Symmetriska
  speglade diffs + uppblåst radantal = kartesisk self-join. Läs nyckeln ur konsumentkoden.
- **KÄRNPRINCIPER (grindar som rapporterar)** — varje verifierare visar avvikelser, inte ja/nej.
- **LB.21** — leverera `.py`, inte `.ps1` att anropa.
- **A.3** — max 3–5 filer per leverans, commit + sanity-check emellan.

---

## Efter detta pass (FAS T parallellt, sen F, sen A — se ROADMAP.md)

- **FAS T (kan börja parallellt, kräver ingen kod):** strukturera teknisk skuld-registret till IT —
  *varför* vi kört på VM (lokal OOM på Stage 2, **G-skuld**), AppLocker (.exe/pip.exe), execution policy
  (LB.21), blob-roll-blockeringen (Storage Blob Data Contributor, kräver Owner), G7-datumhårdkodning.
  Mål: en miljö IT kan ge oss så replikeringen inte bara bor i repot. Förutsättning för FAS A.
- **FAS F:** färsk data — G7-parametrisering (annars filtreras 2026-data tyst bort), output-rimlighetsgrind
  (ersätter facit när facit försvinner), SQL_data_prep / DW-vy (B.4b, modellkontrakt §8), FTE Väg 2 (Quinyx).
- **FAS A:** flytta städad struktur till robust Azure-miljö, körbar/schemalagd. Beror på FAS T (IT) + FAS F.
- **Städning (del av V eller egen):** `verify_tool` är fröet till den samlade valideringssviten Jens vill
  kunna visa upp. Ev. dela `verify_tool\` i verifierare (bevis) vs setup (engångsbyggen). Permanenta
  xlwings-valfriheten i pipelinekoden i stället för patch på arbetskopia.

---

## Vid sessionsslut

1. Committa varje verifierare + `README.md` (per enhet). Tunga outputs trackas ej (`.gitignore`).
2. `git status` — rent.
3. Uppdatera denna fil: ny SHA + nästa mål (FAS T-skuldregister eller FAS F).
4. Nya lärdomar → `LESSONS_BCG.md`; insikter → `INSIGHTS_BCG.md`.
5. Uppdatera `ROADMAP.md` (FAS V → ✅ när sviten är komplett) + playbookens riktningsblock + README:s roadmap.

---

*Skapad 2026-05-27 vid FR-7-passets slut (commit 96fe7a3). FR-1..7 stängd, bit-för-bit bevisad. Riktad mot
FAS V: bevis-bibliotek `verify_tool`. Inventering av befintliga verify_*-script är blockeraren att lösa
först (LB.1) — väv ihop det vi gjort, återuppfinn inte.*

# NEXT_SESSION — Steg 6-passet (Fall Back Logic, F1–F7 → final_elasticity)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på Evidensia
Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_AZURE.md`, `MASTER_AZURE_COMPUTE.md`,
`MASTER_PYTHON.md`. Linux/bash: `UBUNTU_AZURE_VM.md`. Nuläge: `BCG_PRICING_PLAYBOOK.md`
(läs riktningsblocket överst först). Lärdomar: `LESSONS_BCG.md` (`LB.N`). Insikter: `INSIGHTS_BCG.md` (`IB.N`).

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel) i
> `LESSONS_BCG.md`, eller ny insikt i `INSIGHTS_BCG.md`. Befordra till MASTER_* om generell.

> **Miljödisciplin (skärpt 2026-05-26):** Tre skal är i spel vid VM-arbete. Varje kommandoblock SKA
> etiketteras med miljö + hur den nås: **PowerShell** (`PS C:\`, kör `ssh`/`scp`/`az`), **bash på VM**
> (`azureuser@bcg-poc-vm`, kör pipeline — nås via `ssh azureuser@172.18.148.4`). Kolla prompten före
> varje kommando. `&&` är bash, fungerar ej i PowerShell. `ssh`/`scp` körs ALDRIG inifrån VM:en.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Senaste commit på origin/main:** `<UPPDATERA med SHA efter denna sessions push>`
- **Branch:** `main`
- **Repot innehåller hela receptet** (kod/config/control/kurerade inputs). Excel + tung output +
  körutfall utestängt. Strukturen är återskapningsbar.
- **Azure-VM:** `bcg-poc-vm`, `Standard_E16s_v5` (16 vCPU / 128 GB RAM), privat IP `172.18.148.4`,
  **deallocated** (disken består). Subscription `ev-lz3-ai (SE)`, RG `ev-openai-swce-rg-test` (PIM Contributor).
- **VM-disklayout:** `~/bcg/cluster/`, `~/bcg/site/`, `~/bcg/bundle/` (alla tre körda + fixade),
  `~/bcg/_old_runs_20260521/` (gamla rester), `~/verify_output.py`. Cluster-venv (`~/bcg/cluster/.venv`,
  Python 3.11.9) återanvänds för alla familjer.

---

## Status vid sessionsstart

**Full replikering är klar t.o.m. FR-6. Alla tre modellfamiljer (Cluster + Site + Bundle) är körda och
verifierade — de tre `output_summary.xlsx` som steg 6 behöver finns. Det enda kvarvarande för "full
replikering" är steg 6-vävningen (FR-7).**

- ✅ Klart: input-steg, model, feature_selection, steg 5-fallback (facit-validerad fristående).
- ✅ Klart (2026-05-26): VM-passet — Cluster full + Site + Bundle körda, verifierade, hemtagna (FR-4..6).
- 🔴 Detta pass: steg 6 (`Fall_Back_Logic.py`, F1–F7-väv) — FR-7. Input finns nu; blockeraren upplöst.

**De tre output_summary.xlsx (steg 6:s input) — hemtagna lokalt:**
- Cluster: `Pipeline\02. Elasticity\2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx`
- Site: `Pipeline\02. Elasticity\3. Product Site Level Models\output\azure_run_model\output_summary.xlsx`
- Bundle: `Pipeline\02. Elasticity\5. Bundle Clinic Models\output\azure_run_model\output_summary.xlsx`

**Referensvärden (verifierade 2026-05-26, för rimlighetskoll, se `IB.9`):**

| Familj | Grupper | Median elasticitet | Neg-andel | p<0,05 |
|---|---:|---:|---:|---:|
| Cluster | 3812 | −0,138 | 76,5 % | 18,0 % |
| Site | 4673 | −0,054 | 62,4 % | 9,3 % |
| Bundle | 125 | −0,211 | 85,6 % | 22,4 % |

- Cluster 18,0 % rå signifikans ≈ BCG:s frusna 17,8 % (`IB.1`) — trogen replikering bekräftad.

---

## Mål för denna session

### Primärt: Steg 6 — Fall Back Logic (F1–F7) → final_elasticity

**Syfte:** Köra `Fall_Back_Logic.py` (folder 6) som väver de tre modellfamiljernas output + steg 5:s
cluster-fallback till en slutlig elasticitet via F1–F7-prioritet (`np.select`). Detta stänger FR-7 och
därmed hela replikeringssidan.

**Leveranser:**
1. Läs `Fall_Back_Logic.py` i detalj NU (input finns → `LB.3` upphävd): `creating_one_df` +
   F1–F7-vävfunktionerna. Förstå np.select-prioritetsordningen.
2. Verifiera att steg 6 hittar sina tre `output_summary.xlsx` (cluster/site/bundle) + steg 5-output.
   Path-hantering kan ha samma Windows-rester som Site/Bundle (`LB.19`) — scanna FÖRE körning.
3. Kör steg 6 → `final_elasticity` (eller motsv. slutfil).
4. Rimlighetskoll av final_elasticity mot referensvärdena ovan + facit om tillgängligt.

**Datakälla:** de tre `output_summary.xlsx` (hemtagna) + steg 5-output. Kan köras lokalt om det inte är
tungt (steg 6 är en väv, inte en regression — sannolikt lätt), annars VM.

---

## Steg (ett i taget, verifiera mellan steg)

> **Notera:** Steg 6 är en VÄV, inte en tung modellkörning. Den är sannolikt lätt nog att köra lokalt
> (Windows). Avgör efter att ha läst `Fall_Back_Logic.py` — om den bara läser xlsx + np.select, kör
> lokalt. Om den drar Ray eller tung data, VM. Läs FÖRST (`LB.1`).

### Steg 0 — Pre-flight (PowerShell, Windows)
```powershell
cd "C:\Projekt\BCG"
```
```powershell
git log --oneline -5
git status
```
Förväntat: senaste commit `<SHA>`, working tree clean.

### Steg 1 — Läs steg 6-koden (FÖRE körning, LB.1/LB.4)
Läs `Pipeline\02. Elasticity\6. Fall Back Logic\` — särskilt `Fall_Back_Logic.py`:s `__main__`,
`creating_one_df`, F1–F7-funktionerna. Identifiera: vilka filer den läser (sökvägar), np.select-ordning,
och om den har Windows-rester (`C:\`, `.\code`, xlwings). Kartlägg som vi gjorde för modellerna.

### Steg 2 — Scanna Windows-rester (LB.19)
Steg 6 kördes aldrig på Linux. Om den ska köras på VM: scanna `grep 'C:'`, `grep 'config.yml'`
i ev. constants, `grep 'xlwings'`. Om den körs lokalt (Windows): sökvägarna fungerar som de är, men
verifiera att de tre `output_summary.xlsx` ligger där steg 6 förväntar dem.

### Steg 3 — Kör steg 6
Lokalt (om lätt) eller VM (om tung). Tee till logg, filtrera strukturella rader (`LB.14`).

### Steg 4 — Verifiera final_elasticity
Rimlighetskoll mot referensvärdena. Negativ elasticitet, trovärdiga band. Om BCG-facit för slutsteget
finns — jämför. Annars output-rimlighet (`IB.6` — facit-fasen).

---

## Standarder särskilt relevanta nu

- **LB.1** — läs `Fall_Back_Logic.py` FÖRE körning; input finns nu så detaljläsning är befogad.
- **LB.3** — upphävd för steg 6: input (tre output_summary.xlsx) finns, steget är inte längre blockerat.
- **LB.4** — för att veta vad steg 6 behöver, läs dess `__main__` (konsument-kontraktet).
- **LB.19** — steg 6 kördes aldrig på Linux; scanna Windows-rester före ev. VM-körning.
- **LB.20** — om steg 6 importerar xlwings: samma fälla som steg 5, hantera/kringgå.
- **LB.14** — tee + grep strukturella rader.
- **CZ.2** — om VM används: deallokera direkt efter. **OBS:** PIM-roll + az-token kan ha gått ut sedan
  förra passet — återaktivera PIM i portalen + `az login` vid `AuthorizationFailed`/`AADSTS70043`.

---

## Efter detta pass (förberedelse, ej denna session)

Med steg 6 klart är HELA replikeringen (FR-1..7) stängd. Då återstår **färsk-data-fasen** mot
affärsmålet (`IB.6`): output-rimlighetsgrind + G7-datumparametrisering (annars filtreras färsk 2026-data
tyst bort av det hårdkodade `START_DATE 2022-07-01 / END_DATE 2025-06-30`) + FTE Väg 2 (Quinyx).
Parallellt: DW-native bygget (Spår B, se `TECHNICAL_PREREQUISITES.md`).

---

## Vid sessionsslut

1. Committa ev. ändrade verktyg/dokumentation och pusha (output går INTE in — utestängt av `.gitignore`).
2. `git status` — ska vara rent.
3. Om VM användes: bekräfta `VM deallocated`.
4. Uppdatera denna fil: ny SHA + nästa mål (färsk-data-fasen / DW-bygget).
5. Nya lärdomar → `LESSONS_BCG.md`; nya insikter → `INSIGHTS_BCG.md`; befordra till MASTER_* om generella.
6. Uppdatera playbookens riktningsblock (FR-7 → ✅) och README:s roadmap.

---

*Skapad 2026-05-26 vid VM-passets slut. Riktad mot steg 6 (FR-7) — det enda kvarvarande för full
replikering. FR-4..6 stängda: tre output_summary.xlsx körda, verifierade, hemtagna. Blockeraren (LB.3)
upplöst — steg 6 kan nu läsas och köras.*

# BCG_PRICING_PLAYBOOK — Replikering och migrering av BCG:s prissättningsflöde

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md` och
`MASTER_AZURE.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md vid sessionsslut.

**Syfte:** En läsare ska förstå exakt var projektet står, vilka steg vi tagit och ska ta,
vilka beslut som är fattade och vilka som återstår — utan att rekonstruera kontext.

**Projektets natur:** Replikering och migrering, inte utveckling. Vi återskapar BCG:s flöde
faithfully (trogna namn, verbatim-kopia) och städar/rättar *längs vägen*. Designfel loggas
i avsnitt 9 för att specas mot konsult senare — åtgärdas inte nu.

**Nuläge i en mening:** Replikeringen är byggd och miljön verifierad lokalt, men en full
körning ryms inte på lokal maskin (OOM) — därför har vi rest in i Azure och har en körklar
VM (`bcg-poc-vm`, 128 GB RAM) som väntar på första riktiga körningen.

**Senast uppdaterad:** 2026-05-20.

---

## 1. Beslut (decision log)

| # | Beslut | Motivering |
|---|---|---|
| D1 | Källa = `BCG_orginal_V2_New` | BCG:s bekräftade slutversion; innehåller v2-fixar |
| D2 | Alteryx skippas helt | SQL-steget ersätter Alteryx; `.yxmd`/`.yxdb` kopieras ej |
| D3 | Allt ut ur OneDrive till `C:\Projekt\BCG` | Löser venv-i-OneDrive, sync-låsning, sökvägs-strul |
| D4 | `duckdb.exe` ersätts av duckdb-Python-paketet | AppLocker blockerar `.exe`; IT: exe är dött |
| D5 | Ray-resurser sätts i `config.yml` (`ray:`-sektionen) per maskin | v2 flyttade parametrarna dit; inget i koden ändras |
| D6 | Interim-input: BCG:s `0828_*` CSV:er tills SQL-steget validerats | Frikopplar modellvalidering från SQL-migrering |
| D7 | Trogna namn, verbatim-kopia i fas 1; städning senare | Spårbarhet, minimera replikeringsfel |
| **D8** | **Azure blir testmotorn (PoC)** — lokal maskin räcker inte | 31 GB RAM → OOM; bevisat 2026-05-20 |
| **D9** | **VM utan publik IP, i befintligt VNet, nås från kontorsnätet** | Tenant-policy förbjuder publika IP:n |
| **D10** | **Eget Git-repo (`evbcgpricing`), endast våra artefakter — ej Pipeline-data** | Git för vårt arbete; data/kod bor i V2_New/Azure |
| **D11** | **PoC-genväg: lånar LZ3-connectivity-subnet, VM-disk ej Blob** | Bevis först, elegant drift sen |

## Öppna beslut

| # | Fråga | Behöver |
|---|---|---|
| O1 | Owner på `ev-openai-swce-rg-test`? | Kent — krävs för dataroller/Blob/ACR, ej för VM-PoC |
| O3 | Krävs `InScope Mapping.xlsx` + icke-tom `date_to_month_year_mapping.csv`? | Avgörs vid körning |
| O4 | Blob + DW-vyer (spår B, drift) — när? | Efter PoC validerad |

---

## 2. Migreringsfaser

| Fas | Innehåll | Status |
|---|---|---|
| 0 | Orientering, scan, källa & rotorsaker | ✅ KLAR |
| 1 | Replikera struktur + kopiera källor (`Build-Structure.ps1`, `Copy-Sources.ps1`) | ✅ KLAR |
| 2 | Miljö: venv + `requirements.txt` (lokalt) | ✅ KLAR (lokalt) |
| 3 | Ray-config + första modellkörning | ⚠️ Config satt; **lokal körning OOM:ade** → flyttas till Azure |
| **8** | **Azure-motor (PoC): VM byggd, data+kod+venv+körning** | 🔄 **VM klar, nästa: kör** |
| 4 | SQL data prep (ersätt `duckdb.exe` med Python) | Planerad |
| 5 | Övriga modellsteg (Site, Bundle) | Planerad |
| 6 | Fall Back Logic (fixa hårdkodade sökvägar) | Planerad |
| 7 | Mata pricing-modellen + validera KPI mot facit | Planerad |
| 9 | Git-baslinje (eget repo, efter validering) | 🔄 Påbörjad (denna session) |
| B | DW-vyer + Blob input-folder (drift) | Senare |

**Kritisk insikt:** Faserna är inte längre strikt linjära. Fas 8 (Azure) är *var* vi kör;
faserna 3–7 är *vad* vi kör. Bastestet (fas 3) körs nu i Azure (fas 8), inte lokalt.

---

## 3. Dagens stora lärdomar (det vi inte visste i morse)

1. **Ray-felet var inte i koden.** v2 flyttade `cpus`/`memory` till `config.yml` (`ray:`-sektionen, rad 128–131). Värdet stod på `memory: 80` (GB) — kalibrerat för BCG:s maskin. Fix: `memory: 8`, `cpus: 12` för en 31 GB-maskin. **Koden rörs inte.** Detta är inte en kodfix utan ett konfigvärde.
2. **Filen jag först diagnosticerade var fel version.** En tidig uppladdning visade hårdkodat `80 * 1024**3` i `feature_selection.py`; den riktiga v2-filen parametriserar via config. Sanity-check (`Select-String`) fångade diskrepansen. → L.14 i praktiken.
3. **Replikeringen kan inte valideras lokalt.** 31 GB RAM → Ray OOM:ar (`GetLastError() = 1455`, paging file för liten). Ett steg ensamt tog 120+ min och kraschade. Detta är ett *resultat*, inte ett misslyckande — det motiverar Azure.
4. **`Pipeline completed` ljuger** (R7) — skrivs även vid krasch. Verifiera alltid output-fil, aldrig loggraden.
5. **`$Args` är ett reserverat namn i PowerShell** — krockar med automatisk variabel, gör splat tom. Använd `$RoboArgs`.
6. **PS 5.1 läser UTF-8-script som CP1252** — levererade `.ps1` ska vara ren ASCII; å genereras via `[char]0x00E5`.
7. **Azure: tenant-policy förbjuder publika IP:n.** VM måste skapas med `--public-ip-address '""'` i befintligt VNet.
8. **Contributor ≠ dataroll.** Skapa storage/VM går; skriva blobar kräver `Storage Blob Data Contributor` (egen dataroll), som Contributor inte får tilldela (E.4/AZ.1).
9. **azcopy kör lokalt** (exe i användarprofil ej AppLocker-blockerat) — men exe-förbudet gäller *lösningen*, inte ett lokalt engångsverktyg. Beslut tas medvetet.

---

## 4. Azure-läget (fas 8)

| Resurs | Värde |
|---|---|
| Subscription | `ev-lz3-ai (SE)` — `42f726f8-91ee-44d4-832f-9d9ec412ef8f` |
| Resursgrupp | `ev-openai-swce-rg-test` (din sandlåda, PIM Contributor) |
| VM | `bcg-poc-vm`, `Standard_E16s_v5` (16 vCPU / **128 GB RAM**), Ubuntu 22.04, 128 GB disk |
| Privat IP | `172.18.148.4` (ingen publik — nås från kontorsnätet via SSH) |
| VNet/subnet | `ev-lz3-swce-vnet-prod` / `ev-lz3backend-swce-snet-prod` (lånat, D11) |
| Storage | `evbcgpricinginput` (containrar `input`, `output`) — **låst** tills dataroll (O1) |
| E-serie-kvot | 0/50 i lz3 — fri |

**Kostnadsdisciplin (KRITISKT):** VM kostar ~8–10 kr/h **igång**, nära noll stoppad.
Mönster: `az vm start` → jobba → `az vm deallocate`. Deallocate (ej bara stop) stoppar
debiteringen. Disken består, så omstart bygger inte om något.

---

## 5. Vad pipelinen gör (config-/strukturnivå)

Priselasticitetsmodell för efterfrågan. Beroende variabel: `QuantitySold(SalesTotal>0)`.
Per produktgrupp (`KEY`) körs **OLS-regression** (`statsmodels`); priskoefficienten *är*
elasticiteten (`ELASTICITY_Regular_Price_fwbw_max_6`). Feature-selection är en **brute-force
delmängdssökning** (`itertools`) parallelliserad över Ray. Glesa grupper hanteras via
klustring + fallback/blend (`final_elasticity`). Domänanpassningar värda att notera: bemanning
som kontrollvariabel, och dummies för två negativa medieperioder (mar24/jan25).

**Frågetecken att verifiera mot full kod** (model.py/regular_price.py/data_prepration.py):
prisendogenitet, temporal vs slumpad train/test-split (`train_perc: 0.90`), log-log vs semi-log
(avgör exakt elasticitetsdefinition).

---

## 6. Riskregister

| ID | Symptom | Rotorsak | Status |
|---|---|---|---|
| R1 🔴→✅ | Ray OOM-krasch | Hårdkodat 80 GB i config (BCG:s maskin) | Löst: `config.yml memory:8/cpus:12` — men lokal maskin OOM:ar ändå → Azure |
| R2 🔴 | DuckDB-steget kraschar | Blockerad `duckdb.exe` | Ersätts av Python-paket på Linux-VM (fas 4) |
| R3 🔵→✅ | venv i OneDrive | Konsultleverans | Löst (D3) |
| R4 🔵→✅ | `pip.exe` nekas | AppLocker | `python -m pip` |
| R5 🟡 | `config.yml` ej hittad | Fel CWD | Kör launcher från `code\`-mappen |
| R6 🟡 | Fall Back hårdkodad sökväg | Ej parametriserad | Fas 6 |
| R7 🟡 | "Pipeline completed" vid fel | Saknad exit-code | Verifiera output-fil |
| R8 🟡 | "output from Alteryx" i logg | Ej omdöpt | Spec mot konsult |
| R9 🔵→ | xlwings/pywin32 | — | **Gäller ej modellsteget** (openpyxl); ev. fas 7 |
| R10 🔵→✅ | Mojibake i `.ps1` | PS 5.1/CP1252 | Script är ASCII; å via `[char]0x00E5` |
| **R11** 🔵 | Azure-VM utan publik IP | Tenant-policy | Löst (D9); nås via kontorsnät |
| **R12** 🔵 | Blob-skrivning nekad | Saknar dataroll | Väntar Owner (O1); ej blockerande för VM-PoC |

---

## 7. Ray-config (fas 3, KLAR lokalt)

I `...\code\src\config.yml`, `ray:`-sektionen. Lokalt (31 GB): `cpus: 12`, `memory: 8`.
**På Azure-VM (128 GB) kan vi vara generösa:** `cpus: 14`, `memory: 32` (eller högre) — ingen
OOM-risk. Sätt detta innan körning på VM:en. `feature_selection.py` rörs aldrig.

---

## 8. Vad nästa pass gör (fas 8 forts.)

På `bcg-poc-vm`: (1) installera Python 3.11 + venv, (2) få upp kod + data, (3) `pip install -r
requirements.txt` (Linux → duckdb trivialt), (4) sätt `config.yml` `ray:` för 128 GB, (5) kör
`launcher.py` **med tee:ad logg** (skicka bara strukturrader — se README), (6) jämför
`output_summary.xlsx` mot BCG:s frusna facit. Det är PoC-målet: en validerad körning.

---

## 9. Återbesök mot konsult (spec senare)

Maskinspecifik config ej parametriserad (delvis fixad i v2) · `.exe`-beroende i intern leverans ·
"Pipeline completed" vid fel · hårdkodade Fall Back-sökvägar · Alteryx-referenser kvar i logg ·
död config (`reference.csv`/`baseline_control.csv`) · `C:\ray_spill` hårdkodad spill-katalog.

---

## 10. Nya lärdomar till MASTER-filerna

**MASTER_PYTHON:**
- `$Args` reserverat i PowerShell → splat blir tom; använd `$RoboArgs`.
- Levererade `.ps1` ska vara ASCII; icke-ASCII genereras via `[char]0xNNNN` (PS 5.1/CP1252).
- Verifiera filversion med `Select-String` innan fix — en uppladdad fil kan vara fel kopia (L.14).

**MASTER_AZURE:**
- Tenant-policy förbjuder publika IP:n → `--public-ip-address '""'` + befintligt VNet.
- Tom sträng till `az` i PowerShell skrivs `'""'` (enkelfnutt utanpå).
- Contributor får ej tilldela dataroller (`Storage Blob Data Contributor`) — kräver Owner (E.4/AZ.1).
- PoC-VM utan publik IP nås från kontorsnätet om det routar till VNet:et (ExpressRoute/S2S).

---

*Skapad av Jens Palmö (utvecklare) med AI-rådgivaren. Reviderad 2026-05-20 vid Azure-PoC.*

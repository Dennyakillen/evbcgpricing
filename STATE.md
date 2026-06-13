# STATE — nuläge och färskvara (evbcgpricing)

**Roll:** Detta är projektets *enda* källa för färskvara — det som är sant **nu** och ändras ofta:
resurs-ID, VM-status, aktiv subscription, roller, blob-läge, senaste commit. Allt annat
(principer, lärdomar, beslut, roadmap) bor i sina egna filer och *pekar hit* för aktuella värden.

**Underhållsregel (kritisk):** ersättande, inte additiv. När ett värde ändras — *skriv över raden*
och uppdatera dess datum. Stapla aldrig "gammalt värde bredvid nytt"; en korrigerad rad bredvid den
felaktiga är inte historik, det är en framtida tyst-fel-källa. Historik hör i git-loggen och i
LESSONS/beslut — inte här. Varje rad bär **senast verifierad**-datum så att en stale rad kan kännas
igen (en inaktuell rad ser annars identisk ut med en aktuell — det är hela faran).

**Varför filen finns:** AI:n har inget minne mellan sessioner. Denna fil *är* minnet av var projektet
står. En ny session läser den först och vet omedelbart nuläget utan att rekonstruera ur gissning.

**Känslighet:** filen bär interna resurs-ID och bör vara `.gitignore`:ad om repot någonsin delas
externt. Koden läser dessa värden från env/konfiguration — aldrig hårdkodade i kod (se MASTER_AZURE).

---

## 1. Var projektet står (en mening)

**FAS A pågår** — orchestrator-motorn kör site-modellsteget end-to-end via Azure och reproducerar
facit bit-för-bit; replikering (FAS V) och färsk-data (FAS F) är klara. *(Senast verifierad: 2026-06-12)*

| Fas | Status | Senast verifierad |
|---|---|---|
| FR-1..7 Replikering | KLAR (bit-för-bit mot facit) | 2026-05-27 |
| FAS V Bevis-bibliotek (verify_tool) | KLAR | 2026-05-27 |
| FAS F Färsk data | KLAR (alla 3 familjer växande, Step 6 validerad, modell matbar) | 2026-06-11 |
| FAS A Azure-drift | PÅGÅR (site-runnern bevisad; cluster-runner härnäst) | 2026-06-12 |
| FAS T Teknisk skuld → IT | ÖPPEN (Blob-dataroll ABAC-blockerad) | 2026-06-12 |

---

## 2. Repo & arbetskopia

| Vad | Värde | Senast verifierad |
|---|---|---|
| Aktivt repo | `evbcgpricing` (repo-URL i README, ej här) | 2026-06-12 |
| Lokal sökväg | `C:\Projekt\BCG` | 2026-06-12 |
| Branch | `main` (växande-data-arbetet historiskt på `fas-f-fresh-data`) | 2026-06-12 |
| Senaste relevanta commit | `6c9b4b8` — frontyta FAS A (read-only dashboard) | 2026-06-12 |
| Parallellrepo (DW-extraktion) | `Business_Analytics`, `C:\Projekt\Business_Analytics` | 2026-06-12 |

> Verifiera vid sessionsstart: `git log --oneline -5` + `git status`. Om SHA ovan inte matchar
> HEAD — uppdatera denna rad innan arbete (sessionsstartsprotokollet, KÄRNPRINCIPER §6.1).

---

## 3. Azure-resurser (BCG-pricing) — färskvara

| Resurs | Värde | Senast verifierad |
|---|---|---|
| VM | `bcg-poc-vm`, Standard_E16s_v5 (16 vCPU / 125 GB RAM), Ubuntu 22.04 | 2026-06-12 |
| VM privat IP | `172.18.148.4` (ingen publik IP — tenant-policy) | 2026-06-12 |
| VM power-state | **DEALLOCATED** (verifiera — se nedan; debiterar ~9 kr/h när running) | 2026-06-12 |
| Resursgrupp | `ev-openai-swce-rg-test` | 2026-06-12 |
| Aktiv subscription | `ev-lz3-ai (SE)` | 2026-06-12 |
| SSH | `ssh azureuser@172.18.148.4` (endast kontorsnät/VPN) | 2026-06-12 |
| Blob-auth | **kontonyckel-läge** (`PRICINGMODEL_AUTH=key`) — AAD-roll ABAC-blockerad | 2026-06-12 |
| Managed Identity (mål) | `evi-pricingmodel-mi-prod` (väntar Blob-dataroll, se §6) | 2026-06-12 |

> **Subscription-fälla (LB.46):** `az` cachar aktiv subscription mellan sessioner. Kör ALLTID
> `az account show` före VM-kommandon; sätt rätt med `az account set --subscription "ev-lz3-ai (SE)"`.
> Fel subscription ger `AuthorizationFailed` (VM "finns inte"), inte token-fel.

> **Verifiera VM power-state (LB.60 — lita på tillståndet, inte på log-raden):**
> ```powershell
> az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code,'PowerState/')].displayStatus" -o tsv
> ```
> En "deallocated"-rad i en körlogg är INTE bevis på att VM:en är nere. Verifiera alltid efter körning.

---

## 4. Miljöer (tre, korsa aldrig)

| Miljö | Sökväg | Bär | Senast verifierad |
|---|---|---|---|
| Global Python 3.11 | systemets `py -3.11` | verify_tool, validering, Step 6, build_r12 (duckdb/pandas/openpyxl/xlwings) | 2026-06-12 |
| Business_Analytics venv | `C:\Projekt\Business_Analytics\.venv` | DW-extraktion (pyodbc) | 2026-06-12 |
| Pipeline venv (VM) | `~/bcg/cluster/.venv` på VM | Ray/statsmodels, modellsteg 1-4 (delas av alla 3 familjer) | 2026-06-12 |

> System-Python 3.10 på VM saknar Ray — använd pipeline-venv. Cluster har egen `.venv` (aktiverad,
> ej lånad); Site delar Cluster's. Detaljerad miljödisciplin: MASTER_PYTHON.

---

## 5. Vad som är färskt vs fruset (operativ sanning)

| Del | Tillstånd | Senast verifierad |
|---|---|---|
| Cluster + Site-elasticiteter | VÄXANDE (färsk) | 2026-06-11 |
| R12 volym & omsättning | VÄXANDE (`build_r12_for_model.py`) | 2026-06-11 |
| `transaction_data.parquet` | Regenererad t.o.m. 2026-04-30 (27,4M rader) | 2026-06-11 |
| Cluster steg-5-routning | FRUSEN (2025) — FD.15 | 2026-06-11 |
| Väv-vikter | FRUSEN (2025) — FD.14 | 2026-06-11 |
| Bundle-gren | FRUSEN/parkerad — FD.11 (2,2 % väv-vinst) | 2026-06-11 |

> De tre frusna låsen (LF.9) står på 2025-värden medvetet. Kärnsignalen för priskänslighet är färsk.
> Uppdateringsordning vid behov: FD.15 → FD.14 → FD.11 (kostnad vs påverkan).

---

## 6. Öppen IT-skuld som blockerar full autonomi (FAS T)

| Skuld | Effekt | Väntar på | Senast verifierad |
|---|---|---|---|
| Blob-dataroll (Storage Blob Data Contributor) till MI | kontonyckel-läge i stället för AAD | Owner (Kent) — ABAC-blockerad | 2026-06-12 |
| Pinnad/reproducerbar venv på VM | miljö ej deterministisk | eget arbete, ej IT | 2026-06-12 |

> När Blob-rollen ges: sätt `PRICINGMODEL_AUTH=aad`, ta bort nyckel-läget (skuld i `blob.py`-headern).
> Övrig permanent IT-miljörestriktion (AppLocker, pip.exe, public-IP-policy) är hållbar kontext —
> bor i MASTER_PYTHON/MASTER_AZURE, inte här (den ändras inte per session).

---

## 7. Snubbeltrådar denna fas (kort — full lärdom i LESSONS_BCG)

- Token dör var 4:e h (E.3): `az login --scope https://management.core.windows.net//.default`.
- VM nås bara på kontorsnät/VPN. SSH-timeout = nätet, inte koden.
- `orchestration/` är enda sanning för motorfilerna; `workspace/`-kopior gitignoreras (dubbletter
  ställde till det 2026-06-12).
- Regenerera `transaction_data.parquet` FÖRST vid ny period — annars filtreras ny data tyst bort
  (LB.50 / G7-klassen).

---

*Förvaltas av Jens Palmö (Senior Business Analyst). Färskvarufil — uppdateras vid varje sessionsslut
(KÄRNPRINCIPER §6.2). Ersätter tidigare spridd state i NEXT_SESSION + MASTER_AZURE + DRIFT. För vad
*nästa session ska göra* (kö, prioriteringar), se NEXT_SESSION.md — den ändras varje session och hålls
skild från denna mer stabila nulägesfil.*

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

**FAS A pågår** — tre familje-runners (cluster/site/bundle) kör modellsteg 1-4 på Azure-VM:en, var
och en auto-validerar mot fryst facit och laddar upp all output till Blob. En webapp-dashboard visar
modellens hälsa som en förtroende-tratt per familj. Konto-spretigheten löst (FD.35: allt i ett
test-konto, 19/19 rör-kontroller gröna). Bundle aktiverad som fullvärdig familj (FD.34). Replikering
(FAS V) och färsk-data (FAS F) klara. Cluster + Site körda VÄXANDE end-to-end på VM 2026-06-17
(4180 + 6624 KEY = matchar facit, allt till Blob). Alla tre familjer körda VÄXANDE (bundle 2026-06-20: 125 KEY, median -0,21). Orkestrerings-MOTORN
validerad 2026-06-22 med tre statiska sonder; run_id ändrat till **datafönster** (`window_run_id`) så
alla familjer för samma period delar EN statusfil, och `RunStatus.finalize()` byggd så run-nivån
härleds ur faserna (heartbeat-spöket dött). Verifierat i dashboarden via syntetisk statusfil (alla
gröna i synk, vilande). Nästa: `run_after.py` (Efter-kedjan, FD.37), prod-konto-städning, app-polering.
*(Senast verifierad: 2026-06-22)*

| Fas | Status | Senast verifierad |
|---|---|---|
| FR-1..7 Replikering | KLAR (bit-för-bit mot facit) | 2026-05-27 |
| FAS V Bevis-bibliotek (verify_tool) | KLAR | 2026-05-27 |
| FAS F Färsk data | KLAR (alla 3 familjer växande, Step 6 validerad, modell matbar) | 2026-06-11 |
| FAS A Azure-drift | PÅGÅR (motor validerad m. sonder; run_id=datafönster + finalize; run_after.py härnäst FD.37) | 2026-06-22 |
| FAS T Teknisk skuld → IT | ÖPPEN (Blob-dataroll ABAC-blockerad) | 2026-06-12 |

---

## 2. Repo & arbetskopia

| Vad | Värde | Senast verifierad |
|---|---|---|
| Aktivt repo | `evbcgpricing` (repo-URL i README, ej här) | 2026-06-12 |
| Lokal sökväg | `C:\Projekt\BCG` | 2026-06-12 |
| Branch | `main` (bekräftat 2026-06-22) | 2026-06-22 |
| Senaste relevanta commit | `d98c5da` (FD.36 avslut + tre sonder); dagens motor-arbete (run_id/finalize/3 sonder) EJ committat än 2026-06-22 | 2026-06-22 |
| Orkestrator-push-status | Allt pushat till `main` (orchestration/ är single source; webapp + tre runners + bundle live) | 2026-06-16 |
| Parallellrepo (DW-extraktion) | `Business_Analytics`, `C:\Projekt\Business_Analytics` | 2026-06-12 |

> Verifiera vid sessionsstart: `git log --oneline -5` + `git status`. Om SHA ovan inte matchar
> HEAD — uppdatera denna rad innan arbete (sessionsstartsprotokollet, KÄRNPRINCIPER §6.1).

---

## 3. Azure-resurser (BCG-pricing) — färskvara

| Resurs | Värde | Senast verifierad |
|---|---|---|
| VM | `bcg-poc-vm`, Standard_E16s_v5 (16 vCPU / 125 GB RAM), Ubuntu 22.04 | 2026-06-12 |
| VM privat IP | `172.18.148.4` (ingen publik IP — tenant-policy) | 2026-06-12 |
| VM power-state | **DEALLOCATED** (verifierat `VM deallocated` 2026-06-16; ~9 kr/h running) | 2026-06-16 |
| VM auto-shutdown | **INGEN konfigurerad** (ResourceNotFound 2026-06-15) — deallokera ALLTID manuellt (LB.68) | 2026-06-15 |
| VM managed identity | SystemAssigned, principalId `c45a568e-...` (saknar Blob-dataroll, ABAC) | 2026-06-15 |
| VM `az`-CLI | INTE installerat på VM:en (`az: command not found`) — VM kan ej läsa Blob via az | 2026-06-15 |
| Resursgrupp | `ev-openai-swce-rg-test` | 2026-06-12 |
| Aktiv subscription | `ev-lz3-ai (SE)` (id `42f726f8-91ee-44d4-832f-9d9ec412ef8f`) | 2026-06-15 |
| SSH | `ssh azureuser@172.18.148.4` (endast kontorsnät/VPN) | 2026-06-12 |
| Storage-konto | `evbcgpricinginput` (FD.35: ett hem, test-RG dar VM bor; prod-kontot orort tills stadning) | 2026-06-16 |
| Blob-containrar (test-konto) | `input` (vaxande parquet 27,4M rader), `output`, `runstatus`, `pipeline` (00_frozen_facit/ cluster+site+bundle) | 2026-06-16 |
| Blob-auth | **kontonyckel-läge** (`PRICINGMODEL_AUTH=key`) — AAD-roll ABAC-blockerad; `--auth-mode login` ger TYST tomt utan dataroll (LB.67) | 2026-06-15 |
| Managed Identity (mål) | `evi-pricingmodel-mi-prod` (väntar Blob-dataroll, se §6) | 2026-06-12 |

> **Subscription-fälla (LB.46):** `az` cachar aktiv subscription mellan sessioner. Kör ALLTID
> `az account show` före VM-kommandon; sätt rätt med `az account set --subscription "ev-lz3-ai (SE)"`.
> Fel subscription ger `AuthorizationFailed` (VM "finns inte"), inte token-fel.

> **Verifiera VM power-state (LB.60 — lita på tillståndet, inte på log-raden):**
> ```powershell
> az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[1].displayStatus" -o tsv
> ```
> En "deallocated"-rad i en körlogg är INTE bevis på att VM:en är nere. Verifiera alltid efter körning.
> OBS: `statuses[1]` (inte JMESPath-filter med `[?...]`) — `[`/`?`/`]` rivs sönder av az.cmd-wrappern
> på Windows (CMD-tecken). Index eller `-o json` undviker det.

> **Token dör var 4:e h (E.3):** hände TVÅ gånger 2026-06-15. `az login --scope
> https://management.core.windows.net//.default` före varje Blob/VM-arbetspass.

---

## 4. Miljöer (tre, korsa aldrig)

| Miljö | Sökväg | Bär | Senast verifierad |
|---|---|---|---|
| Global Python 3.11 | systemets `py -3.11` | verify_tool, validering, Step 6, build_r12, blob.py/upload_inputs (duckdb/pandas/openpyxl/xlwings/azure-libs) | 2026-06-15 |
| Business_Analytics venv | `C:\Projekt\Business_Analytics\.venv` | DW-extraktion (pyodbc), parquet-regenerering | 2026-06-12 |
| Pipeline venv (VM) | `~/bcg/cluster/.venv` på VM | Ray/statsmodels, modellsteg 1-4 (delas av alla 3 familjer) | 2026-06-12 |

> System-Python 3.10 på VM saknar Ray — använd pipeline-venv. Cluster har egen `.venv` (aktiverad,
> ej lånad); Site delar Cluster's. Detaljerad miljödisciplin: MASTER_PYTHON.

---

## 5. Vad som är färskt vs fruset (operativ sanning)

| Del | Tillstånd | Senast verifierad |
|---|---|---|
| Cluster + Site-elasticiteter | VÄXANDE (färsk) | 2026-06-11 |
| R12 volym & omsättning | VÄXANDE (`build_r12_for_model.py`) | 2026-06-11 |
| `transaction_data.parquet` (lokalt) | Regenererad t.o.m. 2026-04-30 (27,4M rader, 1144,5 MB) | 2026-06-11 |
| `transaction_data.parquet` (Blob) | I test-kontots `input/` (27,4M rader, 1144 MB; vaxande t.o.m. 2026-04-30) | 2026-06-16 |
| Cluster steg-5-routning | FRUSEN (2025) — FD.15 | 2026-06-11 |
| Väv-vikter | FRUSEN (2025) — FD.14 | 2026-06-11 |
| Bundle model-data-creation | VÄXANDE LÖST 2026-06-17 — 27 921 rader, datumspann → 2026-04-27 (FD.36, LB.73-76). Tyst tömnings-bugg i BCG:s process_bundles_with_fte spårad+fixad additivt | 2026-06-17 |
| Bundle-modell (runner) | KÖRD VÄXANDE 2026-06-20 — 125 KEY (matchar facit-ref), elasticitet median -0,21 (86% neg), via run_bundle_model.py. Alla 3 familjer nu körda växande (FD.36) | 2026-06-20 |
| Bundle-gren i Step6-väv | FRUSEN 2025 (FD.11) — separat från bundle-modellen | 2026-06-16 |
| Status-modell (run_id) | run_id = **datafönster** (`window_run_id(start,end)`), EJ körningsdatum — alla familjer/etapper för samma period delar EN statusfil. `finalize()` härleder run-nivån (pending=grå, hängande running stängs, vilande/klar ej tickande). succeed() föråldrad (städas) | 2026-06-22 |
| Diagnostiska sonder | `verify_tool/probes/` har nu SEX: chain_population, model_chain_validator, support_files_check (FD.36) + infrastructure_map, contract_integrity, after_chain_probe (2026-06-22, tokenfria statiska sonder mot motorn + efter-kedjan) | 2026-06-22 |

> De tre frusna låsen (LF.9) står på 2025-värden medvetet. Kärnsignalen för priskänslighet är färsk.
> Uppdateringsordning vid behov: FD.15 → FD.14 → FD.11 (kostnad vs påverkan).

---

## 6. Öppen IT-skuld som blockerar full autonomi (FAS T)

| Skuld | Effekt | Väntar på | Senast verifierad |
|---|---|---|---|
| Blob-dataroll (Storage Blob Data Contributor) till MI | kontonyckel-läge i stället för AAD; upload_inputs Jens-access-beroende (FD.29) | Owner (Kent) — ABAC-blockerad | 2026-06-15 |
| Pinnad/reproducerbar venv på VM | miljö ej deterministisk | eget arbete, ej IT | 2026-06-12 |
| Konto-spretighet (FD.35): status i prod-konto, facit i test-konto | förvirrat var sanningen bor; bygg 2-output kan hamna fel | eget beslut — lös FÖRE end-to-end-körningen | 2026-06-16 |

> När Blob-rollen ges: sätt `PRICINGMODEL_AUTH=aad`, ta bort nyckel-läget (skuld i `blob.py`-headern).
> Då slutar upload_inputs vara Jens-access-beroende och börjar köra på MI:n (FD.29) — envariabel-ändring.
> Övrig permanent IT-miljörestriktion (AppLocker, pip.exe, public-IP-policy) är hållbar kontext —
> bor i MASTER_PYTHON/MASTER_AZURE, inte här (den ändras inte per session).

---

## 7. Snubbeltrådar denna fas (kort — full lärdom i LESSONS_BCG)

- Token dör var 4:e h (E.3): `az login --scope https://management.core.windows.net//.default`.
- VM nås bara på kontorsnät/VPN. SSH-timeout = nätet, inte koden.
- VM:en har INGEN auto-shutdown (LB.68) — deallokera alltid manuellt. `deallocate`, inte `stop`.
- Storage dataplane kräver nyckel-läge (LB.67): `--auth-mode key` / `PRICINGMODEL_AUTH=key`. AAD ger
  tyst tomt utan dataroll — tomt svar ≠ "saknas".
- DW når INTE VM (LB.58) + data prep behöver inte VM:ens RAM (LB.65) → data prep körs LOKALT, output
  till Blob för överlevnad (LB.66). VM är till för Ray-modellstegens RAM, inget annat.
- `orchestration/` är enda sanning för motorfilerna; `workspace/`-kopior gitignoreras.
- ETAPPMODELLEN (operativ sanning): familjerna körs som SEPARATA etapper (komplext flöde, lång VM-tid,
  facit-validering + haverikontroll per familj), ofta vid olika tillfällen, mot SAMMA datafönster. En
  statusfil = ETT datafönster. Faserna speglar arbetet på den parquetens data: ny parquet → allt grått
  (pending); färdig etapp → grön; ej körda steg förblir grå. "Kör pågår, 1 av 7" är legitimt (inte
  spöke). Spöket = en running-fas som ALDRIG stängs (löst av finalize, LB.59).
- Regenerera `transaction_data.parquet` FÖRST vid ny period — annars filtreras ny data tyst bort
  (LB.50 / G7-klassen). `_inject_dates` i tools/replicate_dataprep.py patchar BÅDA datumlåsen
  (weekly_base-fönster + YearFlag-lista) — verifierat 2026-06-15.
- Redigera filer via skript (backup + UTF-8 utan BOM), inte genom att klistra Python i PowerShell-prompten.
- Före varm körning: `py -3.11 orchestration\dry_run_pipeline.py` (19 rör-kontroller — konto, parquet, facit, status, runners, app pekar rätt). Fångar fel kallt i stället för mitt i en flertimmars körning.
- Bundle model-data-creation kräver VM (Ray basket-build, dlmalloc-minnesvägg lokalt) + paket tqdm/ray i VM-venv (ensurepip först — venv saknar pip). BCG-koden anpassas vid INLÄSNING (encoding/kolumnnamn/datatyp), aldrig nedströmslogiken (LB.73-76).
- Bundle-MODELLEN (mapp 5) läser bundle_weekly_model_data_clinic_hospital.xlsx (ej CSV). Hela kedjan styrs av ETT datumfönster: constants.py BCG_START_DATE/BCG_END_DATE (env), används i regular_price/data_prep/model. Runnern injicerar dem via --start-date/--end-date. Alla merges i modellen är left/outer (tål växande, till skillnad från model-data-creation). InScope Mapping.xlsx = dött config-arv (regular_price läser den aldrig).

---

*Förvaltas av Jens Palmö (Senior Business Analyst). Färskvarufil — uppdateras vid varje sessionsslut
(KÄRNPRINCIPER §6.2). Ersätter tidigare spridd state i NEXT_SESSION + MASTER_AZURE + DRIFT. För vad
*nästa session ska göra* (kö, prioriteringar), se NEXT_SESSION.md — den ändras varje session och hålls
skild från denna mer stabila nulägesfil.*

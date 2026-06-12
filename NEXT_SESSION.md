# NEXT_SESSION — var vi står och vad som väntar

**Projekt:** `evbcgpricing` — Phase Z / FAS A (produktionssättning på Azure)
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Senast uppdaterad:** 2026-06-12 (efter att orchestrator-motorn byggts och bevisats på site-steget)

> Läs `KÄRNPRINCIPER.md`, `MASTER_AZURE.md` (§2.5 + AZ.6-10), `LESSONS_BCG.md` (LB.54-58),
> `FUTURE_DEVELOPMENT.md` (FD.16-17) och `orchestration/README.md` FÖRE start.

---

## 1. Vad som blev klart 2026-06-12 (Phase Z, första bygg- och körsessionen)

**Orchestrator-motorn är byggd och bevisad på site-modellsteget.** Den kör BCG:s `launcher.py`
(steg 1-4) på Azure-VM:en end-to-end, helt automatiserat, och **reproducerar facit bit-för-bit**:
6624 KEY, korr 1.000000, max_abs_diff 0 mot 2026-06-09 manuella körning. Kvitto i
`workspace/validation_receipts/`.

Levererade filer (i `orchestration/`):
- `shared/run_status.py` — statuskontrakt v1.0 (faser på familjenivå, hint-fält, tidtagning).
- `infrastructure/azure_vm.py` — VM/SSH-mekanik (start/deallocate/ssh/setsid-detach/scp/SshUnreachable).
- `infrastructure/blob.py` — Blob-I/O, kontonyckel-läge (ABAC-skuld dokumenterad).
- `runners/run_site_model.py` — flaggskeppsrunnern (preflight → detached launch → tolerant poll →
  verify mot facit → fetch → Blob → utfallsstyrd deallocate; `--check/--dry-run/--launch-test/--attach`).
- `validate_orchestrator_vs_facit.py` (repo-roten) — validerar output mot facit, skriver Excel-kvitto.

Tre felmoder bevisat hanterade **live**: seg kallstart (CZ.6-retry), SSH-detach-bugg (LB.54, fixad +
isolerat verifierad 1,4 s), skarp VPN-tunnelglapp mitt i körningen (LB.55 — svald av retry, körningen
överlevde och gick i mål).

**Utrett och avgjort:**
- **Prefect förkastat** för denna miljö (dashboard når ej kollegan utan publik IP/proxy; hemmabygget
  med Blob-statusfil är rätt). Återbesök om flera pipelines/utvecklare.
- **DW når INTE från VM:en** (LB.58, mätt `BLOCKED` mot `:1433`, `OUT_OK` mot github → DW-specifik
  IP-vitlistning). Extraktionen förblir lokal; arkitektur = lokal extraktion → Blob → VM (FD.17).

---

## 2. Nästa session — prioriterad ordning

### 2a. Cluster-runner (lägst risk, högst värde — gör först)
Copy-adapt av `run_site_model.py`. Cluster är site:s nära tvilling; ~5 konstanter byts:
`PHASE_KEY="cluster_model"`, `REMOTE_CODE=~/bcg/cluster/code`, `REMOTE_PYTHON` (cluster egen
`.venv/bin/python` — aktiverad, ej lånad), input-CSV-namnet, `EXPECTED_KEYS` (cluster-facit, ej 6624),
lokal output-mapp. Verifiera mot cluster-facit på samma sätt. **Rör inte** site-runnern.

### 2b. Lokala faser i sekvensen (site steg 5 + Step 6)
Tunna lokala wrappers som uppdaterar samma statusfil: site steg 5 (`py -3.11 code\...` + env-vars,
från Site-roten — LB.44/site-step5-regeln), Step 6 (`run_step6.py` finns, addera 3 statusanrop).
Dessa kör på Jens maskin (xlwings/COM kan ej köra på Linux-VM — principiellt).

### 2c. Sekvenserare över alla faser
En tunn meny/körare som kör vald fas (lokal eller VM) i rätt ordning och visar statusfilen. Faserna
finns redan i `run_status.py::default_pipeline`. Ingen generisk motor — bara en sekvens av de bevisade
runnersarna.

### 2d. Extraktions-fasen (FD.17 — egen tyngre session)
Lokal extraktion (`export_b4b_for_model.py` + parquet-regenerering + SQL-dataprep på behörig maskin) →
upload till Blob → VM läser Blob. **Kärnan Jens vill utveckla.** OBS den frysta-snapshot-kedjan:
regenerera `transaction_data.parquet` FÖRST (annars filtreras ny data tyst bort — LB.50/G7-klassen).

### 2e. Webbvy + skyddsnät
Läs-vy ovanpå Blob-statusfilen (kollega ser status, kan ej köra). VM-sidigt auto-shutdown (FD.16).

---

## 3. Driftnoteringar (så du inte snubblar)

- **Token dör var 4:e h** (E.3): `az login --scope https://management.core.windows.net//.default`.
- **Subscription-fällan** (LB.46): `az account show` före VM-kommandon; sätt `ev-lz3-ai (SE)`.
- **VM nås bara på kontorsnät/VPN** (privat IP `172.18.148.4`). SSH-timeout = nätet, inte koden.
- **PowerShell-quoting** (KÄRNPRINCIPER §5): inga `#`-kommentarer/backtick-fortsättningar i klistrade
  block; oavslutade citat hänger prompten.
- **Workspace-drift:** `orchestration/` är enda sanning för motorfilerna. `workspace/` ska tömmas/
  gitignoreras på dessa filer (dubbla kopior ställde till det 2026-06-12).
- **Kör orchestratorn:** placera filerna i `orchestration/{shared,infrastructure,runners}/`, kör
  `py -3.11 orchestration\runners\run_site_model.py --launch-test` (validera detach) → sedan skarpt.

---

## 4. Öppen teknisk skuld (FAS T — kräver IT)

- **Blob-dataroll till MI** (`evi-pricingmodel-mi-prod`) är ABAC-blockerad → kontonyckel-läge tills
  vidare. När rollen ges: `PRICINGMODEL_AUTH=aad`, ta bort nyckel-läget (skuld i `blob.py`-headern).
- Övrig FAS T-skuld oförändrad (se ROADMAP): pinnad venv, reproducerbar miljö.

---

*Skapad 2026-06-12 av Jens Palmö (utvecklare) med AI-rådgivaren, vid Phase Z-sessionens avslut.
Ersätter ev. tidigare NEXT_SESSION-innehåll som nu är inbakat i ROADMAP FAS A / FUTURE_DEVELOPMENT.*

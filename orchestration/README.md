# orchestration — Phase Z: kör BCG-prismodellen via Azure

**Projekt:** `evbcgpricing` / FAS A (produktionssättning)
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB), med AI-rådgivare
**Status:** Site-modellsteget bevisat end-to-end 2026-06-12 (6624 KEY, korr 1.000000 mot facit).

---

## Vad detta är

En tunn orchestrator som kör BCG:s modellsteg på Azure-VM:en (`bcg-poc-vm`) automatiserat, delar
status via Blob så en kollega kan följa körningen utan att röra VM/venv/SSH, och hämtar hem resultatet.
**BCG:s validerade kod rörs aldrig** — runnern anropar `launcher.py` exakt som Jens gör för hand, bara
automatiserat och med statusskrivning runtomkring.

Detta är **inte** en generisk pipeline-motor (Prefect/Dagster utreddes och förkastades — de når inte
kollegan utan publik IP/proxy och lägger till serverkomponenter, fel för Evidensias låsta miljö och
årsvisa körfrekvens). Det är **en runner per fas** efter Jens bevisade `run_step6.py`-mönster:
preflight → kör verbatim → verifiera output (R7) → tolerera kända fel.

---

## Filer

```
orchestration/
  shared/run_status.py            statuskontrakt v1.0 (RunStatus/Phase, JSON, tidtagning, hint-fält)
  infrastructure/azure_vm.py      VM/SSH-mekanik (start/deallocate/ssh/setsid-detach/scp/SshUnreachable)
  infrastructure/blob.py          Blob-I/O (status + output), AAD ELLER kontonyckel (PRICINGMODEL_AUTH=key)
  runners/run_site_model.py       FLAGGSKEPP: site steg 1-4 på VM, end-to-end
  (validate_orchestrator_vs_facit.py ligger i repo-roten — validerar output mot facit)
```

Importkedja: runners lägger `shared/` + `infrastructure/` på `sys.path` (parents[1]) — därför MÅSTE
en runner ligga i `orchestration/runners/`, annars hittar den inte `run_status`/`blob`.

---

## Köra (global Python 3.11, från repo-roten `C:\Projekt\BCG`)

```powershell
az login --scope https://management.core.windows.net//.default
py -3.11 orchestration\runners\run_site_model.py --check        # lokal preflight (rör inget)
py -3.11 orchestration\runners\run_site_model.py --dry-run      # visa exakt plan
py -3.11 orchestration\runners\run_site_model.py --launch-test  # validera detach-mekaniken (~2 min VM)
py -3.11 orchestration\runners\run_site_model.py                # skarp körning (~70 min)
py -3.11 orchestration\runners\run_site_model.py --attach       # återanslut till pågående körning
```

Förutsättning: på kontorsnät/VPN som ser `172.18.148.4` (VM saknar publik IP). Token-färsk (E.3).

Validera utfallet efteråt:
```powershell
py -3.11 validate_orchestrator_vs_facit.py    # KEY-mängd, elasticitet, p-värden + Excel-kvitto
```

---

## Designbeslut (varför det ser ut så här)

- **Faser på familjenivå** (Alternativ A): `launcher.py` kedjar redan de fem delstegen inom en familj
  och skriver `Finished <script>`-rader vi parsar. Vi rör inte koden för finare granularitet.
- **setsid-detach via launcher.sh** (LB.54): `&` räcker inte — SSH väntar på kanalen, Rays workers
  håller den öppen. Skriv skript på VM:en som äger sin egen redirect, starta detached, returnera via
  `echo started`. Verifierat isolerat (1,4 s släpp).
- **Tunneltolerans** (LB.55): observationsförlust ≠ pipelinefel. Retry + `ServerAlive`, `az` out-of-band
  som sanningsvittne, tre utfallslägen (success/pipeline_dead/lost).
- **Utfallsstyrd deallokering** (LB.56): deallokera bara vid bekräftat utfall; lämna VM:en köra vid
  observationsförlust; `--attach` återansluter; Ctrl+C dödar inte VM-jobbet.
- **Kontonyckel-läge** (skuld): MI:n är ABAC-blockerad från Blob-dataroll → Jens läser nyckeln som
  control-plane-Owner, nyckeln lever i processminnet. Byt till `DefaultAzureCredential` när dataroll
  finns (`PRICINGMODEL_AUTH=aad`). Se `blob.py`-headern + MASTER_AZURE §2.5.

## Kända benigna fel runnern tolererar

- **launcherns steg 5 (`data_prep_after_model_output.py`) failar alltid på Linux** — xlwings/Excel-COM
  kan ej köra utan Excel (LB.44). Steg 1-4 klart när `output_summary.xlsx` är färsk; steg 5 är en egen
  LOKAL fas.
- **feature_selection tvåpass** (LB.40/18-klassen): på ny KEY-uppsättning utan control_file kraschar
  pass 1 (genererar mall) by design → runnern relaunchar en gång (pass 2).

## Skuld & nästa steg

Se `NEXT_SESSION.md` (cluster-runner, lokala faser, sekvenserare, extraktion FD.17, webbvy, FD.16
auto-shutdown) och `FUTURE_DEVELOPMENT.md` Phase Z. Resurser i `MASTER_AZURE.md` §2.5.

---

*Skapad 2026-06-12 av Jens Palmö med AI-rådgivaren, vid Phase Z-sessionens avslut.*

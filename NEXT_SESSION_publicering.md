# NEXT_SESSION — Dashboard-publicering: beslut moln vs paketering

Du agerar som senior teknisk rådgivare för Jens Palmö (Senior Business Analyst).
Svenska för resonemang, engelska för kod. Sarkastisk humor OK. Utmana antaganden,
säg ifrån vid fel spår, lär ut medan du levererar men bryt inte leveransen för
pedagogik om Jens inte ber om det.

> Läs FÖRE start: denna fil i sin helhet, MASTER_AZURE_DEPLOY.md (spökkatalogen),
> DEPLOY_DASHBOARD.md (de tre publiceringsvägarna), KÄRNPRINCIPER.md (särskilt den
> nya "sök online före hypotes"-principen). Etapp B-arbetet ligger separat i
> NEXT_SESSION_etappB.md — detta dokument gäller ENBART publiceringen.

═══════════════════════════════════════════════════════════════════════════
## KÄRNBESLUTET SOM VÄNTAR (läs detta först)
═══════════════════════════════════════════════════════════════════════════

Dashboarden ska publiceras så att kollegor når den UTAN att Jens dator är på.
Efter 13 deployförsök till Azure App Service 2026-07-04/06 är läget:

- **Appen är BEVISAT felfri.** Lokal körning 2026-07-06 23:28: `GET / → 200`,
  BlobServiceClient ansluter i kontonyckel-läge, läser runstatus + fönstret
  `2022-07-01_2026-05-31.json`, 200 på varje endpoint. Koden och blob-kopplingen
  har ALDRIG varit problemet.
- **Molnvägen (App Service + Oryx) är olöst** — fastnar på två SAMVERKANDE spöken
  (D.22 + D.23) plus D.16 (cache), som var för sig är lösta men tillsammans bildar
  en knut (detaljer nedan).

**Rekommendation (Claude, 2026-07-06): stäng molnkapitlet, bygg paketering.**
Skäl längst ned under "Rekommendation framåt". Jens fattar beslutet utvilad —
gräv inte vidare i molnet innan beslutet är taget.

═══════════════════════════════════════════════════════════════════════════
## VAD SESSIONEN GJORDE (2026-07-04 + 2026-07-06 kväll)
═══════════════════════════════════════════════════════════════════════════

**Före deploy-jakten (allt PUSHAT, klart):**
- FD.33-B2c/d/e: dashboard-finslipning — What&why/How/Without synliga igen,
  null-medveten rendering (inga [fill in]), bilagor dedupe:ade till senaste
  körning, arkitekturkarta i About-fliken, footer-städ + Jens som utvecklare,
  step5-facit MÄTT (31.5 MB → 52.5 MB, +67 %), engelska tidsetiketter, "The big
  picture". Commits 4867493 → 47e0553 → 78d5bf7 → de30fd9 → 9501804.
- MASTER_AZURE_DEPLOY.md skapad som spökkatalog (Master-Bibliotek, pushad).

**Deploy-jakten (13 försök, olöst):**
- Skapade grindat idempotent deploy-skript (tools/deploy_dashboard.ps1, v1.1–1.6).
- Uttömde ACR-vägen (D.1) → valde kod-deploy/zip.
- Byggde spökkatalogen D.1–D.23 (nedan) — varje post uppmätt.
- Sökte online (MS-dok + azureossd + community) → bekräftade D.20/D.22/D.23 mot
  Microsofts egna källor. Fångade ny KÄRNPRINCIP: sök online före hypotes.
- Bevisade appen lokalt (fungerar felfritt).

═══════════════════════════════════════════════════════════════════════════
## SPÖKKATALOGEN — vad vi testat och lärde (D.1–D.23)
═══════════════════════════════════════════════════════════════════════════
Full text med belägg i MASTER_AZURE_DEPLOY.md. Kortform:

| # | Spöke | Status |
|---|---|---|
| D.1 | ContainerRegistry-provider ej registrerad (subscription-scope, RG-PIM räcker ej) | ACR-väg övergiven |
| D.2 | RBAC-nekad läsning maskeras som NotFound | Regel: mät rollen |
| D.3 | PIM-aktivering dör mitt i pass (tidsboxad) | Regel: re-mät per block |
| D.4 | PowerShell stoppar ej på az-fel → kaskad | Löst: grindat skript |
| D.5 | Container-app ↔ kod-app kan ej flippas | Löst: recreate |
| D.6 | Dörren låses före nyckeln (EasyAuth före secrets) | Regel + hälsokoll-larm |
| D.7 | Kod-deploy: SCM_DO_BUILD + startup + ingen WEBSITES_PORT | Löst |
| D.8 | --deployment-container-image-name deprecated | Undvik |
| D.9 | az-login promptar subscription interaktivt | Grind: account show |
| D.10 | 503 på container utan image = normalläge | Kontext |
| D.11 | Polling på tillstånd man ej rår över = evig loop | Max-varv |
| D.12 | EAP=Stop + 2>$null dödar förväntade sond-fel (PS 5.1) | Löst: EAP Continue |
| D.13 | az webapp delete raderar tom plan by default | --keep-empty-plan |
| D.14 | cmd-parsern dödar JMESPath-parenteser i --query | Parentesfri query |
| D.15 | Compress-Archive skriver backslash → Linux ser inga kataloger | py -m zipfile |
| D.16 | Överhoppat bygge → GAMLA artefakter spökar ("Build 0s"/samma OperationID) | config-zip; **ÅTERKOM** |
| D.17 | Klient-timeout = observationsförlust, ej byggdöd | Mät server-side |
| D.18 | Krasch-loop stjäl byggets CPU (B1, 1 kärna) | webapp stop före deploy |
| D.19 | Stop-före-deploy låser deploy-pollern (Starting evigt) | Kort timeout + D.17 |
| D.20 | Nested träd via Oryx tar-extrakt opålitligt | FLATTEN till zip-rot |
| D.21 | az-subkommandon driftar mellan CLI-versioner | Håll till kärnkommandon |
| D.22 | Opinnad gunicorn ≥22 ej cwd på sys.path; imagens gunicorn skuggar pinnad | startup.sh; **DELVIS** |
| D.23 | startup.sh skapad på Windows med CRLF → Linux läser /bin/sh\r → "not found" | LF-fix; **DELVIS** |

**Den olösta knuten (D.22 + D.23 + D.16 tillsammans):**
1. startup.sh med explicit chdir/PYTHONPATH löser D.22 (gunicorn hittar app).
2. MEN filen skapad på Windows = CRLF → D.23 → "not found" innan den ens kör.
3. Skrev om filen med garanterat LF (hexdump: 0 CR-bytes, verifierat i BÅDE
   container-loggen och på Jens maskin via ReadAllBytes).
4. MEN sista deployen konsumerades ALDRIG — `Build Operation ID: a885ccb64c1a662f`
   och extraktkatalog `/tmp/8dedba02144619c` var IDENTISKA med föregående deploy
   → D.16: Oryx serverade den gamla CRLF-artefakten trots ny zip.

Nästa tekniska steg OM molnvägen återupptas (EJ rekommenderat): bryt artefakt-cachen
(töm wwwroot via Kudu, eller WEBSITE_RUN_FROM_PACKAGE-växling, eller ändra en byte i
en deployad fil så hash skiljer) SÅ att den LF-rena zip:en faktiskt extraheras.
Verifiera sedan att loggen visar `App command line is a shell script, will execute
this script as startup script` — den raden har ALDRIG synts än, och är själva kvittot
på att startup.sh körs. Utan den raden vet vi inget.

═══════════════════════════════════════════════════════════════════════════
## REKOMMENDATION FRAMÅT (Claude) — och varför
═══════════════════════════════════════════════════════════════════════════

**Rekommendation: bygg PAKETERING (hemsida_automation-mönstret) som permanent
lösning. Stäng molnet som "löst i teorin, dokumenterat, parkerat".**

**Varför — omdefiniera "robust":** robust = få rörliga delar, inga dolda
beroenden, reproducerbar. Mätt så är App Service/Oryx den MINST robusta vägen för
detta fall: beror på Oryx tar-extrakt till flyktig /tmp, Windows-radslut, artefakt-
cache, kontonyckel i molnet, PIM som dör. 23 uppmätta spöken ÄR beviset på skörheten.
En "robust lösning" på den grunden är en självmotsägelse.

**De två faktiskt robusta vägarna (båda med appen som bevisat fungerar):**

1. **Paketering** (REKOMMENDERAD permanent lösning, ~30 min):
   `build_dashboard_dist.ps1` (redan skriven, i outputs — ej nedladdad än).
   Embeddable Python + pip-target + start.bat, exakt hemsida_automation-mönstret
   Jens redan förvaltar. Kollegan får en mapp, dubbelklickar, dashboarden öppnas.
   Noll Azure, noll spöken.
   KRITISKT: (a) start.bat måste ha LF-radslut? NEJ — start.bat körs av Windows
   cmd.exe, där CRLF är korrekt; det är bara Linux-startup.sh som krävde LF. (b)
   Nyckeln bör sättas som miljövariabel på mottagarens dator, INTE klartext i delad
   mapp. (c) Verifiera build_dashboard_dist.ps1 mot faktisk repo-struktur; app.py
   är körbar direkt (rad 562: __main__ + app.run, bekräftat).

2. **Schemaläggaren** (fallback för Jens egen åtkomst, 5 min):
   DEPLOY_DASHBOARD.md alt. A. pythonw startar appen vid inloggning på 127.0.0.1.
   Robust för Jens men bunden till hans maskin. Redan kört och fungerar 2026-07-06.

**Varför INTE fortsätta molnet nu:** om nästa molnfix lyckas har Jens en dashboard
på den sköraste vägen → tillbaka i spökjakt vid nästa uppdatering. Om den misslyckas
= spöke 24. Ingen utgång tjänar Jens. Paketering tjänar Jens.

**OM Jens ändå vill ha molnet** (fullt legitimt — publik URL + Entra-inloggning är
det ursprungliga FD.32-syftet): då är rätt väg troligen INTE mer Oryx-brottning utan
GitHub Actions-deploy (build i ren Ubuntu-miljö, LF bevaras, ingen artefakt-cache,
ingen lokal zip). Det kringgår D.15/D.16/D.20/D.23 på en gång. Kräver dock att
repo-URL exponeras för en workflow — väg mot Jens önskan att hålla repot utanför
dokumentationen. Diskutera FÖRE bygge.

═══════════════════════════════════════════════════════════════════════════
## OGITAT — samla ihop när beslutet är taget (git i BÅDA repona)
═══════════════════════════════════════════════════════════════════════════
Inget nedan är committat. Alla filer i /mnt/user-data/outputs (ladda ner):

**BCG-repot (evbcgpricing):**
- `startup.sh` (LF-ren, D.23-fix) → repo-rot, OM molnvägen behålls som referens
- `tools/deploy_dashboard.ps1` (v1.6, grindat/idempotent, D.1–D.21-fixar)
- `requirements.txt` (gunicorn==20.1.0 pinnad, kommentar om D.22)
- `build_dashboard_dist.ps1` → tools/ (paketering — permanent lösning)
- BB.14-rad → BACKLOG.md (.bak-skräp i deploy.zip, löstes av flatten-layout)

**Master-Bibliotek:**
- `MASTER_AZURE_DEPLOY.md` — D.1–D.23 + Microsoft-källor. Verifiera att D.23 (CRLF)
  är formellt inskriven + notera D.16-återkomsten (cache-knuten) som varning.
- `SOK_ONLINE_PRINCIP.md` → klistras in i KÄRNPRINCIPER.md.

**Dokument-klistringar (om ej redan gjorda):**
- DOC_UPPDATERINGAR_2026-07-03.md → FUTURE_DEV/LESSONS/BACKLOG/STATE.

═══════════════════════════════════════════════════════════════════════════
## SESSIONENS METALÄRDOM
═══════════════════════════════════════════════════════════════════════════
D.23 (CRLF) är SAMMA klass som er befintliga regel "PowerShell .ps1 måste vara ren
ASCII" — Windows-radslut/kodning som bryter i en icke-Windows-tolk. Borde kopplats
internt efter FÖRSTA "not found", inte efter tolfte försöket. Dubbel lärdom:
(1) sök det RÅA felet direkt (nu i KÄRNPRINCIPER), (2) korskoppla nya spöken mot
BEFINTLIGA lessons innan de behandlas som nya. Kopplingen fanns redan i era filer.

**Kvar i projektet i övrigt:** FD.33 Etapp B-cutover (7 filer, se
NEXT_SESSION_etappB.md), FD.40 revenue-coverage, facit-fönstret i run-väljaren.

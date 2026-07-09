# NEXT_SESSION — Dashboard-publicering v2: sista mätpunkten, sedan stängning

Du agerar som senior teknisk rådgivare för Jens Palmö (Senior Business Analyst).
Svenska för resonemang, engelska för kod. Sarkastisk humor OK. Utmana antaganden,
säg ifrån vid fel spår, lär ut medan du levererar men bryt inte leveransen för
pedagogik om Jens inte ber om det.

> Läs FÖRE start: denna fil i sin helhet, MASTER_AZURE_DEPLOY.md (spökkatalogen
> D.1–D.23), KÄRNPRINCIPER.md, SOK_ONLINE_PRINCIP.md. Etapp B ligger separat i
> NEXT_SESSION.md (FD.33) och påverkas INTE av detta spår.
> Ersätter NEXT_SESSION_publicering.md (v1, 2026-07-06) i sin helhet.

═══════════════════════════════════════════════════════════════════════════
## KÄRNLÄGET (läs detta först)
═══════════════════════════════════════════════════════════════════════════

**Genombrott 2026-07-07 (försök 14–15): D.16 är BRUTEN och FÖRSTÅDD.**
Kvällens config-zip-deploy körde det FÖRSTA riktiga Oryx-bygget av vår kod
någonsin (99 s, "Errors (0)", nytt Build Operation ID `e20bc0f40ef35ca3`,
nytt extrakt `/tmp/8dedc6df1961672`, containern bootar det). Deploy-kedjan
zip → bygge → tarball → container är därmed BEVISAD hela vägen.

**Vad som återstår är TVÅ mätbara frågor — inte spöken:**

1. **Varför gunicorn 26.0.0 trots pin?** Kvällens boot körde gunicorn 26.0.0
   (inte pinnade 20.1.0) + `ModuleNotFoundError: No module named 'app'`.
   Trolig mekanik: Oryx byggde på wwwroots GAMLA requirements.txt från
   2026-07-04 (opinnad) — den överlevde eftersom rivningen av wwwroot aldrig
   gick igenom och zip-kopiering hoppar filer med matchande tidsstämpel.
   AVGÖRS av F2/F3 i morgonblocket (tarballens gunicorn-version + wwwroots
   requirements-innehåll).
2. **Kör /home/startup.sh eller inte?** Filen BEVISAT på plats (VFS GET ekar
   innehållet) men wrappern säger `not found` — enda Linux-scenariot där en
   existerande skriptfil ger "not found" är shebang-tolk som inte hittas,
   dvs. `/bin/sh\r` = CRLF. PUT-rundan gick via Windows-textlager
   (Get-Content → WriteAllText → az rest) och har sannolikt CRLF:at LF-filen.
   AVGÖRS av F1 (`cat -A` visar ^M okulärt).

**Båda frågorna konvergerar i EN mätpunkt: Kudu Bash-konsolen** (Portalen →
evbcg-dashboard → Advanced Tools → Go → Bash). Noll Windows-lager, noll
citatkrig. Kudus /api/command visade sig vara skallöst (`&&`, `<`, `>` blir
bokstavliga argument) och PS 5.1→JSON→inget-skal gav tre felciterade
kommandon i rad — konsolen är rätt verktyg, inte fler az rest-försök.

**Beslutsläge:** även om morgonblocket ger grönt förblir Azure DevOps den
permanenta publiceringsvägen (IT sätter upp; pipelinen gör kvällens hela
läxa — rent tillstånd + garanterat bygge — by design varje körning). Den
manuella kedjan dokumenteras i mastern som "fungerar, med tre icke-uppenbara
krav" (ENABLE_ORYX_BUILD, ZipDeploy inte OneDeploy, startup-fil under /home).

═══════════════════════════════════════════════════════════════════════════
## MORGONBLOCKET — exakt sekvens (~15 min)
═══════════════════════════════════════════════════════════════════════════

### Steg 0 — token + subscription (CA-policyn dödar token efter 14400 s = 4 h)
```powershell
az login --scope https://management.core.windows.net//.default
az account show --query name -o tsv    # MÅSTE: ev-lz3-ai (SE)
```

### Steg 1 — Kudu Bash: mät + laga (Portalen → Advanced Tools → Go → Bash)
```bash
# F1: Bär /home/startup.sh CR? (^M i radslut = CRLF-korruption bevisad)
cat -A /home/startup.sh | head -3

# Laga på plats om ^M syns (server-side, inga Windows-lager):
tr -d '\r' < /home/startup.sh > /tmp/s && mv /tmp/s /home/startup.sh && chmod +x /home/startup.sh && wc -c /home/startup.sh
# facit: 649 byte (stagerns uppmätta LF-storlek)

# F2: Vilken gunicorn ligger i kvällens FÄRSKA tarball? (26.0.0-gåtans dom)
tar -tzf /home/site/wwwroot/output.tar.gz | grep -i "gunicorn-2" | head -3

# F3: Vilken requirements byggde Oryx på?
cat /home/site/wwwroot/requirements.txt
```

**Tolkning:**
- F1 med `^M` → CRLF via Windows-rundresan bevisad; tr-fixen löser. (Ny
  master-regel: LF-filer lagas/skrivs server-side, aldrig via
  Windows-textlager. VFS GET kan INTE avslöja \r — cat -A kan.)
- F2 visar `gunicorn-26.x` och/eller F3 visar requirements UTAN
  `gunicorn==20.1.0`/`duckdb` → Oryx byggde på 04-juli-resterna. Åtgärd i
  samma konsol + omdeploy (steg 2).
- F2 visar `gunicorn-20.1.0` → miljön är redan rätt; endast F1-fixen +
  restart behövs (hoppa steg 2).

### Steg 2 — ENDAST om F2/F3 visade gammalt bygg-underlag
```bash
# I Kudu Bash: riv gamla generationens rester (ny deploy återskapar allt)
rm -f /home/site/wwwroot/output.tar.zst /home/site/wwwroot/requirements.txt /home/site/wwwroot/hostingstart.html
ls -la /home/site/wwwroot
```
```powershell
# Lokalt: omdeploy på den bevisade vägen (ZipDeploy + Oryx-flaggorna står redan)
cd C:\Projekt\BCG
py -3.11 tools\webapp_deploy_probe.py            # ska vara CLEAN
py -3.11 tools\stage_webapp.py                   # färsk deploy.zip
az webapp deployment source config-zip -g ev-openai-swce-rg-test -n evbcg-dashboard --src C:\Projekt\BCG\deploy.zip
# Förväntat: "Building the app..." i ~90-120 s (duckdb-wheelen), INTE "0(s)"
```

### Steg 3 — restart + avläsning (OBS: loggen är UTC, du är UTC+2)
```powershell
$RG="ev-openai-swce-rg-test"; $APP="evbcg-dashboard"
az webapp config show -g $RG -n $APP --query appCommandLine -o tsv   # ska vara /home/startup.sh
az webapp restart -g $RG -n $APP
Start-Sleep 100
try { $c=(Invoke-WebRequest "https://$APP.azurewebsites.net" -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0).StatusCode } catch { $c=[int]$_.Exception.Response.StatusCode }; "ping: HTTP $c"
$zip="$env:TEMP\evbcg_logs.zip"; Remove-Item $zip -Force -EA SilentlyContinue
az webapp log download -g $RG -n $APP --log-file $zip
py -3.11 C:\Projekt\BCG\tools\read_app_logs.py --zip $zip --since 2026-07-08T0   # justera UTC-timmen!
```

**Läskedja (i denna ordning):**
1. `Checking of /home/startup.sh is a file` → `App command line is a file on disk`
2. `App command line is a shell script, will execute this script as startup
   script` — KVITTORADEN (aldrig sedd under 15 försök; källbelagd ur MS Q&A)
3. `[startup.sh] running from /tmp/8ded...` — vår egen echo = VÅRT skript kör
4. `Starting gunicorn 20.1.0` — pinnen regerar (26.0.0 = fel underlag kvar)
5. `Booting worker` → antingen `Listening`-läge eller Traceback

**Ping 401/302 = MÅLET** (appen står bakom EasyAuth-dörren) → öppna i
webbläsare, logga in med Entra, verifiera att dashboarden läser
maj-fönstret från Blob. En Traceback efter Booting worker är appens FÖRSTA
egna ord i molnet — vanlig Python-felsökning på utpekad rad, inte spökjakt.

### Steg 4 — vid GRÖNT: efter-succé-checklista
- [ ] Webbläsartest: Entra-login → dashboard → välj fönster 2022-07-01_2026-05-31
      → status + kvitton renderar
- [ ] Kända begränsningar gäller (DEPLOY_DASHBOARD.md §skulder): statiska
      facit-kvittolänkar 404:ar i molnet (backlog, ej blockerare);
      kontonyckel som app setting tills Kents dataroll (FD.29)
- [ ] `/home/startup.sh` är PERSISTENT infra (överlever deployer, /home är
      beständig) — skapad en gång, DevOps-pipelinen behöver aldrig röra den
- [ ] Dokumentera segersekvensen → mastern (se DOKUMENTATION nedan)
- [ ] RÖR INGET MER — låt den stå, städning är eget pass

### Vid RÖTT efter steg 3 (t.ex. kvittoraden syns men appen kraschar oväntat):
kapitlet stängs ändå — mekaniken är nu FÖRSTÅDD, DevOps-pipelinen bygger på
exakt samma bevisade sekvens i ren miljö. Ingen mer manuell iteration.

═══════════════════════════════════════════════════════════════════════════
## VAD 2026-07-07-SESSIONEN GJORDE (för STATE/LESSONS-klistring)
═══════════════════════════════════════════════════════════════════════════

**Byggt (mät → paketera → transportera-kedjan, plattforms-kompatibel):**
- `tools/webapp_deploy_probe.py` — P.5-sond: AST-baserad transitiv
  import-closure från app.py, requirements-täckning, verktygskoll
  (az --clean-stöd), Azure-state (settings-NAMN, aldrig värden). Skriver
  staging-manifest + Excel-kvitto (validation_receipts).
- `tools/stage_webapp.py` v1.1.1 — manifest-DRIVEN staging (sonden äger
  closuren, stagern konsumerar). LF-verifierad startup.sh, cachebust,
  zip-grindar. (v1.0:s regex-grind pensionerad: 3 falska positiva + blind
  för transitiva beroenden.)
- `tools/deploy_dashboard_final.ps1` v1.8 — grindad kedja sond→stage→deploy.
- `tools/read_app_logs.py` — läser Kudu-logg-zippen I MINNET (zippen är
  känt icke-standard sedan 2017; Expand-Archive/PS 5.1 kraschar på
  kolon-namn i trace-poster).
- `azure-pipelines.yml` (repo-rot, INERT) — DevOps-pipelinen, kör samma
  sond+stage-moduler; aktiveras när IT landat (aktiveringssteg i filhuvudet).
- `requirements.txt` — duckdb tillagd (sonden fann lazy import
  run_status.py:94 — osynlig vid boot, live vid runtime).

**Sondens fynd:** closuren är FEM moduler (app, blob, info_config,
run_status, story_config) + templates/. `info_config` och `run_status`
saknades i ALLA 13 tidigare deployer — två tysta bootkrascher låg bakom
startup-spöket. duckdb saknades i requirements (guaranteed ModuleNotFound
i molnet, funkar lokalt).

**Mekaniken som förklarade alla 14 försök (lagerkakan):**
wwwroot under Oryx är ett ARKIV, inte en filyta: bygget lämnar bara
`output.tar.gz` + `oryx-manifest.toml`; containern extraherar tarballen
till /tmp och kör DEN — råa filer bredvid ignoreras. Bevisfoto (VFS-listning)
visade två generationer sida vid sida: output.tar.zst + requirements.txt
från 07-04 bredvid 07-07:s tarball+manifest. `az webapp deploy` (OneDeploy)
triggade ALDRIG Oryx (ENABLE_ORYX_BUILD saknades; "Build 0(s)" =
signaturen); `az webapp deployment source config-zip` (ZipDeploy) +
ENABLE_ORYX_BUILD=true + SCM_DO_BUILD=true gav första riktiga bygget.
Källor: MS deploy-zip-dok (timestamp-skip, build-automation-flaggan),
MS Q&A "Oryx not being triggered" (exakt vårt fall), azureossd (venv-krav,
OneDeploy vs Oryx), Blimped-bloggen (ENABLE_ORYX_BUILD-fixen),
MS Q&A "Startup.sh not found" (startup-fil under /home + kvittoradens
exakta lydelse).

**Kvällens egna fel (ärligt, för lärdomskatalogen):** relativ startup-file
skrev över uppmätt absolutväg (A.9b-brott); f-string med backslash (3.12-
syntax mot 3.11); JSON-escape → riktig CR i serverkommandot (två varv);
UTC-filter mot lokal klocka. Mönster: tre felciterade kommandon i rad =
BYT VERKTYG (→ Kudu Bash), iterera inte citatlager.

═══════════════════════════════════════════════════════════════════════════
## SPÖKKATALOG-TILLÄGG → MASTER_AZURE_DEPLOY (verifiera nr mot mastern, additivt)
═══════════════════════════════════════════════════════════════════════════

| # (prel.) | Spöke | Regel |
|---|---|---|
| D.24 | wwwroot under Oryx = arkiv (tarball+manifest), inte filyta. Startup-filvägar under wwwroot kan ALDRIG hittas — de sväljs av tarballen | Startup-fil bor under /home (persistent, utanför wwwroot) eller ges som kommandosträng |
| D.25 | OneDeploy (`az webapp deploy`) triggar inte Oryx pålitligt; "Build 0(s)" = inget bygge skedde | Python-koddeployer: `config-zip` (ZipDeploy) + BÅDA flaggorna `SCM_DO_BUILD_DURING_DEPLOYMENT=true` OCH `ENABLE_ORYX_BUILD=true` |
| D.26 | Zip-kopiering hoppar filer med matchande tidsstämpel → gamla wwwroot-filer (t.ex. requirements.txt) överlever och blir BYGG-underlag | Vid generationsskifte: riv gamla filer i Kudu Bash före deploy |
| D.27 | LF-fil som rundreser Windows-textlager (Get-Content/WriteAllText/az rest-body) CRLF:as tyst; VFS GET kan inte visa \r | LF-filer lagas/verifieras server-side: `cat -A` (visar ^M), `tr -d '\r'`. Fil-existens + "not found" = shebang-tolken `/bin/sh\r` |
| D.28 | Kudu `/api/command` kör UTAN skal — `&&`, `;`, `<`, `>` blir bokstavliga argument | Skalkedjor körs i Kudu Bash-konsolen, inte via az rest |
| D.29 | `az webapp log download`-zippen är icke-standard (kolon-namn i trace-poster) → Expand-Archive/PS 5.1 kraschar | Läs docker-loggar I MINNET (tools/read_app_logs.py); extrahera aldrig |
| — | AADSTS70043 med "maximum allowed lifetime 14400" = CA-policyn själv bekräftar 4h-token (LB.88 nu KÄLLBELAGD) | az login före varje block; pollning över timgräns dör i observation, inte i bygge |
| — | Deploy-pollern ljuger tre sätt: "Build 0(s)" (hoppat bygge), sena landningar (gårdagens deploy dyker upp med nytt ID timmar senare), klient-timeout ≠ byggdöd (D.17) | Domen står ALLTID i serverloggen + Build Operation ID, aldrig i pollern |
| — | All App Service-logg är UTC; lokal klocka UTC+2 | --since-filter i UTC, alltid |

═══════════════════════════════════════════════════════════════════════════
## DEVOPS-SPÅRET (permanent väg — löper parallellt, blockerar inget)
═══════════════════════════════════════════════════════════════════════════

- **IT-asken (skicka om ej gjort):** (1) status på Azure DevOps-uppsättningen,
  (2) enrads-registrering av `Microsoft.ContainerRegistry`-providern
  (subscription-scope) — öppnar container-vägen för framtiden, kostar IT
  två minuter.
- `azure-pipelines.yml` ligger inert i repo-roten. Aktivering när IT landat:
  service connection (Workload Identity Federation, inga secrets) → klistra
  namnet i SERVICE_CONNECTION → Pipelines → Existing YAML. Pipelinen kör
  sond + stage på ubuntu-agent (LF nativt, färsk artefakt varje gång) —
  D.15/16/20/23/26/27 döda by design.
- `/home/startup.sh` är engångs-infra som överlever pipelinens deployer.
- Microsofts egen OSS-supportblogg avråder zip-utan-Oryx för Python och
  pekar på DevOps/Actions som vägarna som korrekt bygger+aktiverar miljön —
  referensen in i CI/CD-kapitlet.

═══════════════════════════════════════════════════════════════════════════
## OGITAT — committa när morgonblocket är avläst (git i BÅDA repona)
═══════════════════════════════════════════════════════════════════════════

**BCG-repot (evbcgpricing):**
- `tools/webapp_deploy_probe.py`, `tools/stage_webapp.py` (v1.1.1),
  `tools/deploy_dashboard_final.ps1` (v1.8), `tools/read_app_logs.py`
- `requirements.txt` (duckdb + gunicorn-pin, kommenterad)
- `azure-pipelines.yml` (inert)
- `.gitignore`: + `workspace/deploy_staging/`, `workspace/deploy_staging_manifest.json`
  (genererade; deploy.zip redan ignorerad)
- BACKLOG.md: **BB.15** — bryt ut blob.py:s läs-sida till ren
  `data_access`-modul så webapp-payloaden slipper släpa pipeline-beroenden
  (duckdb kom in via run_status; "en modul = ett ansvar", plattformsvisionen)
- Äldre ogitat från v1 kvarstår: `SOK_ONLINE_PRINCIP.md`-klistring,
  DOC_UPPDATERINGAR_2026-07-03 om ej gjorda

**Master-Bibliotek:**
- MASTER_AZURE_DEPLOY.md: spöktilläggen ovan (verifiera numrering, additivt)
  + kapitel "Lagerkakan — wwwroot under Oryx" + kvittoradens exakta lydelse
  + segersekvensen (eller stängningssekvensen) från morgonblocket

═══════════════════════════════════════════════════════════════════════════
## DOKUMENTATION VÄNTAR (görs SIST, samlat pass — ligger även i Claude-minnet)
═══════════════════════════════════════════════════════════════════════════

1. Ny KÄRNPRINCIP: **"Plattforms-kompatibelt, inte plattforms-komplett"** —
   varje projektbeslut valideras mot plattformsvisionen (Azure AI Platform
   Vision.md) som RIKTNING, inte byggorder; bygg det minsta som skalar.
2. SOK_ONLINE_PRINCIP.md → in i konsoliderade KÄRNPRINCIPER (bevisad i
   skarpt läge 07-07: varje genombrott kom från rå-fel-sökning + systematisk
   loggläsning, inte härledning).
3. MASTER_AZURE_DEPLOY: CI/CD-kapitel som dokumenterar MÖNSTRET (bygge i
   ren Linux-miljö → artefakt → deploy) med Azure DevOps och GitHub Actions
   som utbytbara implementationer + formell stängning av manuella
   Oryx-zip-vägen med utfall och krav.
4. Lärdomsflytt per §6.6: kvällens fel-mönster ("tre felciterade = byt
   verktyg", UTC-disciplin, LF-server-side-regeln) → rätt masterfil.

═══════════════════════════════════════════════════════════════════════════
## SNUBBELTRÅDAR DENNA SESSION
═══════════════════════════════════════════════════════════════════════════
- Token 4h (LB.88, nu CA-källbelagd): `az login` FÖRE morgonblocket och före
  varje nytt tungt block. PIM kan behöva re-aktiveras.
- Kudu Bash för allt server-side (mät/laga/riv) — az rest /api/command är
  skallöst, PS 5.1-JSON-citat är ett träsk. Tre felciterade i rad = stopp.
- UTC i alla --since-filter (lokal tid −2 h).
- Rör INTE Etapp B-filerna i detta pass — fyra-kartors-regeln kräver egen
  fokuserad commit (NEXT_SESSION.md).
- Ingen VM inblandad i detta spår — men om VM startas av annat skäl:
  deallocate efteråt (LB.68).
- Vid grönt: fira kort, committa OGITAT, dokumentera. Vid rött: stäng
  kapitlet med belägg, DevOps-spåret står redo. INGEN utgång motiverar
  fler manuella iterationer efter morgonblocket.

---
*v2 skriven 2026-07-08 00:3x efter genombrottspasset. Ersätter v1 (2026-07-06).
Utvecklare: Jens Palmö. Sessionens facit: D.16 bruten och förstådd på försök
14–15; två mätbara frågor kvar; alla trådar konvergerar i Kudu Bash-konsolen.*

> **STÄNGT GRÖNT 2026-07-09/10 (morgonblocket kört sent):** F2 friade bygget
> (färska tarballen bär gunicorn-20.1.0). F1:s rot var ADRESS, inte CRLF: VFS-API:t
> rotar på /home → PUT skapade /home/home/startup.sh, GET ekade från samma
> feladress = falskt bevis. Fix: tar -xzf ur färska tarballen → /home/startup.sh
> (649 B, LF). Bov 2: runtime-extraktorn tar output.tar.zst FÖRE .gz →
> 07-04-generationen bootades varje gång; riven (zst/requirements/hostingstart).
> Därefter FULL kvittokedja: file on disk → gz-extrakt → egen echo →
> gunicorn 20.1.0 → Listening → HTTP 200. MEN EasyAuth saknades (D.5: dog med
> appen 07-04; appregistrering = tenant-rättighet, utanför RBAC/PIM) → appen
> STOPPAD (verifierat Stopped + 403). REGEL: startas EJ förrän auth sitter.
> IT-ask 3 rader: DevOps-status · ContainerRegistry-provider · appregistrering
> bcg-dashboard-auth + Require authentication på evbcg-dashboard.
> /home/home rivet. Toolchain committad f776b16. Kvar: dokumentationspasset
> (skördelistan hos AI-rådgivaren) + IT-asken.
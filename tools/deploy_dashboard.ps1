# deploy_dashboard.ps1 -- BCG dashboard till Azure App Service (kod-deploy, ingen ACR)
# =====================================================================================
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Monster: MASTER_AZURE_DEPLOY (spok-katalogen D.1-D.21 + diagnos-skolan i dess 3).
# D.13-varning: 'az webapp delete' raderar AVEN tom plan by default -- anvand
# --keep-empty-plan vid recreate pa delad plan (darfor "forsvann" planen 2026-07-04). Skriven som GRINDAT skript
# eftersom PowerShell INTE stoppar pa az-fel: utan grindar kaskadar ett rotfel till
# tio foljdfel (uppmatt tva ganger 2026-07-04). Varje az-steg mats och grindas.
# Idempotent: kan koras om fran borjan efter varje stopp -- befintligt hoppas over.
#
# KORNING (PowerShell, var som helst):
#   powershell -ExecutionPolicy Bypass -File C:\Projekt\BCG\tools\deploy_dashboard.ps1
#      -> fas 1: subscription/PIM-matning, plan, app, settings. Stannar vid AUTH-PAUS.
#   ... aktivera auth i Portalen (instruktion skrivs ut) ...
#   powershell -ExecutionPolicy Bypass -File C:\Projekt\BCG\tools\deploy_dashboard.ps1 -Deploy
#      -> fas 2: zip + deploy (Oryx bygger) + halsokoll med auth-larm.
param([switch]$Deploy)
# D.12: EAP=Stop + native stderr-redirect (2>$null) gor i PS 5.1 att FORVANTADE
# sond-fel ("finns resursen?") blir terminerande NativeCommandError -- sonden
# dodar skriptet. Darfor Continue har; ALLT stoppande ags av Gate/throw explicit.
$ErrorActionPreference = "Continue"

$RG      = "ev-openai-swce-rg-test"
$PLAN    = "bcg-dashboard-plan"
$APP     = "evbcg-dashboard"
$STORAGE = "evbcgpricinginput"
$REPO    = "C:\Projekt\BCG"

function Gate([string]$msg) {
    if ($LASTEXITCODE -ne 0) {
        throw "STOPP vid: $msg (se az-felet ovan). Atgarda och kor om -- skriptet ar idempotent."
    }
}
function Say([string]$m) { Write-Host "[deploy] $m" }

# --- Steg 0: subscription + PIM (D.2: RBAC-nekad lasning maskeras som NotFound) -------
$sub = az account show --query name -o tsv; Gate "az account show (ar du inloggad?)"
if ($sub -ne "ev-lz3-ai (SE)") {
    Say "Fel subscription ($sub) -- byter..."
    az account set --subscription "ev-lz3-ai (SE)"; Gate "account set"
}
# Rollkravande lasning = PIM-matning. Faller den: rollen ar dod, INTE resursen.
az group show -g $RG -o none
Gate "PIM-rollen nar inte $RG -- aktivera i Portalen (PIM > My roles > aktivera pa RG:n), vanta ~1 min, kor om"
Say "Subscription + PIM OK ($sub)"

if (-not $Deploy) {
    # --- Steg 1: plan (skapa BARA om den saknas) --------------------------------------
    $planId = az appservice plan show -g $RG -n $PLAN --query id -o tsv 2>$null
    if (-not $planId) {
        Say "Planen saknas -- skapar $PLAN (B1 Linux)..."
        az appservice plan create -g $RG -n $PLAN --sku B1 --is-linux --tags owner="Jens Palmo" -o none
        Gate "plan create"
    } else { Say "Planen finns redan: $PLAN" }

    # --- Steg 2: webapp som KOD-app (D.5: container-app kan inte flippas) -------------
    $appId = az webapp show -g $RG -n $APP --query id -o tsv 2>$null
    if (-not $appId) {
        Say "Appen saknas -- skapar $APP (PYTHON:3.11)..."
        az webapp create -g $RG -p $PLAN -n $APP --runtime "PYTHON:3.11" --tags owner="Jens Palmo" -o none
        Gate "webapp create (klagar CLI pa runtime-strangen: prova PYTHON^|3.11)"
    } else { Say "Appen finns redan: $APP" }

    # --- Steg 3: settings + startup + VERIFIERING (mat, anta inte) --------------------
    $key = az storage account keys list --account-name $STORAGE --resource-group $RG --query "[0].value" -o tsv
    Gate "storage keys list"
    if (-not $key) { throw "STOPP: keys list gav tom nyckel." }
    az webapp config appsettings set -g $RG -n $APP -o none --settings `
        SCM_DO_BUILD_DURING_DEPLOYMENT=true PRICINGMODEL_AUTH=key `
        PRICINGMODEL_KEY=$key PRICINGMODEL_STORAGE=$STORAGE PRICINGMODEL_RG=$RG
    Gate "appsettings set"
    az webapp config set -g $RG -n $APP --always-on true `
        --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app" -o none
    Gate "config set (always-on + startup)"
    # D.14: az ar az.cmd -> cmd.exe parsar argumenten FORST; JMESPath-funktions-
    # PARENTESER (length(...)) dor dar med "-o was unexpected". Hakparenteser
    # overlever. Darfor: .name-query + PS-tomhetskoll i stallet for length().
    $n = az webapp config appsettings list -g $RG -n $APP --query "[?name=='PRICINGMODEL_KEY'].name" -o tsv
    Gate "settings verify"
    if (-not $n) { throw "STOPP: PRICINGMODEL_KEY saknas efter set -- settings landade inte." }
    Say "Infra klar och verifierad."

    Write-Host ""
    Write-Host ">>> AUTH-PAUS (D.6 -- dorren fore nyckeln):" -ForegroundColor Yellow
    Write-Host ">>>   Portalen > App Service '$APP' > Authentication > Add identity provider"
    Write-Host ">>>   > Microsoft > Create new app registration > Require authentication"
    Write-Host ">>> Kor sedan fas 2:" -ForegroundColor Yellow
    Write-Host ">>>   powershell -ExecutionPolicy Bypass -File $REPO\tools\deploy_dashboard.ps1 -Deploy"
    exit 0
}

# --- Fas 2: zip + deploy + halsokoll --------------------------------------------------
# Grind: fas 2 kraver att fas 1 byggt infran (annars kaskadar deploy mot tomrum, D.4)
$appId = az webapp show -g $RG -n $APP --query id -o tsv 2>$null
if (-not $appId) { throw "STOPP: appen $APP finns inte i $RG -- kor fas 1 forst (utan -Deploy)." }
Set-Location $REPO

# D.20: nested app-trad genom Oryx tar-extrakt ar OPALITLIGT (fyra uppmatta varv:
# relativ chdir -> flyktigt /tmp-extrakt utan tradet; absolut wwwroot-vag -> wwwroot
# rymmer bara oryx-manifest.toml + output.tar.zst, INTE kallfiler). Boten ar att
# ELIMINERA klassen: appen stagas PLATT och deployas i ZIP-ROTEN -- formen som
# App Service Python-runtimen ar byggd for. Ingen chdir, ingen extrakt-mystik.
$STAGE = Join-Path $env:TEMP "bcg_dashboard_stage"
if (Test-Path $STAGE) { Remove-Item $STAGE -Recurse -Force }
New-Item -ItemType Directory -Force (Join-Path $STAGE "templates") | Out-Null
Copy-Item orchestration\webapp\app.py          $STAGE
Copy-Item orchestration\webapp\story_config.py $STAGE
Copy-Item orchestration\webapp\info_config.py  $STAGE
Copy-Item orchestration\webapp\templates\*    (Join-Path $STAGE "templates")
Copy-Item orchestration\shared\run_status.py   $STAGE
Copy-Item orchestration\infrastructure\blob.py $STAGE
Copy-Item requirements.txt                       $STAGE
# Startup utan chdir (idempotent -- fas 1 kan ha satt gammal chdir-variant)
az webapp config set -g $RG -n $APP `
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app" -o none
Gate "startup-reset (root-layout)"
Set-Location $STAGE
if (-not (Test-Path .gitignore) -or -not (Select-String -Path .gitignore -Pattern "deploy\.zip" -Quiet)) {
    Add-Content .gitignore "deploy.zip"
}
# D.15: Compress-Archive (PS 5.1) skriver BACKSLASH som separator i zip-poster.
# Linux ser da inga kataloger -- Oryx bygger (rotfiler ok) men gunicorn dor pa
# "can't chdir to orchestration/webapp". Python-zipfile skriver korrekta '/'.
if (Test-Path deploy.zip) { Remove-Item deploy.zip -Force }
py -3.11 -m zipfile -c deploy.zip app.py story_config.py info_config.py blob.py run_status.py requirements.txt templates
Gate "zip-bygge (py -m zipfile, platt rot-layout)"
# Mat, anta inte: 0 backslash-poster + nyckelfilerna i ZIP-ROTEN (D.15 + D.20).
$bad = py -3.11 -c "import zipfile; print(sum(1 for n in zipfile.ZipFile('deploy.zip').namelist() if chr(92) in n))"
if ($bad -ne "0") { throw "STOPP: $bad zip-poster har backslash-separatorer (D.15)." }
$ok = py -3.11 -c "import zipfile; ns=set(zipfile.ZipFile('deploy.zip').namelist()); print(int(all(x in ns for x in ['app.py','blob.py','run_status.py','templates/dashboard.html'])))"
if ($ok -ne "1") { throw "STOPP: rot-filer saknas i zipen (app/blob/run_status/templates)." }
$mb = [math]::Round((Get-Item deploy.zip).Length / 1MB, 1)
Say "deploy.zip byggd ($mb MB). Forsta poster (ska ha snedstreck '/'):"
py -3.11 -c "import zipfile; [print('    '+n) for n in zipfile.ZipFile('deploy.zip').namelist()[:4]]"
# D.16: 'az webapp deploy' kan HOPPA Oryx-bygget ('Build successful 0s') -- da
# extraherar runtime GAMLA output.tar.zst och forra felet spokar vidare fast
# kallzipen ar lagad. config-zip bygger BEVISAT (71 s uppmatt 2026-07-04).
# Deprecated-varningen ar kosmetisk. Krav: 'Building the app... 30-90 s' ska SYNAS.
# D.18: en krasch-loopande sajt delar B1-instansens ENDA karna med Kudu-bygget
# (71 s-bygge blev 15+ min). Stoppa sajten fore deploy -> bygg i lugn -> starta.
Say "Stoppar sajten (krasch-loop far inte stjala byggets CPU, D.18)..."
az webapp stop -g $RG -n $APP -o none; Gate "webapp stop"
# D.19: med sajten stoppad (D.18) kan config-zip-pollerns "Starting the site"
# ALDRIG lyckas -- den vantar pa nagot vi sjalva haller nere. FORVANTAT beteende:
# bygget blir klart (~80-120 s), pollern hanger, timeouten slapper oss till
# D.17-grenen som mater byggstatus och gar vidare. Darfor kort timeout (300 s).
Say "Deployar via config-zip (bygget ska SYNAS vaxa; pollern hanger sedan AVSIKTLIGT pa Starting, D.19)..."
az webapp deployment source config-zip -g $RG -n $APP --src deploy.zip --timeout 300
if ($LASTEXITCODE -ne 0) {
    # D.17: klient-timeout ar OBSERVATIONSFORLUST, inte byggdod. D.21: 'az webapp
    # deployment list' saknas i vissa CLI-versioner ("'list' is misspelled", uppmatt)
    # -- darfor VERSION-SAKER hantering: fast extra byggtid, sedan lat start +
    # halsokollen doma (den ar anda slutdomaren).
    Say "Klient-timeout (forvantat med stoppad sajt, D.19) -- ger bygget 120 s till (D.17/D.21)..."
    Start-Sleep 120
}
Say "Bygget klart -- startar sajten + halsokoll..."
az webapp start -g $RG -n $APP -o none; Gate "webapp start"
Start-Sleep 40
$code = 0
try {
    $r = Invoke-WebRequest "https://$APP.azurewebsites.net" -UseBasicParsing -MaximumRedirection 0
    $code = [int]$r.StatusCode
} catch {
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
}
Say "HTTP-svar: $code"
if ($code -eq 302 -or $code -eq 401) {
    Say "RATT: login-redirect -- appen ar publicerad och last bakom Entra-inloggning."
} elseif ($code -eq 200) {
    Write-Host ">>> VARNING: 200 UTAN inloggning -- auth ar INTE aktiv. Aktivera i Portalen NU." -ForegroundColor Red
} elseif ($code -eq 503) {
    Say "503: appen startar an / bygget foll. Kor: az webapp log tail -g $RG -n $APP"
} else {
    Say "Ovantat svar -- kor: az webapp log tail -g $RG -n $APP"
}

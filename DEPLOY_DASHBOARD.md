# DEPLOY_DASHBOARD.md — publicera dashboarden permanent (utan VS Code)

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB).
**Mönster:** MASTER_AZURE §3 (ACR Tasks → App Service-container, bevisat av hemsida_automation) + §4 (Dockerfile).
**Förutsättning:** FD.33 Etapp A klar (appen läser Blob-kvitton — inget lokalt beroende kvar för molnläge).

---

## Två alternativ — välj efter publik

| | A. Schemaläggaren (lokalt) | B. App Service (molnet) |
|---|---|---|
| Vem ser den | Bara du (127.0.0.1) | Kollegor (låst med Entra-inloggning) |
| Tid att sätta upp | ~5 min | ~30–45 min första gången |
| Kostnad | 0 | B1-plan ~110 kr/mån (delas om hemsida_automations plan återanvänds) |
| Beroenden | Din dator påslagen | Ingen — överlever att datorn stängs |
| Skuld | Ingen ny | Kontonyckel som app setting (tills Kents dataroll → MI) |

**Rekommendation:** A idag (0 risk, löser "inte ha VS Code öppet"), B när du vill visa kollegor — B är ju hela FD.32-syftet, så den är målet.

---

## A. Schemaläggaren — appen startar själv vid inloggning (5 min)

`pythonw.exe` = Python utan konsolfönster; appen lever i bakgrunden, VS Code och terminaler stängda.

```powershell
# PowerShell, C:\Projekt\BCG — skapar uppgiften EN gång:
$key = az storage account keys list --account-name evbcgpricinginput --resource-group ev-openai-swce-rg-test --query "[0].value" -o tsv
$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe" }
$action  = New-ScheduledTaskAction -Execute $pyw -Argument '"C:\Projekt\BCG\orchestration\webapp\app.py"' -WorkingDirectory "C:\Projekt\BCG"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "BCG-Dashboard" -Action $action -Trigger $trigger -Description "Read-only BCG pricing dashboard, 127.0.0.1:5000"

# PRICINGMODEL_KEY som ANVÄNDAR-miljövariabel så pythonw slipper az CLI (token-4h-fällan LB.88 elimineras):
[Environment]::SetEnvironmentVariable("PRICINGMODEL_AUTH", "key", "User")
[Environment]::SetEnvironmentVariable("PRICINGMODEL_KEY", $key, "User")

Start-ScheduledTask -TaskName "BCG-Dashboard"     # starta direkt utan omloggning
Start-Sleep 8; Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing | Select-Object StatusCode
```
Stoppa/ta bort: `Stop-ScheduledTask -TaskName "BCG-Dashboard"` / `Unregister-ScheduledTask -TaskName "BCG-Dashboard"`.
OBS skuld: nyckeln lagras i din användarprofils miljö — samma klass som key-läget; roteras nyckeln, kör blocket igen.

---

## B. App Service — masterns recept anpassat för dashboarden

### B0. Filplacering (från leveransen)
```
Dockerfile        -> C:\Projekt\BCG\Dockerfile
requirements.txt  -> C:\Projekt\BCG\requirements.txt
.dockerignore     -> C:\Projekt\BCG\.dockerignore
blob.py (uppdat.) -> C:\Projekt\BCG\orchestration\infrastructure\blob.py   (PRICINGMODEL_KEY-vägen)
```

### B1. Namn (defaults valda — kör direkt, eller byt till hemsida_automations)
Defaults nedan skapar allt fräscht i test-RG:n. Har hemsida_automation redan ACR/plan du vill
återanvända (delad kostnad): byt bara `$ACR`/`$PLAN` till dess värden och hoppa skapanderaderna.
ACR- och app-namn måste vara globalt unika — får du "already in use", ändra suffixet.

### B2. Engångsskapande (hoppa det som redan finns)
```powershell
az login --scope https://management.core.windows.net//.default
az account show --query name -o tsv                     # MÅSTE: ev-lz3-ai (SE)
$RG="ev-openai-swce-rg-test"; $ACR="evbcgpricingacr"; $PLAN="bcg-dashboard-plan"; $APP="evbcg-dashboard"

az acr create --resource-group $RG --name $ACR --sku Basic                       # om nytt
az appservice plan create --resource-group $RG --name $PLAN --sku B1 --is-linux  # om ny (AZ.2: inte F1!)
az webapp create --resource-group $RG --plan $PLAN --name $APP `
  --deployment-container-image-name "$ACR.azurecr.io/bcg-dashboard:v1"
az webapp identity assign --resource-group $RG --name $APP
$MI = az webapp identity show --resource-group $RG --name $APP --query principalId -o tsv
$ACRID = az acr show --name $ACR --query id -o tsv
az role assignment create --assignee $MI --role AcrPull --scope $ACRID           # image-pull utan admin-lösen
```

### B3. LÅS DÖRREN FÖRE NYCKELN (ordningen är poängen)
Entra-inloggning aktiveras INNAN kontonyckeln läggs som setting — appen är aldrig
öppen mot internet med företagsdata bakom sig:
```powershell
az webapp auth microsoft update --resource-group $RG --name $APP `
  --client-id (az ad app create --display-name "bcg-dashboard-auth" --query appId -o tsv) `
  --tenant-id (az account show --query tenantId -o tsv) 2>$null
az webapp auth update --resource-group $RG --name $APP --enabled true `
  --action LoginWithAzureActiveDirectory --unauthenticated-client-action RedirectToLoginPage
```
(Krånglar CLI-varianten i er tenant: Portalen → App Service → Authentication → Add identity provider
→ Microsoft → Create new app registration → Require authentication. Två minuter, samma resultat.)

### B4. Settings + deploy + verifiera (= masterns standardsekvens)
```powershell
$key = az storage account keys list --account-name evbcgpricinginput --resource-group $RG --query "[0].value" -o tsv
az webapp config appsettings set --resource-group $RG --name $APP --settings `
  WEBSITES_PORT=8000 PRICINGMODEL_AUTH=key PRICINGMODEL_KEY=$key `
  PRICINGMODEL_STORAGE=evbcgpricinginput PRICINGMODEL_RG=$RG
az webapp config set --resource-group $RG --name $APP --always-on true            # AZ.4

cd C:\Projekt\BCG
az acr build --registry $ACR --image bcg-dashboard:v1 .
az webapp restart --resource-group $RG --name $APP
Start-Sleep -Seconds 30
Invoke-WebRequest -Uri "https://$APP.azurewebsites.net" -UseBasicParsing          # förväntat: redirect till login → 200
```
Felsökning: `az webapp log tail --resource-group $RG --name $APP` (container startar inte →
port/WEBSITES_PORT, image-bygge eller settings — masterns §9-regel).

### B-ALT. Kod-deploy utan ACR (VALD VÄG 2026-07-04 — PIM når inte provider-registrering)
`Microsoft.ContainerRegistry`-registrering kräver subscription-scope; RG-scopad PIM stoppas
(AuthorizationFailed, mätt 2026-07-04). Zip-deploy till Linux Python-runtime kringgår hela
registret — Oryx pip-installerar requirements.txt vid deploy. Dockerfile vilar tills IT
registrerar providern (enrads-ask), då är B2-vägen öppen igen.

```powershell
$RG="ev-openai-swce-rg-test"; $PLAN="bcg-dashboard-plan"; $APP="evbcg-dashboard"
az webapp delete -g $RG -n $APP                       # container-appen kan inte flippas -> aterskapa som kod-app
az webapp create -g $RG -p $PLAN -n $APP --runtime "PYTHON:3.11"
az webapp update -g $RG -n $APP --set tags.owner="Jens Palmö"
$key = az storage account keys list --account-name evbcgpricinginput --resource-group $RG --query "[0].value" -o tsv
az webapp config appsettings set -g $RG -n $APP --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true `
  PRICINGMODEL_AUTH=key PRICINGMODEL_KEY=$key PRICINGMODEL_STORAGE=evbcgpricinginput PRICINGMODEL_RG=$RG
az webapp config set -g $RG -n $APP --always-on true `
  --startup-file "gunicorn --bind=0.0.0.0:8000 --chdir orchestration/webapp --timeout 120 app:app"
# >>> AUTH NU (Portalen -> evbcg-dashboard -> Authentication -> Add identity provider ->
# >>> Microsoft -> Create new app registration -> Require authentication) — FORE deployen.
cd C:\Projekt\BCG
Add-Content .gitignore "deploy.zip"                    # zipen ska ALDRIG committas
Compress-Archive -Path orchestration, requirements.txt -DestinationPath deploy.zip -Force
az webapp deploy -g $RG -n $APP --src-path deploy.zip --type zip     # Oryx bygger (~2-4 min)
Start-Sleep 40; Invoke-WebRequest "https://$APP.azurewebsites.net" -UseBasicParsing
```
Felsökning: `az webapp log tail -g $RG -n $APP`. Runtime-strangen kraver ibland "PYTHON|3.11"
pa aldre CLI. WEBSITES_PORT behovs INTE for kod-appar (container-specifik).

**Redeploy-loopen (kod-vägen, ~2 min):**
```powershell
cd C:\Projekt\BCG
Compress-Archive -Path orchestration, requirements.txt -DestinationPath deploy.zip -Force
az webapp deploy -g $RG -n $APP --src-path deploy.zip --type zip
```

### B5. Redeploy-loopen (ACR-vägen — vilande tills providern registrerats)
```powershell
cd C:\Projekt\BCG
az acr build --registry $ACR --image bcg-dashboard:v1 .
az webapp restart --resource-group $RG --name $APP
```

---

## Kända begränsningar & skulder (deklarerade, inte gömda)
1. **Kontonyckel som app setting** — samma skuldklass som key-läget. Slutmål: Kents dataroll →
   MI + `PRICINGMODEL_AUTH=aad`, ta bort PRICINGMODEL_KEY. Noll kodändring (byggt för det).
2. **Storage-brandvägg:** når inte App Service kontot (403/timeout i log tail) → lägg till
   "Allow Azure services" eller App Service-utgående IP:n på evbcgpricinginput:s nätverksregler.
3. **Statiska facit-kvittolänkar** (proof_chain/FUNNEL "Export summary") pekar på lokala
   verify_tool-vägar → 404 i molnet tills de pekas om till `_blob/`-vägar (kvittona ligger
   redan i receipts-containern sedan Etapp A). Backlog-rad, inte blockerare — drill 3 och
   valideringar per fönster fungerar fullt ut i molnet.
4. **Rollback:** `az webapp config container set` till föregående tagg, eller stäng av
   webappen — lokala A-alternativet är alltid intakt parallellt.

---

## STATUS 2026-07-10 — B-ALT (kod-deploy) BEVISAD e2e, appen STOPPAD i väntan på auth

Deploy-kedjan är bevisad hela vägen (config-zip + Oryx-flaggor → äkta bygge →
gz-extrakt → `/home/startup.sh` kör → gunicorn 20.1.0 → Listening → HTTP 200).
Fyra icke-uppenbara krav visade sig under 15 försök (07-04→07-09):

1. **ZipDeploy, inte OneDeploy.** `az webapp deployment source config-zip`, INTE
   `az webapp deploy` — den senare gav "Build 0(s)" (inget Oryx-bygge).
2. **Båda Oryx-flaggorna:** `SCM_DO_BUILD_DURING_DEPLOYMENT=true` OCH
   `ENABLE_ORYX_BUILD=true`.
3. **startup.sh under /home, skapad server-side.** Kudu VFS-API:t rotar på /home
   → PUT skapade `/home/home/startup.sh` (falskt "finns"-bevis). Fix: extrahera ur
   byggets tarball i Kudu Bash: `cd /home && tar -xzf site/wwwroot/output.tar.gz ./startup.sh`.
   Startup-kommandot är `/home/startup.sh` (absolut), INTE relativ `--chdir`.
4. **EN generation i wwwroot.** Runtime-extraktorn tar `output.tar.zst` FÖRE `.gz`
   → gamla 07-04-generationen bootades varje gång. Riv gamla komprimat/rester i
   Kudu Bash före omstart: `rm -f /home/site/wwwroot/output.tar.zst
   /home/site/wwwroot/requirements.txt /home/site/wwwroot/hostingstart.html`.

**BLOCKERARE (enda kvarvarande):** EasyAuth saknas — appregistrering är
tenant-rättighet utanför RG-scopad PIM (nekad 2026-07-09/10). IT-ask skickad.
**Appen hålls STOPPAD tills auth är på plats** (D.6: 200 utan login = larm;
`state: Stopped` + HTTP 403 verifierat). Startas EJ förrän Entra-registreringen
landat. När den gör det: verifiera i portalen → `az webapp start` → ping 302/401.

**Permanent väg framåt:** Azure DevOps-pipelinen (`azure-pipelines.yml` inert i
repo-roten) bygger i ren Linux-miljö och gör alla fyra kraven ovan by design.
Den manuella B-ALT-vägen fungerar men är formellt stängd som rutin — reserverad
för engångs-/nödläge. Full spökkatalog: MASTER_AZURE_DEPLOY (kandidat D.24–D.32).

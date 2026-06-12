# =====================================================================
# setup_z0_foundation.ps1 -- Phase Z.0: grundresurser for pricingmodel
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Skapad:     Phase Z, session 1 (AI-radgivare)
#
# SYFTE
#   Skapa det minsta som behovs for orchestrator-karnan (Z.1-Z.2):
#     1. Storage Account  -> har statusfil + output i Blob. Overlever
#        att VM:en deallokeras; kollega laser utan VM-access.
#     2. User-Assigned Managed Identity -> orchestratorns korande
#        identitet. Vald framfor System-Assigned for att den OVERLEVER
#        att resurser rivs/aterskapas och kan delas av flera resurser
#        (CLI nu, ev. Flask-app senare) -- ratt for ett ateranvandbart
#        skelett.
#     3. Tva blob-containrar: 'runstatus' (statusfiler) + 'output'.
#
#   Detta ar ocksa ett EMPIRISKT TEST: racker RG-Owner for att skapa
#   resurser, eller kravs subscription-niva nagonstans? Vi mater, antar
#   inte. Storage + ManagedIdentity-providers ar redan Registered, sa
#   detta SKA ga -- men vi verifierar att det faktiskt gor det.
#
# BEHORIGHETSKONTEXT (matt 2026-06-12)
#   Jens = permanent Owner pa ev-openai-swce-rg-prod (RG-niva).
#   RG-Owner racker INTE for subscription-niva-actions (provider
#   register foll med AuthorizationFailed). Detta skript haller sig
#   helt inom RG-scope -- inga subscription-operationer.
#
# IDEMPOTENS
#   Skriptet kan koras om utan skada. Det kontrollerar om varje resurs
#   redan finns innan det skapar. Andrar inget pa befintliga resurser.
#
# DETTA SKRIPT SKAPAR RESURSER (kostar pengar)
#   Storage Account Standard_LRS i Sweden Central: nagra ören/manad vid
#   var datavolym -- forsumbart. MI ar gratis. Riskflagga: detta ar
#   forsta gangen vi SKRIVER till prod-RG. Allt ar smatt och rivbart.
#
# STANDARD (KARNPRINCIPER + Jens preferenser)
#   Ren ASCII (PS 5.1). Receipt till validation_receipts\. Loggsektion
#   forst. Idempotent. Namntillganglighet testas innan skapande.
# =====================================================================

[CmdletBinding()]
param(
    [string]$SubscriptionId   = "42f726f8-91ee-44d4-832f-9d9ec412ef8f",  # ev-lz3-ai (SE)
    [string]$SubscriptionName = "ev-lz3-ai (SE)",
    [string]$ResourceGroup    = "ev-openai-swce-rg-prod",
    [string]$Location         = "swedencentral",

    [string]$StorageAccount   = "evipricingmodelstprod",
    [string]$ManagedIdentity  = "evi-pricingmodel-mi-prod",
    [string]$ContainerStatus  = "runstatus",
    [string]$ContainerOutput  = "output",

    [string]$LogDir = "C:\Projekt\BCG\workspace\validation_receipts"
)

$ErrorActionPreference = "Continue"

# ---------- Logguppsattning ----------
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logFile = Join-Path $LogDir "setup_z0_foundation_$stamp.log"

function Write-Line { param([string]$Text)
    Write-Host $Text
    Add-Content -Path $logFile -Value $Text -Encoding ASCII
}
function Write-Header { param([string]$Title)
    Write-Line ""
    Write-Line ("=" * 70)
    Write-Line $Title
    Write-Line ("=" * 70)
}

$results = [ordered]@{}

# ---------- Loggsektion forst ----------
Write-Line ("=" * 70)
Write-Line "LOGG -- Phase Z.0 foundation"
Write-Line ("=" * 70)
Write-Line ("Tidsstampel    : " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Line ("Loggfil        : " + $logFile)
Write-Line ("Korande anvand : " + $env:USERNAME)
Write-Line ("Subscription   : " + $SubscriptionName + " (" + $SubscriptionId + ")")
Write-Line ("Resursgrupp    : " + $ResourceGroup + " (" + $Location + ")")
Write-Line ("Storage        : " + $StorageAccount)
Write-Line ("Managed Id     : " + $ManagedIdentity)
Write-Line ("Containrar     : " + $ContainerStatus + ", " + $ContainerOutput)
Write-Line ("Syfte          : skapa grundresurser; testa att RG-Owner racker")
Write-Line ("OBS            : idempotent -- kan koras om utan skada")

# ---------- Steg 0: subscription korrekt (LB.46) ----------
Write-Header "STEG 0 -- ratt subscription aktiv"
az account set --subscription $SubscriptionId 2>$null
$cur = az account show --query "id" -o tsv 2>$null
if ($cur -eq $SubscriptionId) {
    Write-Line ("OK   aktiv subscription: " + $SubscriptionId)
    $results["0_subscription"] = "PASS"
} else {
    Write-Line ("FAIL aktiv sub '" + $cur + "' != '" + $SubscriptionId + "'. Kor:")
    Write-Line ('       az account set --subscription "' + $SubscriptionName + '"')
    Write-Line "AVBRYTER -- fel subscription."
    return
}

# ---------- Steg 1: namntillganglighet for Storage Account ----------
# Storage-namn ar GLOBALT unika. Testa innan vi forsoker skapa, sa vi
# far ett tydligt besked i stallet for ett kryptiskt fel.
Write-Header "STEG 1 -- Storage Account namntillganglighet"
$exists = az storage account show --name $StorageAccount --resource-group $ResourceGroup 2>$null
if ($exists) {
    Write-Line ("OK   Storage '" + $StorageAccount + "' finns redan i denna RG (idempotent -- skapar ej om).")
    $results["1_storage_namn"] = "EXISTS"
    $storageReady = $true
} else {
    $avail = az storage account check-name --name $StorageAccount --query "nameAvailable" -o tsv 2>$null
    if ($avail -eq "true") {
        Write-Line ("OK   namnet '" + $StorageAccount + "' ar ledigt globalt.")
        $results["1_storage_namn"] = "AVAILABLE"
        $storageReady = $false
    } else {
        $reason = az storage account check-name --name $StorageAccount --query "reason" -o tsv 2>$null
        Write-Line ("FAIL namnet '" + $StorageAccount + "' ej tillgangligt. Orsak: " + $reason)
        Write-Line "     Valj annat namn (globalt unikt, gemener+siffror, max 24 tecken) och kor om."
        $results["1_storage_namn"] = "FAIL"
        Write-Header "AVBRYTER -- storage-namn upptaget"
        return
    }
}

# ---------- Steg 2: skapa Storage Account (om det inte fanns) ----------
Write-Header "STEG 2 -- skapa Storage Account"
if ($storageReady) {
    Write-Line "INFO Storage fanns redan -- hoppar over skapande."
    $results["2_storage_skapa"] = "SKIPPED"
} else {
    Write-Line ("     Skapar " + $StorageAccount + " (Standard_LRS, " + $Location + ") ...")
    # --min-tls-version och --allow-blob-public-access false = sakra defaults.
    # LRS (lokalt redundant) racker -- detta ar harledd analysdata, ej
    # kallsystem; billigaste redundansnivan, helt tillracklig.
    $create = az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku "Standard_LRS" `
        --kind "StorageV2" `
        --min-tls-version "TLS1_2" `
        --allow-blob-public-access false `
        --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Line "OK   Storage Account skapat."
        Write-Line "     >>> VIKTIGT FYND: RG-Owner RACKER for resursskapande i prod-RG. <<<"
        $results["2_storage_skapa"] = "PASS"
    } else {
        Write-Line "FAIL Storage Account kunde inte skapas. Rad-output:"
        Write-Line ("     " + ($create | Out-String).Trim())
        Write-Line "     Om AuthorizationFailed -> RG-Owner racker INTE; eskalera till RG/sub-agare."
        $results["2_storage_skapa"] = "FAIL"
        Write-Header "AVBRYTER -- kunde ej skapa storage"
        return
    }
}

# ---------- Steg 3: skapa User-Assigned Managed Identity ----------
Write-Header "STEG 3 -- skapa User-Assigned Managed Identity"
$miExists = az identity show --name $ManagedIdentity --resource-group $ResourceGroup 2>$null
if ($miExists) {
    Write-Line ("OK   MI '" + $ManagedIdentity + "' finns redan (idempotent).")
    $results["3_mi_skapa"] = "EXISTS"
} else {
    Write-Line ("     Skapar User-Assigned MI " + $ManagedIdentity + " ...")
    $mi = az identity create --name $ManagedIdentity --resource-group $ResourceGroup --location $Location --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Line "OK   Managed Identity skapad."
        $results["3_mi_skapa"] = "PASS"
    } else {
        Write-Line "FAIL MI kunde inte skapas. Rad-output:"
        Write-Line ("     " + ($mi | Out-String).Trim())
        $results["3_mi_skapa"] = "FAIL"
    }
}

# Las MI:s ID (behovs i Z.2 for rolltilldelning + i azure_vm.py)
$miClientId    = az identity show --name $ManagedIdentity --resource-group $ResourceGroup --query "clientId" -o tsv 2>$null
$miPrincipalId = az identity show --name $ManagedIdentity --resource-group $ResourceGroup --query "principalId" -o tsv 2>$null
$miResourceId  = az identity show --name $ManagedIdentity --resource-group $ResourceGroup --query "id" -o tsv 2>$null
Write-Line ("     MI clientId    : " + $miClientId)
Write-Line ("     MI principalId : " + $miPrincipalId + "   (anvands for rolltilldelning i Z.2)")

# ---------- Steg 4: skapa blob-containrar ----------
# Vi anvander --auth-mode login (AAD), inte konto-nyckel. Det ar best
# practice: ingen nyckel att lacka. Kraver att DITT konto har en
# data-plane-roll pa storage. Har du precis skapat kontot som Owner kan
# du ha control-plane men inte data-plane an -- darfor testar vi och ger
# tydligt besked om det fallerar (da gor Z.2:s rolltilldelning susen).
Write-Header "STEG 4 -- skapa blob-containrar (AAD-auth)"
foreach ($c in @($ContainerStatus, $ContainerOutput)) {
    Write-Line ("     Container: " + $c)
    $cc = az storage container create `
        --name $c `
        --account-name $StorageAccount `
        --auth-mode login `
        --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Line ("OK   container '" + $c + "' klar.")
        $results["4_container_$c"] = "PASS"
    } else {
        Write-Line ("WARN container '" + $c + "' kunde inte skapas via AAD-auth nu:")
        Write-Line ("     " + ($cc | Out-String).Trim())
        Write-Line "     Trolig orsak: ditt konto saknar data-plane-roll (Storage Blob Data"
        Write-Line "     Contributor) pa kontot annu. Detta tilldelas i Z.2. Ej blockerande har."
        $results["4_container_$c"] = "DEFERRED"
    }
}

# ---------- Sammanfattning ----------
Write-Header "RESULTATSAMMANFATTNING"
$anyFail = $false
foreach ($k in $results.Keys) {
    Write-Line ("  " + $results[$k].PadRight(9) + " " + $k)
    if ($results[$k] -eq "FAIL") { $anyFail = $true }
}
Write-Line ""
Write-Line "SPARA DESSA FOR Z.1/Z.2 (klistra tillbaka till AI-radgivaren):"
Write-Line ("  StorageAccount   : " + $StorageAccount)
Write-Line ("  MI principalId   : " + $miPrincipalId)
Write-Line ("  MI clientId      : " + $miClientId)
Write-Line ("  MI resourceId    : " + $miResourceId)
Write-Line ""
if ($anyFail) {
    Write-Line "SLUTSATS: Minst ett FAIL -- atgarda innan Z.1. Bygg inte vidare pa trasig grund."
} else {
    Write-Line "SLUTSATS: Grunden star. DEFERRED-containrar (om nagra) loses av Z.2:s rolltilldelning."
}
Write-Line ("Loggfil: " + $logFile)

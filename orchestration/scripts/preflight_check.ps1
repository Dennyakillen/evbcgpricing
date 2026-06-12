# =====================================================================
# preflight_check.ps1 -- Phase Z preflight for evbcgpricing on Azure
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Skapad:     Phase Z, session 1 (AI-radgivare)
#
# SYFTE
#   Kor de fem valideringsstegen ur STARTPROMPT_PHASE_Z.md innan nagon
#   arkitektur byggs. Detta ar Jens forsta riktiga kvitto pa att
#   forutsattningarna stammer. Skriptet GISSAR ALDRIG -- det kor faktiska
#   az-kommandon och visar deras utdata. Tomma/felande svar rapporteras
#   som FAIL eller MANUAL, aldrig som tyst antagande.
#
# BEROR PA
#   - Azure CLI installerat och inloggat (az login --scope ...)
#   - Korrekt subscription: ev-lz3-ai (SE) for BCG-VM (MASTER_AZURE 1.2)
#   - Kors fran office network (VM nas endast via SSH dar; preflight
#     gor dock inga SSH-anrop -- enbart control-plane via az)
#
# DETTA SKRIPT GOR INGA ANDRINGAR
#   Enbart lasoperationer (az ... show / list). Inga start/stop/deallocate.
#
# ANVANDS AV
#   Jens manuellt fore varje Phase Z-bygge. Output (Logg-sektion overst)
#   ar kvittot som matas tillbaka till AI-radgivaren.
#
# STANDARDER (KARNPRINCIPER + Jens preferenser)
#   - Ren ASCII (PS 5.1 laser UTF-8 som CP1252).
#   - Tee till tidsstamplad loggfil; Logg-sektion forst i filen.
#   - Strukturella rader; inga radata-dumpar.
# =====================================================================

[CmdletBinding()]
param(
    # BCG-projektets fakta. Antaganden ur memory -- detta skript VERIFIERAR dem.
    [string]$Subscription   = "ev-lz3-ai (SE)",
    [string]$SubscriptionId = "42f726f8-91ee-44d4-832f-9d9ec412ef8f",
    [string]$VmName         = "bcg-poc-vm",
    [string]$VmResourceGroup= "ev-openai-swce-rg-test",
    [string]$ExpectedRegion = "swedencentral",
    [string]$ExpectedSku    = "Standard_E16s_v5",

    # Loggmapp -- Jens standardarkiv for validerings-kvitton.
    [string]$LogDir = "C:\Projekt\BCG\workspace\validation_receipts"
)

$ErrorActionPreference = "Continue"   # vi vill fortsatta och rapportera, inte krascha

# ---------- Logguppsattning ----------
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logFile = Join-Path $LogDir "preflight_phaseZ_$stamp.log"

# Resultatackumulator: varje steg far PASS / FAIL / MANUAL
$results = [ordered]@{}

function Write-Line {
    param([string]$Text)
    Write-Host $Text
    Add-Content -Path $logFile -Value $Text -Encoding ASCII
}

function Write-Header {
    param([string]$Title)
    Write-Line ""
    Write-Line ("=" * 70)
    Write-Line $Title
    Write-Line ("=" * 70)
}

# ---------- Logg-sektion forst (Jens standard) ----------
Write-Line ("=" * 70)
Write-Line "LOGG -- Phase Z preflight"
Write-Line ("=" * 70)
Write-Line ("Tidsstampel    : " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Line ("Loggfil        : " + $logFile)
Write-Line ("Korande anvand : " + $env:USERNAME)
Write-Line ("Maskin         : " + $env:COMPUTERNAME)
Write-Line ("Subscription   : " + $Subscription + " (" + $SubscriptionId + ")")
Write-Line ("VM             : " + $VmName + " i RG " + $VmResourceGroup)
Write-Line ("Forvantat      : " + $ExpectedSku + " / " + $ExpectedRegion)
Write-Line ("Syfte          : verifiera de 5 stegen ur STARTPROMPT_PHASE_Z fore bygge")
Write-Line ("OBS            : enbart lasoperationer -- inga andringar gors")
Write-Line ""
Write-Line "Resultatsammanfattning fylls i sist i denna fil."

# ---------- Steg 0: az finns och ar inloggad ----------
Write-Header "STEG 0 -- az CLI installerat och inloggat"
$azOk = $false
try {
    $acct = az account show 2>$null | ConvertFrom-Json
    if ($acct) {
        Write-Line ("OK   az inloggad som : " + $acct.user.name)
        Write-Line ("     aktiv sub       : " + $acct.name + " (" + $acct.id + ")")
        $azOk = $true
    } else {
        Write-Line "FAIL az account show gav tomt svar -- kor: az login --scope https://management.core.windows.net//.default"
    }
} catch {
    Write-Line "FAIL az CLI svarar inte. Ar Azure CLI installerat och inloggat?"
}
$results["0_az_inloggad"] = if ($azOk) { "PASS" } else { "FAIL" }

if (-not $azOk) {
    Write-Header "AVBRYTER -- az ej tillgangligt"
    Write-Line "Logga in och kor om: az login --scope https://management.core.windows.net//.default"
    Write-Line ("Loggfil sparad: " + $logFile)
    return
}

# ---------- Steg 1 (Startprompt p.1): verifiera ProvetDiscount-mall ----------
# Detta steg kraver MASTER_AZURE-jamforelse, inte ett az-anrop. Markeras MANUAL
# sa Jens medvetet kvitterar att han last och stamt av mot dokumentet.
Write-Header "STEG 1 -- ProvetDiscount-monstret verifierat mot MASTER_AZURE (MANUELL kvittens)"
Write-Line "Detta steg ar en LASKONTROLL mot MASTER_AZURE, inte ett kommando."
Write-Line "Bekrafta foljande mot MASTER_AZURE 2.x innan bygge (kryssa manuellt):"
Write-Line "  [ ] RG-namn        : ev-vetpris-swce-rg-prod (ProvetDiscount, Owner)"
Write-Line "  [ ] ACR            : evvetprisswceprodacr (Basic, Sweden Central)"
Write-Line "  [ ] App Service SKU: B1 Linux (AZ.2: F1 racker INTE)"
Write-Line "  [ ] MI-flode       : SystemAssigned + AcrPull (kraver Owner, E.4)"
Write-Line "  [ ] Deploy         : az acr build (ACR Tasks, ingen lokal Docker)"
Write-Line ""
Write-Line "VIKTIGT (diskrepans funnen vid bygge):"
Write-Line "  ProvetDiscount-skelettet ligger i ev-lz1-hybrid (SE)."
Write-Line "  BCG-VM:en ligger i ev-lz3-ai (SE). Det ar TVA subscriptions."
Write-Line "  Vagval for Z.0/Z.3: nya resurser i ev-lz3-ai ELLER cross-sub."
$results["1_provetdiscount_mall"] = "MANUAL"

# ---------- Steg 2 (Startprompt p.2): Owner pa BCG-RG ----------
Write-Header "STEG 2 -- Owner-roll pa BCG-RG"
$ownerOk = $false
try {
    $scope = "/subscriptions/$SubscriptionId/resourceGroups/$VmResourceGroup"
    $roles = az role assignment list --assignee $acct.user.name --scope $scope 2>$null | ConvertFrom-Json
    if ($roles) {
        $roleNames = ($roles | ForEach-Object { $_.roleDefinitionName }) -join ", "
        Write-Line ("     Roller pa " + $VmResourceGroup + " : " + $roleNames)
        if ($roleNames -match "Owner") {
            Write-Line "OK   Owner bekraftad -- kan tilldela roller sjalv (MI, AcrPull, Blob)."
            $ownerOk = $true
        } else {
            Write-Line "WARN Owner SAKNAS pa denna RG. Rolltilldelning (E.4/AZ.1) blockeras."
            Write-Line "     Notera: VM-RG kan skilja fran den RG dar du tanker lagga nya resurser."
        }
    } else {
        Write-Line "MANUAL Inga rolltilldelningar returnerades for ditt konto pa denna scope."
        Write-Line "       Kontrollera RG-namnet och att ratt subscription ar aktiv (se Steg 3)."
    }
} catch {
    Write-Line "FAIL  az role assignment list kastade fel -- se ovan."
}
$results["2_owner_roll"] = if ($ownerOk) { "PASS" } else { "MANUAL" }

# ---------- Steg 3 (Startprompt p.3 del 1): subscription korrekt ----------
Write-Header "STEG 3 -- Korrekt subscription aktiv (LB.46-fallan)"
$subOk = $false
if ($acct.id -eq $SubscriptionId) {
    Write-Line ("OK   Aktiv subscription matchar BCG: " + $acct.name)
    $subOk = $true
} else {
    Write-Line ("WARN Aktiv sub ar '" + $acct.name + "' men BCG kraver '" + $Subscription + "'.")
    Write-Line "     Detta ar exakt LB.46-fallan. Kor foljande och kor om preflight:"
    Write-Line ('       az account set --subscription "' + $Subscription + '"')
}
$results["3_subscription"] = if ($subOk) { "PASS" } else { "FAIL" }

# ---------- Steg 3 (Startprompt p.3 del 2): VM finns, SKU/region ----------
Write-Header "STEG 3b -- VM finns med ratt SKU och region"
$vmOk = $false
if ($subOk) {
    try {
        $vm = az vm show --name $VmName --resource-group $VmResourceGroup 2>$null | ConvertFrom-Json
        if ($vm) {
            $sku = $vm.hardwareProfile.vmSize
            $loc = $vm.location
            Write-Line ("     VM-namn : " + $vm.name)
            Write-Line ("     SKU     : " + $sku + "  (forvantat " + $ExpectedSku + ")")
            Write-Line ("     Region  : " + $loc + "  (forvantat " + $ExpectedRegion + ")")
            $skuMatch = ($sku -eq $ExpectedSku)
            $locMatch = ($loc -eq $ExpectedRegion)
            if ($skuMatch -and $locMatch) {
                Write-Line "OK   VM-fakta matchar memory-noten."
                $vmOk = $true
            } else {
                Write-Line "WARN VM finns men SKU eller region avviker fran forvantat -- uppdatera memory."
                $vmOk = $true   # VM finns; avvikelse ar en notering, inte ett hart fel
            }
        } else {
            Write-Line ("FAIL VM '" + $VmName + "' hittades inte i RG '" + $VmResourceGroup + "'.")
            Write-Line "     Kontrollera VM-namn/RG (memory-antagande) eller subscription."
        }
    } catch {
        Write-Line "FAIL az vm show kastade fel."
    }
} else {
    Write-Line "HOPPAS OVER -- fel subscription aktiv (se Steg 3). Satt ratt sub forst."
}
$results["3b_vm_finns"] = if ($vmOk) { "PASS" } else { "FAIL" }

# ---------- Steg 3 (Startprompt p.3 del 3): VM power state ----------
Write-Header "STEG 3c -- VM power state (informativt)"
if ($vmOk) {
    try {
        $iv = az vm get-instance-view --name $VmName --resource-group $VmResourceGroup 2>$null | ConvertFrom-Json
        $power = ($iv.instanceView.statuses | Where-Object { $_.code -like "PowerState/*" }).displayStatus
        Write-Line ("     Power state: " + $power)
        if ($power -match "deallocated") {
            Write-Line "OK   VM ar deallocated -- ingen compute-debitering pagar nu."
        } elseif ($power -match "running") {
            Write-Line "WARN VM KORS just nu (~9 kr/h). Deallokera om ingen korning pagar:"
            Write-Line ("       az vm deallocate --resource-group " + $VmResourceGroup + " --name " + $VmName)
        }
    } catch {
        Write-Line "INFO Kunde inte lasa power state (ej blockerande)."
    }
} else {
    Write-Line "HOPPAS OVER -- VM ej bekraftad."
}
$results["3c_power_state"] = "INFO"

# ---------- Steg 4 (Startprompt p.4): E-serie quota headroom ----------
Write-Header "STEG 4 -- E-serie quota har headroom i Sweden Central"
$quotaOk = $false
if ($subOk) {
    try {
        $usage = az vm list-usage --location $ExpectedRegion 2>$null | ConvertFrom-Json
        # E16s_v5 tillhor "Standard ESv5 Family vCPUs" -- behover 16 lediga vCPU.
        $esv5 = $usage | Where-Object { $_.localName -match "ESv5" -or $_.localName -match "ES v5" }
        if ($esv5) {
            foreach ($q in $esv5) {
                $free = [int]$q.limit - [int]$q.currentValue
                Write-Line ("     " + $q.localName + " : anvant " + $q.currentValue + " / limit " + $q.limit + " -> ledigt " + $free)
                if ($free -ge 16) {
                    Write-Line "OK   Minst 16 vCPU lediga -- E16s_v5 far plats."
                    $quotaOk = $true
                } else {
                    Write-Line "WARN Mindre an 16 vCPU lediga -- VM-start kan neka. Begar quota-okning."
                }
            }
        } else {
            Write-Line "MANUAL Hittade ingen ESv5-rad i quota-listan. Kontrollera familjenamn manuellt:"
            Write-Line "       az vm list-usage --location swedencentral --output table | findstr /i esv5"
        }
    } catch {
        Write-Line "FAIL az vm list-usage kastade fel."
    }
} else {
    Write-Line "HOPPAS OVER -- fel subscription aktiv."
}
$results["4_quota"] = if ($quotaOk) { "PASS" } else { "MANUAL" }

# ---------- Steg 5 (Startprompt p.5): projektets egna RG ----------
Write-Header "STEG 5 -- Projektets egna RG (test + prod) -- inventering"
Write-Line "Startprompten vill skapa egna BCG-RG, isolerade fran ProvetDiscount."
Write-Line "Detta steg INVENTERAR vad som redan finns -- skapar inget."
if ($subOk) {
    try {
        $rgs = az group list --query "[?contains(name,'bcg') || contains(name,'openai') || contains(name,'pricing')].{name:name,location:location}" 2>$null | ConvertFrom-Json
        if ($rgs) {
            foreach ($rg in $rgs) {
                Write-Line ("     RG: " + $rg.name + "  (" + $rg.location + ")")
            }
            Write-Line "INFO Ovan ar befintliga relaterade RG. Beslut om nya egna RG tas i Z.0."
        } else {
            Write-Line "INFO Inga RG med bcg/openai/pricing i namnet i denna subscription."
        }
    } catch {
        Write-Line "INFO Kunde inte lista RG (ej blockerande)."
    }
} else {
    Write-Line "HOPPAS OVER -- fel subscription aktiv."
}
$results["5_egna_rg"] = "INFO"

# ---------- Resultatsammanfattning ----------
Write-Header "RESULTATSAMMANFATTNING"
$anyFail = $false
foreach ($k in $results.Keys) {
    $v = $results[$k]
    Write-Line ("  " + $v.PadRight(7) + " " + $k)
    if ($v -eq "FAIL") { $anyFail = $true }
}
Write-Line ""
if ($anyFail) {
    Write-Line "SLUTSATS: Minst ett FAIL -- atgarda innan bygge. Bygg inte pa otestade antaganden."
} else {
    Write-Line "SLUTSATS: Inga FAIL. MANUAL/INFO-steg kraver din kvittens men blockerar inte."
}
Write-Line ""
Write-Line "Mata tillbaka denna fils Logg-sektion + sammanfattning till AI-radgivaren."
Write-Line ("Loggfil: " + $logFile)

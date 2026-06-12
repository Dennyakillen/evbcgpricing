# =====================================================================
# setup_z2_roles.ps1 -- Phase Z.2: roller till orchestratorns identitet
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Skapad:     Phase Z, session 1 (AI-radgivare)
#
# SYFTE
#   Ge den User-Assigned Managed Identity (MI) som skapades i Z.0 exakt
#   de roller orchestratorn behover -- inte mer (minsta-privilegium):
#     1. Storage Blob Data Contributor  -> pa storage-kontot, sa MI:n
#        kan skriva/lasa statusfil + output i Blob.
#     2. Virtual Machine Contributor    -> pa test-RG (dar VM:en bor),
#        sa MI:n kan starta/deallokera bcg-poc-vm. CROSS-RG: MI lever i
#        prod-RG men styr en VM i test-RG -- medvetet, dokumenterat.
#
#   VARFOR INTE Owner till MI:n: en automation-identitet ska aldrig ha
#   bredare ratt an den anvander. Owner pa en automation = sakerhets-
#   skuld. Tva smala roller racker exakt for det orchestratorn gor.
#
# VIKTIGT OM ANVANDNING (las -- vanlig missuppfattning)
#   En User-Assigned MI kan INTE logga in fran din laptop. Den anvands
#   skarpt forst nar koden kor PA en Azure-resurs (App Service/VM) som
#   MI:n ar tilldelad till. Under lokal utveckling kor azure_vm.py/
#   blob.py som DIG via DefaultAzureCredential (din az-login). Samma kod
#   byter automatiskt till MI:n nar den flyttar till molnet -- ingen
#   andring. Denna rolltilldelning gor MI:n REDO for det skiftet.
#
# BEHORIGHET SOM KRAVS FOR ATT KORA DETTA SKRIPT
#   Du tilldelar roller -> kraver Owner pa respektive scope. Du ar
#   permanent Owner pa BADE prod-RG och test-RG (matt 2026-06-12), sa
#   bada tilldelningarna ska ga. OBS villkoret i din Owner: testa om
#   det tillater att tilldela ANDRA roller an Owner (constrained
#   delegation). Failar det med villkorfel -> da var det den begransning
#   vi flaggade, och da behovs RG-agaren for just rolltilldelningen.
#
# IDEMPOTENS
#   Kontrollerar om rollen redan finns innan tilldelning. Kan koras om.
#
# STANDARD: ren ASCII (PS 5.1), receipt, loggsektion forst.
# =====================================================================

[CmdletBinding()]
param(
    [string]$SubscriptionId   = "42f726f8-91ee-44d4-832f-9d9ec412ef8f",
    [string]$SubscriptionName = "ev-lz3-ai (SE)",

    # MI (skapad i Z.0). principalId = mal for rolltilldelning.
    [string]$MiPrincipalId    = "14fe926b-8722-4c53-9ef8-642e190fb0d0",
    [string]$MiName           = "evi-pricingmodel-mi-prod",

    # Scope 1: storage-kontot (i prod-RG) for blob-data.
    [string]$ProdResourceGroup= "ev-openai-swce-rg-prod",
    [string]$StorageAccount   = "evipricingmodelstprod",

    # Scope 2: test-RG (dar VM:en bor) for VM-livscykel.
    [string]$TestResourceGroup= "ev-openai-swce-rg-test",

    [string]$LogDir = "C:\Projekt\BCG\workspace\validation_receipts"
)

$ErrorActionPreference = "Continue"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logFile = Join-Path $LogDir "setup_z2_roles_$stamp.log"

function Write-Line { param([string]$Text)
    Write-Host $Text
    Add-Content -Path $logFile -Value $Text -Encoding ASCII
}
function Write-Header { param([string]$Title)
    Write-Line ""
    Write-Line ("=" * 70); Write-Line $Title; Write-Line ("=" * 70)
}

$results = [ordered]@{}

Write-Line ("=" * 70)
Write-Line "LOGG -- Phase Z.2 rolltilldelning till MI"
Write-Line ("=" * 70)
Write-Line ("Tidsstampel  : " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Line ("Loggfil      : " + $logFile)
Write-Line ("MI           : " + $MiName + " (" + $MiPrincipalId + ")")
Write-Line ("Storage      : " + $StorageAccount + " i " + $ProdResourceGroup)
Write-Line ("VM-RG        : " + $TestResourceGroup + " (cross-RG)")
Write-Line ("Roller       : Storage Blob Data Contributor + Virtual Machine Contributor")

# Steg 0: ratt subscription
Write-Header "STEG 0 -- ratt subscription"
az account set --subscription $SubscriptionId 2>$null
$cur = az account show --query "id" -o tsv 2>$null
if ($cur -eq $SubscriptionId) {
    Write-Line ("OK   " + $SubscriptionId); $results["0_sub"] = "PASS"
} else {
    Write-Line "FAIL fel subscription -- AVBRYTER."; return
}

# Hjalpfunktion: tilldela roll idempotent
function Assign-Role {
    param([string]$RoleName, [string]$Scope, [string]$Key)
    Write-Line ("     Roll : " + $RoleName)
    Write-Line ("     Scope: " + $Scope)
    # Finns rollen redan for MI pa denna scope?
    $existing = az role assignment list `
        --assignee $MiPrincipalId --scope $Scope `
        --query "[?roleDefinitionName=='$RoleName'] | length(@)" -o tsv 2>$null
    if ($existing -and [int]$existing -gt 0) {
        Write-Line "OK   rollen finns redan (idempotent -- ror ej)."
        $script:results[$Key] = "EXISTS"; return
    }
    $out = az role assignment create `
        --assignee-object-id $MiPrincipalId `
        --assignee-principal-type "ServicePrincipal" `
        --role $RoleName `
        --scope $Scope `
        --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Line "OK   roll tilldelad."
        $script:results[$Key] = "PASS"
    } else {
        Write-Line "FAIL kunde inte tilldela rollen. Rad-output:"
        Write-Line ("     " + ($out | Out-String).Trim())
        Write-Line "     Om villkor-/AuthorizationFailed: din Owner kan vara begransad till"
        Write-Line "     att bara tilldela Owner (constrained delegation). Da kravs RG-agaren"
        Write-Line "     for just denna rolltilldelning -- enda potentiella IT-asken."
        $script:results[$Key] = "FAIL"
    }
}

# Steg 1: Storage Blob Data Contributor pa storage-kontot
Write-Header "STEG 1 -- Storage Blob Data Contributor (blob-data)"
$storageScope = "/subscriptions/$SubscriptionId/resourceGroups/$ProdResourceGroup/providers/Microsoft.Storage/storageAccounts/$StorageAccount"
Assign-Role -RoleName "Storage Blob Data Contributor" -Scope $storageScope -Key "1_blob_roll"

# Steg 2: Virtual Machine Contributor pa test-RG (cross-RG)
Write-Header "STEG 2 -- Virtual Machine Contributor (VM-livscykel, cross-RG)"
$vmScope = "/subscriptions/$SubscriptionId/resourceGroups/$TestResourceGroup"
Assign-Role -RoleName "Virtual Machine Contributor" -Scope $vmScope -Key "2_vm_roll"

# Steg 3: verifiera slutligt lage
Write-Header "STEG 3 -- verifiera MI:s roller"
Write-Line "MI:s rolltilldelningar (alla scope):"
$all = az role assignment list --assignee $MiPrincipalId --all `
    --query "[].{roll:roleDefinitionName, scope:scope}" -o table 2>$null
if ($all) { foreach ($line in $all) { Write-Line ("     " + $line) } }
else { Write-Line "     (inga returnerade -- kontrollera ovan FAIL)" }

# Sammanfattning
Write-Header "RESULTATSAMMANFATTNING"
$anyFail = $false
foreach ($k in $results.Keys) {
    Write-Line ("  " + $results[$k].PadRight(7) + " " + $k)
    if ($results[$k] -eq "FAIL") { $anyFail = $true }
}
Write-Line ""
if ($anyFail) {
    Write-Line "SLUTSATS: Minst ett FAIL. Om villkorfel pa rolltilldelning -> RG-agaren"
    Write-Line "          behovs for just det (constrained delegation vi flaggade)."
} else {
    Write-Line "SLUTSATS: MI:n har nu exakt de roller orchestratorn behover. Redo for blob.py-test."
}
Write-Line ("Loggfil: " + $logFile)

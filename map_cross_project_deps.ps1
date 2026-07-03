# =====================================================================================
# map_cross_project_deps.ps1
# -------------------------------------------------------------------------------------
# Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia)
#
# SYFTE: Kartlägg korsprojekt-beroenden FÖRE städning i C:\Projekt\Business_Analytics.
#   Read-only. Rör ingenting. Skriver bara en rapport till skärm + en textfil.
#
# VARFÖR ÅT DETTA HÅLL: Den farliga riktningen när du städar i Business_Analytics är
#   inte "vad beror BA på" utan "VAD PEKAR PÅ BA". Om du flyttar/döper om en BA-fil som
#   BCG importerar eller kör, går BCG sönder tyst (upptäcks först vid nästa körning).
#   Sektion A är därför huvudleveransen: allt i BCG som refererar andra projektfoldrar.
#   Sektion B är den omvända (BA→BCG) — en känd broms för SJÄLVA BA-städningen.
#   Sektion C fångar hårdkodade absoluta sökvägar (den vanligaste tysta fällan).
#
# BEROR PÅ: inget utöver PowerShell 5.1. Ingen VM, ingen Azure, ingen DW.
# VAD SOM BEROR PÅ DEN: din städsession i BA använder output som skyddskarta.
#
# ANVÄNDNING:
#   cd C:\Projekt\BCG
#   powershell -ExecutionPolicy Bypass -File .\map_cross_project_deps.ps1
#   (eller: . .\map_cross_project_deps.ps1  om execution policy tillåter)
#
# OUTPUT: skärm + C:\Projekt\_deps_map_<datum>.txt  (klistra hela filen tillbaka)
# =====================================================================================

$ErrorActionPreference = "Continue"

# --- Konfiguration: projektrötter ---------------------------------------------------
$ProjektRoot = "C:\Projekt"
$BCG         = Join-Path $ProjektRoot "BCG"
$BA          = Join-Path $ProjektRoot "Business_Analytics"
$Masters     = Join-Path $ProjektRoot "masters"
$Keijo       = Join-Path $ProjektRoot "Keijo"
$Bibliotek   = Join-Path $ProjektRoot "Bibliotek"

# Filtyper vi bryr oss om (kod + config + notebooks). Excel/parquet/bak exkluderas.
$Extensions = @("*.py","*.ps1","*.sql","*.ipynb","*.md","*.yml","*.yaml","*.json","*.cfg","*.ini","*.txt","*.bat")

# Mappar vi aldrig letar i (brus)
$SkipDirs = @("\.git\", "\.venv\", "\__pycache__\", "\node_modules\", "\.ipynb_checkpoints\", "\backup\", "\.bak")

$ts     = Get-Date -Format "yyyy-MM-dd-HHmm"
$OutFil = Join-Path $ProjektRoot "_deps_map_$ts.txt"

# --- Hjälpare -----------------------------------------------------------------------
function Write-Both { param([string]$Text) ; Write-Host $Text ; Add-Content -Path $OutFil -Value $Text -Encoding UTF8 }

function Get-CodeFiles {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return @() }
    Get-ChildItem -Path $Root -Recurse -File -Include $Extensions -ErrorAction SilentlyContinue |
        Where-Object {
            $p = $_.FullName
            -not ($SkipDirs | Where-Object { $p -like "*$_*" })
        }
}

function Rel { param([string]$Full,[string]$Base) ; return ($Full -replace [regex]::Escape("$Base\"), "") }

# --- Start --------------------------------------------------------------------------
Set-Content -Path $OutFil -Value "" -Encoding UTF8   # nollställ
Write-Both "====================================================================="
Write-Both " KORSPROJEKT-BEROENDEN — kartläggning för BA-städning"
Write-Both " Genererad: $ts   av map_cross_project_deps.ps1 (Jens Palmö)"
Write-Both " Rötter: BCG=$BCG"
Write-Both "         BA =$BA"
Write-Both "====================================================================="
Write-Both ""

# Verifiera att rötterna finns (mät, gissa inte)
Write-Both "--- Rot-inventering (finns foldrarna?) ---"
foreach ($pair in @(@("BCG",$BCG),@("Business_Analytics",$BA),@("masters",$Masters),@("Keijo",$Keijo),@("Bibliotek",$Bibliotek))) {
    $exists = if (Test-Path $pair[1]) { "FINNS" } else { "SAKNAS" }
    Write-Both ("  {0,-20} {1,-8} {2}" -f $pair[0], $exists, $pair[1])
}
Write-Both ""

$bcgFiles = Get-CodeFiles -Root $BCG
$baFiles  = Get-CodeFiles -Root $BA
Write-Both ("Kodfiler i BCG (exkl git/venv/cache): {0}" -f $bcgFiles.Count)
Write-Both ("Kodfiler i BA  (exkl git/venv/cache): {0}" -f $baFiles.Count)
Write-Both ""

# =====================================================================================
# SEKTION A — HUVUDLEVERANS: allt i BCG som refererar andra projektfoldrar
#   Detta är kartan din BA-städning måste respektera. Varje träff = en BA-fil (eller
#   annan folder) som BCG är beroende av. Flytta/döp inte om dessa utan att fixa BCG.
# =====================================================================================
Write-Both "====================================================================="
Write-Both " SEKTION A — BCG-filer som pekar UT mot andra projektfoldrar  [KRITISK]"
Write-Both "   (dessa referenser går sönder om du flyttar målet i BA-städningen)"
Write-Both "====================================================================="

# Mönster som avslöjar korsprojekt-referens. Både namngivna moduler och sökvägar.
$patterns = @(
    'Business_Analytics',            # explicit foldernamn
    'data_access',                   # känd delad modul
    'export_b4b_for_model',          # känd delad extraktor
    'compare_to_0828',               # känd validator i BA
    'validate_dw_codelevel',         # känd validator i BA
    'regenerate_transaction_parquet',# parquet-regen (survival-buggen)
    'b4b_dw_weekly',                 # SQL-designdok i BA
    '\.\.\\Business',                # relativ sökväg uppåt mot BA
    '\.\.\/Business',                # relativ sökväg uppåt (unix-slash)
    'C:\\Projekt\\Business',         # hårdkodad absolut mot BA
    'C:\\Projekt\\masters',          # hårdkodad mot masters
    'C:\\Projekt\\Keijo',            # hårdkodad mot Keijo (ska vara 0 — referens-only)
    'C:\\Projekt\\Bibliotek'         # hårdkodad mot Bibliotek (under avveckling)
)
$patternRegex = ($patterns -join '|')

$hitsA = @()
foreach ($f in $bcgFiles) {
    $matches = Select-String -Path $f.FullName -Pattern $patternRegex -AllMatches -ErrorAction SilentlyContinue
    if ($matches) {
        foreach ($m in $matches) {
            $hitsA += [PSCustomObject]@{
                File = (Rel $f.FullName $BCG)
                Line = $m.LineNumber
                Text = $m.Line.Trim()
            }
        }
    }
}

if ($hitsA.Count -eq 0) {
    Write-Both "  (inga träffar — antingen rent, eller så använder BCG bara data via Blob/CSV utan kodreferens)"
} else {
    Write-Both ("  {0} referens-rader i {1} unika filer:" -f $hitsA.Count, ($hitsA.File | Select-Object -Unique).Count)
    Write-Both ""
    foreach ($grp in ($hitsA | Group-Object File | Sort-Object Name)) {
        Write-Both ("  >> {0}" -f $grp.Name)
        foreach ($h in $grp.Group) {
            $t = $h.Text ; if ($t.Length -gt 110) { $t = $t.Substring(0,107) + "..." }
            Write-Both ("       L{0,-5} {1}" -f $h.Line, $t)
        }
    }
}
Write-Both ""

# Sammanfattning: vilka BA-mål refereras (så du vet exakt vad som är rört-i-sten)
Write-Both "  --- Sammanfattning: vilka namngivna BA-objekt refereras av BCG? ---"
$targets = @("data_access","export_b4b_for_model","compare_to_0828","validate_dw_codelevel","regenerate_transaction_parquet","b4b_dw_weekly")
foreach ($tg in $targets) {
    $c = ($hitsA | Where-Object { $_.Text -match $tg }).Count
    $flag = if ($c -gt 0) { "<-- BCG BEROR AV DENNA, rör försiktigt" } else { "" }
    Write-Both ("     {0,-35} {1,3} träffar  {2}" -f $tg, $c, $flag)
}
Write-Both ""

# =====================================================================================
# SEKTION B — OMVÄNT: BA-filer som pekar mot BCG  [broms för BA-städningen]
#   Detta gör att BA inte är fristående — du kan inte flytta BA-struktur fritt.
#   Känd tråd från tidigare: ~11 filer. Mät det faktiska antalet nu.
# =====================================================================================
Write-Both "====================================================================="
Write-Both " SEKTION B — BA-filer som pekar mot BCG  [BROMS för BA-städningen]"
Write-Both "   (BA är inte fristående; dessa gör att BA-omstrukturering är låst)"
Write-Both "====================================================================="

$bMatch = 'C:\\Projekt\\BCG|\.\.\\BCG|\.\.\/BCG|02\. Elasticity|Pipeline\\02|evbcgpricing|verify_tool|orchestration\\'
$hitsB = @()
foreach ($f in $baFiles) {
    $matches = Select-String -Path $f.FullName -Pattern $bMatch -AllMatches -ErrorAction SilentlyContinue
    if ($matches) {
        foreach ($m in $matches) {
            $hitsB += [PSCustomObject]@{ File=(Rel $f.FullName $BA); Line=$m.LineNumber; Text=$m.Line.Trim() }
        }
    }
}
if ($hitsB.Count -eq 0) {
    Write-Both "  (inga — BA refererar inte BCG i kod. Då är BA-städning friare än väntat.)"
} else {
    Write-Both ("  {0} rader i {1} unika BA-filer pekar mot BCG:" -f $hitsB.Count, ($hitsB.File | Select-Object -Unique).Count)
    Write-Both ""
    foreach ($grp in ($hitsB | Group-Object File | Sort-Object Name)) {
        Write-Both ("  >> {0}" -f $grp.Name)
        foreach ($h in $grp.Group) {
            $t = $h.Text ; if ($t.Length -gt 110) { $t = $t.Substring(0,107) + "..." }
            Write-Both ("       L{0,-5} {1}" -f $h.Line, $t)
        }
    }
}
Write-Both ""

# =====================================================================================
# SEKTION C — HÅRDKODADE ABSOLUTA SÖKVÄGAR (den vanligaste tysta fällan)
#   Alla C:\Projekt\... och C:\Users\... i båda projekten. Absoluta sökvägar överlever
#   inte flytt och är osynliga tills körning. Detta är där städning oftast smäller.
# =====================================================================================
Write-Both "====================================================================="
Write-Both " SEKTION C — Hårdkodade absoluta sökvägar (BCG + BA)  [TYST FÄLLA]"
Write-Both "====================================================================="

$absPattern = 'C:\\Projekt\\|C:\\Users\\|OneDrive'
foreach ($root in @(@("BCG",$bcgFiles),@("BA",$baFiles))) {
    Write-Both ("  --- {0} ---" -f $root[0])
    $hitsC = @()
    foreach ($f in $root[1]) {
        $matches = Select-String -Path $f.FullName -Pattern $absPattern -AllMatches -ErrorAction SilentlyContinue
        if ($matches) {
            foreach ($m in $matches) {
                $baseRoot = if ($root[0] -eq "BCG") { $BCG } else { $BA }
                $hitsC += [PSCustomObject]@{ File=(Rel $f.FullName $baseRoot); Line=$m.LineNumber; Text=$m.Line.Trim() }
            }
        }
    }
    if ($hitsC.Count -eq 0) {
        Write-Both "     (inga absoluta sökvägar — bra, allt via env/relativt)"
    } else {
        Write-Both ("     {0} absoluta sökvägar i {1} filer:" -f $hitsC.Count, ($hitsC.File | Select-Object -Unique).Count)
        foreach ($grp in ($hitsC | Group-Object File | Sort-Object Name)) {
            Write-Both ("     >> {0}  ({1} st)" -f $grp.Name, $grp.Count)
            foreach ($h in ($grp.Group | Select-Object -First 6)) {
                $t = $h.Text ; if ($t.Length -gt 100) { $t = $t.Substring(0,97) + "..." }
                Write-Both ("          L{0,-5} {1}" -f $h.Line, $t)
            }
            if ($grp.Count -gt 6) { Write-Both ("          ... +{0} till" -f ($grp.Count - 6)) }
        }
    }
    Write-Both ""
}

# =====================================================================================
# SEKTION D — UNTRACKED I BA (survival-risk: BCG anropar fil som git inte känner)
#   Om run_data.py anropar ett skript som ligger untracked i BA, går en frisk BA-klon
#   sönder. Kräver git. Körs bara om BA är ett git-repo.
# =====================================================================================
Write-Both "====================================================================="
Write-Both " SEKTION D — Untracked filer i BA som BCG kan anropa  [SURVIVAL-RISK]"
Write-Both "====================================================================="
if (Test-Path (Join-Path $BA ".git")) {
    Push-Location $BA
    $untracked = git ls-files --others --exclude-standard 2>$null
    Pop-Location
    if ($untracked) {
        Write-Both ("  {0} untracked filer i BA. Korsa mot BCG-referenser (Sektion A) —" -f ($untracked | Measure-Object).Count)
        Write-Both "  en untracked BA-fil som BCG anropar = frisk klon går sönder (survival-bugg):"
        foreach ($u in $untracked) {
            # flagga om filnamnet dyker upp i någon BCG-referens
            $base = [System.IO.Path]::GetFileNameWithoutExtension($u)
            $refByBCG = ($hitsA | Where-Object { $_.Text -match [regex]::Escape($base) }).Count
            $flag = if ($refByBCG -gt 0) { "  <== ANROPAS AV BCG, KRITISK survival-risk" } else { "" }
            Write-Both ("     {0}{1}" -f $u, $flag)
        }
    } else {
        Write-Both "  (inga untracked filer i BA — rent)"
    }
} else {
    Write-Both "  (BA är inte ett git-repo på denna sökväg — hoppar över untracked-koll)"
}
Write-Both ""

# --- Slutsummering ------------------------------------------------------------------
Write-Both "====================================================================="
Write-Both " KLART. Rapport sparad: $OutFil"
Write-Both " Klistra HELA filen tillbaka så bygger vi städ-checklistan på fakta."
Write-Both "====================================================================="

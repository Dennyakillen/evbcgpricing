<#
.SYNOPSIS
    Strukturkartläggning av BCG-projektmappen för replikeringsarbetet.

.DESCRIPTION
    Mappen innehåller >50 000 filer, varav merparten är venv/site-packages och
    Git-objekt. Detta skript klipper bort de tunga underträden och rapporterar
    PRIMÄRT mappstrukturen plus en riktad inventering av de filer som faktiskt
    styr pipelinen (config, requirements, runners, SQL, modeller, Alteryx-rester).

    Skriptet läser ENDAST metadata (namn, storlek, datum) via Get-ChildItem och
    öppnar aldrig filinnehåll. Det hydrerar därför inte OneDrive-only-filer.

    En not om kommentarer: KÄRNPRINCIPER §5 förbjuder #-kommentarer i KLISTRADE
    körblock (PowerShell tolkar varje rad separat vid inklistring i terminalen).
    I en sparad .ps1 som körs med .\skript.ps1 parsas filen som helhet — kommentarer
    är då standard och ofarliga, och hjälper förvaltningen. Inklistringsregeln gäller
    invokationsblocket nedan, som därför är kommentarsfritt.

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass -Force
    cd "C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG"
    .\Scan-BCGFolder.ps1

    (Process-scope rör inte registret och gäller bara denna terminalsession.)

.NOTES
    Jens Palmö (utvecklare), 2026-05-20.
#>

[CmdletBinding()]
param(
    [string]$Root = "C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG",
    [int]$MaxTreeDepth = 3,
    [string]$OutFile = $null
)

$ErrorActionPreference = 'Continue'

if (-not (Test-Path -LiteralPath $Root)) {
    Write-Host "FEL: roten finns inte: $Root" -ForegroundColor Red
    return
}
if (-not $OutFile) { $OutFile = Join-Path $PSScriptRoot 'BCG_STRUCTURE_REPORT.md' }

# Mappnamn vars hela underträd hoppas över (artefakter, inte källkod)
$PruneDirs = @('venv','.venv','env','.env','.git','__pycache__','.ipynb_checkpoints',
               'node_modules','dist','build','.mypy_cache','.pytest_cache',
               'site-packages','.ruff_cache','ray_session')

# Filmönster som är intressanta för replikeringen (-like, skiftlägesokänsligt)
$KeyPatterns = @(
    'config.yml','config.yaml','requirements*.txt','run.ps1','run.bat','launcher.py',
    '*.yxmd','*.yxdb','duckdb.exe','*.sql',
    '*Pricing*Model*.xlsx','*Final*Model*.xlsx','output_summary*.xlsx','*Fallback*.xlsx',
    '*Cluster*Mapping*.csv','Updated_site_cluster.csv','*Interpolated_Productivity*.csv',
    'Fall_Back_Logic.py','*Productive_Time*.py','*regular_price*.py','*feature_selection*.py',
    '*data_prep*.py','*Clustering*.py','*Data_Preparation*.py'
)

# Modulglobala ackumulatorer
$script:Ext       = @{}
$script:KeyHits   = New-Object System.Collections.Generic.List[object]
$script:Pruned    = New-Object System.Collections.Generic.List[object]
$script:Tree      = New-Object System.Collections.Generic.List[string]
$script:TopFolder = ''
$script:TopStats  = @{}

function Format-Size {
    param([double]$Bytes)
    if ($Bytes -ge 1GB) { return ('{0:N1} GB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N1} MB' -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ('{0:N0} KB' -f ($Bytes / 1KB)) }
    return ('{0} B' -f [int]$Bytes)
}

function Test-KeyFile {
    param([string]$Name)
    foreach ($p in $KeyPatterns) { if ($Name -like $p) { return $true } }
    return $false
}

function Walk {
    param([string]$Path, [int]$Depth)

    $children = Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    $dirs  = @($children | Where-Object { $_.PSIsContainer })
    $files = @($children | Where-Object { -not $_.PSIsContainer })

    foreach ($f in $files) {
        $fileExt = if ($f.Extension) { $f.Extension.ToLower() } else { '(ingen)' }
        if ($script:Ext.ContainsKey($fileExt)) {
            $script:Ext[$fileExt].Count++
            $script:Ext[$fileExt].Bytes += [int64]$f.Length
        } else {
            $script:Ext[$fileExt] = [pscustomobject]@{ Count = 1; Bytes = [int64]$f.Length }
        }
        $script:TopStats[$script:TopFolder].Count++
        $script:TopStats[$script:TopFolder].Bytes += [int64]$f.Length
        if ($f.LastWriteTime -gt $script:TopStats[$script:TopFolder].Last) {
            $script:TopStats[$script:TopFolder].Last = $f.LastWriteTime
        }
        if (Test-KeyFile $f.Name) {
            $rel = $f.FullName.Substring($Root.Length).TrimStart('\')
            $script:KeyHits.Add([pscustomobject]@{
                Path = $rel; Size = (Format-Size $f.Length); Modified = $f.LastWriteTime.ToString('yyyy-MM-dd')
            })
        }
    }

    foreach ($d in $dirs | Sort-Object Name) {
        if ($PruneDirs -contains $d.Name) {
            $rel = $d.FullName.Substring($Root.Length).TrimStart('\')
            $script:Pruned.Add([pscustomobject]@{ Path = $rel; Name = $d.Name })
            continue
        }
        if ($Depth -le $MaxTreeDepth) {
            $indent = '  ' * $Depth
            $script:Tree.Add(('{0}- {1}/' -f $indent, $d.Name))
        }
        Walk -Path $d.FullName -Depth ($Depth + 1)
    }
}

Write-Host "Kartlägger: $Root" -ForegroundColor Cyan
Write-Host "Detta kan ta en stund (klipper bort venv/.git/site-packages)..." -ForegroundColor DarkGray

# Initiera topmapp-statistik på rotnivåns mappar
$topDirs = @(Get-ChildItem -LiteralPath $Root -Directory -Force -ErrorAction SilentlyContinue)
foreach ($t in $topDirs) {
    $script:TopStats[$t.Name] = [pscustomobject]@{ Count = 0; Bytes = [int64]0; Last = [datetime]'1900-01-01' }
}
$script:TopStats['(rotfiler)'] = [pscustomobject]@{ Count = 0; Bytes = [int64]0; Last = [datetime]'1900-01-01' }

# Rotfiler först
$script:TopFolder = '(rotfiler)'
$rootFiles = @(Get-ChildItem -LiteralPath $Root -File -Force -ErrorAction SilentlyContinue)
foreach ($f in $rootFiles) {
    $fileExt = if ($f.Extension) { $f.Extension.ToLower() } else { '(ingen)' }
    if ($script:Ext.ContainsKey($fileExt)) { $script:Ext[$fileExt].Count++; $script:Ext[$fileExt].Bytes += [int64]$f.Length }
    else { $script:Ext[$fileExt] = [pscustomobject]@{ Count = 1; Bytes = [int64]$f.Length } }
    $script:TopStats['(rotfiler)'].Count++
    $script:TopStats['(rotfiler)'].Bytes += [int64]$f.Length
    if (Test-KeyFile $f.Name) {
        $script:KeyHits.Add([pscustomobject]@{ Path = $f.Name; Size = (Format-Size $f.Length); Modified = $f.LastWriteTime.ToString('yyyy-MM-dd') })
    }
}

# Walk per topmapp
foreach ($t in $topDirs | Sort-Object Name) {
    if ($PruneDirs -contains $t.Name) {
        $script:Pruned.Add([pscustomobject]@{ Path = $t.Name; Name = $t.Name })
        continue
    }
    $script:TopFolder = $t.Name
    $script:Tree.Add(('- {0}/' -f $t.Name))
    Walk -Path $t.FullName -Depth 1
}

# Bygg rapport
$sb = New-Object System.Text.StringBuilder
$null = $sb.AppendLine('# BCG — strukturrapport')
$null = $sb.AppendLine('')
$null = $sb.AppendLine(('- **Rot:** `{0}`' -f $Root))
$null = $sb.AppendLine(('- **Genererad:** {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm')))
$null = $sb.AppendLine(('- **Maskin:** {0}' -f $env:COMPUTERNAME))
$null = $sb.AppendLine(('- **Träd-djup i rapporten:** {0} nivåer' -f $MaxTreeDepth))

$totalFiles = ($script:TopStats.Values | Measure-Object -Property Count -Sum).Sum
$totalBytes = ($script:TopStats.Values | Measure-Object -Property Bytes -Sum).Sum
$null = $sb.AppendLine(('- **Filer (exkl. bortklippt):** {0:N0}  ·  **Storlek:** {1}' -f $totalFiles, (Format-Size $totalBytes)))
$null = $sb.AppendLine('')

$null = $sb.AppendLine('## Toppmappar')
$null = $sb.AppendLine('')
$null = $sb.AppendLine('| Mapp | Filer | Storlek | Senast ändrad |')
$null = $sb.AppendLine('|---|---:|---:|---|')
foreach ($k in ($script:TopStats.Keys | Sort-Object)) {
    $s = $script:TopStats[$k]
    if ($s.Count -eq 0) { continue }
    $last = if ($s.Last -gt [datetime]'1900-01-01') { $s.Last.ToString('yyyy-MM-dd') } else { '-' }
    $null = $sb.AppendLine(('| {0} | {1:N0} | {2} | {3} |' -f $k, $s.Count, (Format-Size $s.Bytes), $last))
}
$null = $sb.AppendLine('')

$null = $sb.AppendLine('## Mappträd')
$null = $sb.AppendLine('')
$null = $sb.AppendLine('```')
foreach ($line in $script:Tree) { $null = $sb.AppendLine($line) }
$null = $sb.AppendLine('```')
$null = $sb.AppendLine('')

$null = $sb.AppendLine('## Filtyper')
$null = $sb.AppendLine('')
$null = $sb.AppendLine('| Ändelse | Antal | Storlek |')
$null = $sb.AppendLine('|---|---:|---:|')
foreach ($e in ($script:Ext.GetEnumerator() | Sort-Object { $_.Value.Count } -Descending)) {
    $null = $sb.AppendLine(('| {0} | {1:N0} | {2} |' -f $e.Key, $e.Value.Count, (Format-Size $e.Value.Bytes)))
}
$null = $sb.AppendLine('')

$null = $sb.AppendLine(('## Nyckelfiler ({0} träffar)' -f $script:KeyHits.Count))
$null = $sb.AppendLine('')
$null = $sb.AppendLine('Filer som styr pipelinen: config, requirements, runners, SQL, modeller, Alteryx-rester.')
$null = $sb.AppendLine('')
$null = $sb.AppendLine('| Fil (relativ sökväg) | Storlek | Ändrad |')
$null = $sb.AppendLine('|---|---:|---|')
foreach ($h in ($script:KeyHits | Sort-Object Path)) {
    $null = $sb.AppendLine(('| {0} | {1} | {2} |' -f $h.Path, $h.Size, $h.Modified))
}
$null = $sb.AppendLine('')

$null = $sb.AppendLine('## Bortklippta underträd (venv, .git, site-packages m.fl.)')
$null = $sb.AppendLine('')
if ($script:Pruned.Count -eq 0) {
    $null = $sb.AppendLine('Inga.')
} else {
    $null = $sb.AppendLine('| Bortklippt mapp | Namn |')
    $null = $sb.AppendLine('|---|---|')
    foreach ($p in ($script:Pruned | Sort-Object Path)) {
        $null = $sb.AppendLine(('| {0} | {1} |' -f $p.Path, $p.Name))
    }
}
$null = $sb.AppendLine('')

# Skriv UTF-8 utan BOM (MASTER_PYTHON L.13 — undvik mojibake på å/ä/ö)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($OutFile, $sb.ToString(), $utf8NoBom)

Write-Host ''
Write-Host ('Klart. {0:N0} filer kartlagda (exkl. bortklippt).' -f $totalFiles) -ForegroundColor Green
Write-Host ('Nyckelfiler hittade: {0}' -f $script:KeyHits.Count) -ForegroundColor Green
Write-Host ('Bortklippta underträd: {0}' -f $script:Pruned.Count) -ForegroundColor Green
Write-Host ('Rapport: {0}' -f $OutFile) -ForegroundColor Cyan

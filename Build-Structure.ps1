<#
.SYNOPSIS
    Phase 1a - build a faithful, empty folder skeleton from the BCG V2_New tree.

.DESCRIPTION
    Mirrors the DIRECTORY structure (folders only, no files) of the consultant
    source of truth (BCG_orginal_V2_New) for "01. Clustering" and "02. Elasticity"
    into a clean working root. File content is copied separately by Copy-Sources.ps1.

    Names are kept identical to the consultant tree (spaces and numbering preserved)
    so a reader can map 1:1 to the original documentation. We are out of OneDrive now,
    so spaces in paths are no longer a problem.

    This script is pure ASCII. The Swedish letter in the OneDrive path is generated at
    runtime via [char]0x00E5, because PowerShell 5.1 reads UTF-8 script files as CP1252
    and would otherwise mangle a literal 'a-ring' (this is the bug that produced mojibake
    in the structure report). Lesson applied.

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass -Force
    . 'C:\Projekt\BCG\Build-Structure.ps1'

.NOTES
    Jens Palmo (developer), 2026-05-20. Phase 1a of the BCG replication playbook.
#>

[CmdletBinding()]
param(
    [string]$TargetRoot = "C:\Projekt\BCG\Pipeline",
    [string[]]$Subtrees = @("01. Clustering", "02. Elasticity")
)

$ErrorActionPreference = 'Continue'

$aring   = [char]0x00E5
$bcgRoot = "C:\Users\jepa02\OneDrive - Evidensia Djursjukv${aring}rd AB\Datastrategi\BCG"
$source  = Join-Path $bcgRoot "BCG_orginal_V2_New"

$prune = @('venv', '.venv', 'env', '__pycache__', '.git', '.ipynb_checkpoints')

if (-not (Test-Path -LiteralPath $source)) {
    Write-Host "ERROR: source not found: $source" -ForegroundColor Red
    return
}

Write-Host "Building skeleton under: $TargetRoot" -ForegroundColor Cyan
Write-Host "Source of truth        : $source" -ForegroundColor DarkGray

$created = 0
$null = New-Item -ItemType Directory -Path $TargetRoot -Force

foreach ($sub in $Subtrees) {
    $base = Join-Path $source $sub
    if (-not (Test-Path -LiteralPath $base)) {
        Write-Host "  SKIP (missing): $sub" -ForegroundColor Yellow
        continue
    }

    $null = New-Item -ItemType Directory -Path (Join-Path $TargetRoot $sub) -Force
    $created++

    $dirs = Get-ChildItem -LiteralPath $base -Recurse -Directory -Force -ErrorAction SilentlyContinue
    foreach ($d in $dirs) {
        $segments = $d.FullName.Split('\')
        $skip = $false
        foreach ($seg in $segments) { if ($prune -contains $seg) { $skip = $true; break } }
        if ($skip) { continue }

        $rel = $d.FullName.Substring($source.Length).TrimStart('\')
        $dest = Join-Path $TargetRoot $rel
        if (-not (Test-Path -LiteralPath $dest)) {
            $null = New-Item -ItemType Directory -Path $dest -Force
            $created++
        }
    }
}

Write-Host ""
Write-Host ("Skeleton built. Directories created: {0}" -f $created) -ForegroundColor Green
Write-Host "Next: run Copy-Sources.ps1 to populate the structure." -ForegroundColor Cyan

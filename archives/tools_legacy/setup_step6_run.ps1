<#
=====================================================================
 setup_step6_run.ps1
 ---------------------------------------------------------------------
 Builds a faithful, minimal working copy of BCG's step 6 (Fall Back
 Logic) OUTSIDE the OneDrive original, so the original stays untouched
 as facit. Copies ONLY the 7 files step 6 actually reads/needs, in the
 exact directory geometry that Constant.py + Fall_Back_Logic.py expect.

 Path anchoring in the BCG code (why the geometry matters):
   - The 4 model files resolve against base_dir = __file__.parent.parent
     (= the "02. Elasticity" root).
   - df_all_product_path (.\input_data\) and df_product_path
     (.\output_data\) resolve against the CURRENT WORKING DIRECTORY,
     so the script MUST be run from the "6. Fall Back Logic" folder.

 Developer: Jens Palmo
 Run in: PowerShell, locally, no venv needed (file copy only).
=====================================================================
#>

$ErrorActionPreference = "Stop"

$orig = "C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New\02. Elasticity"
$work = "C:\Projekt\BCG\_step6_run\02. Elasticity"

Write-Host "Source (original, read-only):" $orig
Write-Host "Target (working copy):       " $work
Write-Host ""

$dirs = @(
    "$work\2. Product Cluster Level Models\output",
    "$work\3. Product Site Level Models\output\model",
    "$work\5. Bundle Clinic Models\output\model",
    "$work\Excel_Outputs",
    "$work\6. Fall Back Logic\input_data",
    "$work\6. Fall Back Logic\output_data"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

$copies = @(
    @{ Src = "$orig\2. Product Cluster Level Models\output\final_model_cluster_granularity.xlsx"; Dst = "$work\2. Product Cluster Level Models\output\final_model_cluster_granularity.xlsx" },
    @{ Src = "$orig\2. Product Cluster Level Models\output\output_summary_ready.xlsx";            Dst = "$work\2. Product Cluster Level Models\output\output_summary_ready.xlsx" },
    @{ Src = "$orig\3. Product Site Level Models\output\model\output_summary.xlsx";               Dst = "$work\3. Product Site Level Models\output\model\output_summary.xlsx" },
    @{ Src = "$orig\5. Bundle Clinic Models\output\model\output_summary.xlsx";                    Dst = "$work\5. Bundle Clinic Models\output\model\output_summary.xlsx" },
    @{ Src = "$orig\Excel_Outputs\Sweden_Fallback.xlsx";                                          Dst = "$work\Excel_Outputs\Sweden_Fallback.xlsx" },
    @{ Src = "$orig\6. Fall Back Logic\input_data\Complete_Product_Data.xlsx";                     Dst = "$work\6. Fall Back Logic\input_data\Complete_Product_Data.xlsx" },
    @{ Src = "$orig\6. Fall Back Logic\Fall_Back_Logic.py";                                        Dst = "$work\6. Fall Back Logic\Fall_Back_Logic.py" },
    @{ Src = "$orig\6. Fall Back Logic\Constant.py";                                               Dst = "$work\6. Fall Back Logic\Constant.py" },
    @{ Src = "$orig\6. Fall Back Logic\Readme.md";                                                 Dst = "$work\6. Fall Back Logic\Readme.md" }
)

$missing = @()
foreach ($c in $copies) {
    if (Test-Path $c.Src) {
        Copy-Item -Path $c.Src -Destination $c.Dst -Force
        "{0,12:N0}  COPIED  {1}" -f (Get-Item $c.Dst).Length, (Split-Path $c.Dst -Leaf)
    } else {
        $missing += $c.Src
        "          --  MISSING SOURCE  {0}" -f $c.Src
    }
}

Write-Host ""
if ($missing.Count -eq 0) {
    Write-Host "All 9 files copied. Working folder is ready." -ForegroundColor Green
    Write-Host "The original was only read, never written." -ForegroundColor Green
} else {
    Write-Host "WARNING: $($missing.Count) source file(s) missing - do NOT run step 6 until resolved." -ForegroundColor Yellow
}

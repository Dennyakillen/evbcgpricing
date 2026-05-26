Sweden_Elasticity_SQL/
├─ input/                    # put all source CSVs here (see file names below)
├─ output/                       # results are written here
├─ scripts/
│  ├─ duckdb.exe                 # (Windows portable) included if packaged
│  ├─ run.ps1                    # main runner for Windows PowerShell
│  ├─ 00_setup.sql               # (optional) pragma/settings
│  ├─ 10_ingest.sql              # reads all CSVs from input_csv/
│  ├─ 20_process.sql             # all transforms, diagnostics, joins
│  └─ 30_export.sql              # writes CSV, Parquet (and Excel via PS)
├─ duckdb.db                     # DuckDB database file (created on first run)
└─ README.md                     # this file


--> Input files: expected names (put in input_csv/)

These names are referenced by the SQL. Use exact file names (case-insensitive on Windows):
1. loc.Dim_Department.csv -- Sweden Department Dimension Data
2. loc.Dim_Item 20250627 -- Sweden Item Dimension Data
3. transaction_data.parquet -- Sweden transaction data
4. Sweden_Clinic_Cluster_Mapping.csv -- Sweden Clinic Cluster mapping for inscope
5. Updated_site_cluster.csv -- Sweden updated Clinic Cluster mapping for all sites.
6. Sweden_Interpolated_Productivity_time.csv -- Sweden clinic week level, vet working hours

Note: 
1. If your files have different names, either rename them or update table names in scripts/10_ingest.sql accordingly.
2. Also, data prepared by Sweden_FallbackLogic_data_prep.yxdb workflow is been created in these script named Comple_Product_Data. Please copy and paste it in the folder 06.Fall Back Logic>>input_data


--> Executing the pipeline:

Quick start (by OS)
Windows (PowerShell)

Open Windows PowerShell (or Windows Terminal → PowerShell).

cd into the project folder:

cd "location of this folder"


## Only in case of restrictions: (First time only) allow local scripts:

## Set-ExecutionPolicy -Scope CurrentUser RemoteSigned


Run by typing the following in PowerShell:

.\scripts\run.ps1


You’ll see diagnostic tables printed. Outputs land in output folder
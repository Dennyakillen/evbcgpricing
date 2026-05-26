Canada_Clustering_SQL/
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
1. sweden_bundle_analysis.csv -- Sweden bundles information
2. Sweden_Clinic_Cluster_Mapping.csv -- Sweden Clustering data
3. Sweden_Interpolated_Productivity_time.csv -- Sweden clinic week level, vet working hours
4. vet_working_in_use.csv -- Sweden Master raw data with select columns and columns seperated by pipe operater (|)

Note: If your files have different names, either rename them or update table names in scripts/10_ingest.sql accordingly.


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
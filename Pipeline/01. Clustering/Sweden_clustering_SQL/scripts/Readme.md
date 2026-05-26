Sweden_Clustering_SQL/
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
2. Sweden_Hospitals_geodata.csv -- Sweden Geo data
3. Sweden_Hospitals_cluster_business_area_mapping.csv -- Sweden Area and department mapping data
4. Sweden_Competitor_data.csv -- Sweden Competitor data
5. Sweden_Competitor_Analysis.csv -- Sweden Competitor Attributes Data.
6. Sweden_Interpolated_Productivity_time.csv -- Sweden clinic week level, vet working hours
7. beta.FACT_FullTimeEquivalentKPIsByCompanyAndCostCode.csv -- Sweden Vet working FTE data.
8. NPS_Data_SE.csv -- Sweden NPS data.
9. sweden_master_data.parquet -- Sweden master data in parquet format.


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
PRAGMA enable_object_cache;

-- =========================
-- Folders (adjust if needed)
-- =========================
CREATE OR REPLACE MACRO INPUT_DIR()  AS 'input';
CREATE OR REPLACE MACRO OUTPUT_DIR() AS 'output';
CREATE OR REPLACE MACRO PARQUET_DIR() AS 'parquet';  

-- =========================
-- 1) Master fact (CSV)
-- =========================
-- DROP TABLE IF EXISTS sweden_master_data;
-- CREATE TABLE sweden_master_data AS
-- SELECT *
-- FROM read_csv(
--   INPUT_DIR() || '/sweden_master_data.csv',
--   columns = {
--     'ID_Customer': 'BIGINT',
--     'ID_Department': 'BIGINT',
--     'ID_User': 'BIGINT',
--     'ID_Item': 'BIGINT',
--     'ID_Patient': 'BIGINT',
--     'InvoiceDate': 'DATE',
--     'NoofUnits': 'DOUBLE',
--     'Unit': 'VARCHAR',
--     'SalesTotal': 'BIGINT',
--     'SoldQuantity': 'DOUBLE',
--     'PercentageChange': 'DOUBLE',
--     'PatientSinceDate': 'DATE',
--     'CustomerSinceDate': 'DATE',
--     'ItemDescription': 'VARCHAR',
--     'ItemType': 'VARCHAR',
--     'Price': 'DOUBLE',
--     'ItemCode': 'VARCHAR',
--     'ProductGroupL4Name': 'VARCHAR',
--     'CostCenterCode': 'BIGINT',
--     'BusinessArea': 'VARCHAR',
--     'InvoiceMonth': 'BIGINT',
--     'InvoiceYear': 'BIGINT',
--     'VisitID': 'VARCHAR',
--     'YearFlag': 'VARCHAR'
--   },
--   header = true, dateformat = '%Y-%m-%d', sep = '|', nullstr = ['', 'NULL'],
--   encoding='UTF-8', strict_mode=false, null_padding=true
-- );

-- -- Optional: count rows for verification
-- SELECT 'sweden_master_data' AS msg, COUNT(*) AS rows FROM sweden_master_data;

-- -- -- Write flat Parquet (no partitions)
-- COPY sweden_master_data
-- TO (PARQUET_DIR() || '/sweden_master_data.parquet')
-- WITH (FORMAT PARQUET, COMPRESSION ZSTD);


-- =====================================================================
-- === SUBSEQUENT RUNS (Parquet only) ==================================
-- After first run, keep ONLY ONE of the following CREATE VIEW lines.
-- =====================================================================

-- NO-PARTITION read (use this if you wrote to ..._nopart above)
DROP TABLE IF EXISTS sweden_master_data;
CREATE TABLE sweden_master_data AS
SELECT * FROM read_parquet(PARQUET_DIR() || '/sweden_master_data.parquet');
SELECT 'sweden_master_data' AS msg, COUNT(*) AS rows FROM sweden_master_data;

-- -- =========================
-- -- 2) Lookups (CSV)
-- -- =========================

DROP TABLE IF EXISTS sweden_cluster;
CREATE TABLE sweden_cluster AS
SELECT *
FROM read_csv(
  INPUT_DIR() || '/Sweden_Clinic_Cluster_Mapping.csv',
  columns = {"ID_Department":"INT",
             "Cluster":"VARCHAR",
             "New_Cluster":"VARCHAR"
  },
  header = true, sep = ',', nullstr = ['', 'NULL']
);
SELECT 'sweden_cluster' AS msg, COUNT(*) AS rows FROM sweden_cluster;

-- Drop table if it already exists
DROP TABLE IF EXISTS sweden_bundles;

-- Create table from the new CSV
CREATE TABLE sweden_bundles AS
SELECT *
FROM read_csv(
  INPUT_DIR() || '/sweden_bundle_analysis.csv',
  columns = {
    "Bundle":"VARCHAR",
    "Products":"INT",
    "Visits":"INT",
    "Quantity":"DOUBLE",
    "Revenue":"DOUBLE",
    "PricePerQuantity":"DOUBLE",
    "PricePerVisit":"DOUBLE",
    "BundleRevenueSorted":"VARCHAR",
    "BundleRevenueSorted_ItemDescription":"VARCHAR",
    "TA_BORT_Flag":"INT",
    "Surgery_Imaging_Hospitalization_Flag":"INT",
    "Surgery_Imaging_Hospitalization_Anesthetic_Flag":"INT",
    "Emergency_Flag":"INT",
    "To_run_elasticity_analysis":"INT"    
  },
  header = true, sep = ',', nullstr = ['', 'NULL']
);

-- Optional: count rows for verification
SELECT 'Sweden_Bundles' AS msg, COUNT(*) AS rows FROM sweden_bundles;


DROP TABLE IF EXISTS Sweden_Interpolated_Productivity_time;
-- Create table from the new CSV
CREATE TABLE Sweden_Interpolated_Productivity_time AS
SELECT *
FROM read_csv(
  INPUT_DIR() || '/Sweden_Interpolated_Productivity_time.csv',
  columns = {
    "Cluster":"VARCHAR",
    "week_starting_monday":"DATETIME",
    "FTE_Interpolated":"DOUBLE",
    "ID_Department":"INT",
  },
  header = true, dateformat = '%Y-%m-%d', sep = ',', nullstr = ['', 'NULL']
);

-- Optional: count rows for verification
SELECT 'Sweden_Interpolated_Productivity_time' AS msg, COUNT(*) AS rows FROM Sweden_Interpolated_Productivity_time;
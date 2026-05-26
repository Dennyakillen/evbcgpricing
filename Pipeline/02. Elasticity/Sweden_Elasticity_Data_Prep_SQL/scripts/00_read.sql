PRAGMA enable_object_cache;

-- =========================
-- Folders (adjust if needed)
-- =========================
CREATE OR REPLACE MACRO INPUT_DIR()  AS 'input';
CREATE OR REPLACE MACRO OUTPUT_DIR() AS 'output';
CREATE OR REPLACE MACRO PARQUET_DIR() AS 'parquet';  


-- =========================
-- 1) Department Dimension  Data(CSV)
-- =========================
DROP TABLE IF EXISTS dim_Department;
CREATE TABLE dim_Department AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/loc.Dim_Department.csv',
  columns ={
    'ID_Department': 'BIGINT',
    'ProvetDescription': 'VARCHAR',
    'ID_ItemList': 'BIGINT',
    'DepartmentDescription': 'VARCHAR',
    'Group': 'VARCHAR',
    'CostCenterCode': 'BIGINT',
    'DepartmentType': 'VARCHAR',
    'BusinessAreaManager': 'VARCHAR',
    'DepartmentManager': 'VARCHAR',
    'ChiefVeterinarian': 'VARCHAR',
    'StoreManager': 'DOUBLE',
    'ReceptionManager': 'DOUBLE',
    'StreetAddress': 'VARCHAR',
    'ZipCode': 'VARCHAR',
    'City': 'VARCHAR',
    'NoofDaysOpen': 'DOUBLE',
    'RunDateDW': 'VARCHAR',
    'ByUser': 'VARCHAR',
    'BusinessArea': 'VARCHAR'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'dim_Department' AS msg, COUNT(*) AS rows FROM dim_Department;

-- =========================
-- 2) Item Dimension Data(CSV)
-- =========================
DROP TABLE IF EXISTS dim_Item;
CREATE TABLE dim_Item AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/loc.Dim_Item 20250627.csv',
  columns ={
    'ID_Item': 'BIGINT',
    'ID_ItemList': 'BIGINT',
    'ItemDescription': 'VARCHAR',
    'ItemType': 'VARCHAR',
    'ID_InvoiceGroup': 'VARCHAR',
    'InvoiceGroupDescription': 'VARCHAR',
    'AccountNumber': 'VARCHAR',
    'Price': 'VARCHAR',
    'PriceWithVAT': 'VARCHAR',
    'WholeSalePrice': 'VARCHAR',
    'IsAntibiotic': 'VARCHAR',
    'AntibioticGroup': 'VARCHAR',
    'RunDateDW': 'VARCHAR',
    'ByUser': 'VARCHAR',
    'Archived': 'VARCHAR',
    'ItemCode': 'VARCHAR',
    'MasterListItemType': 'VARCHAR',
    'MasterListItemListType': 'VARCHAR',
    'MasterListAssortmentType': 'VARCHAR',
    'MasterListMainCategory': 'VARCHAR',
    'MasterListSubCategory': 'VARCHAR',
    'Supplier': 'VARCHAR',
    'SubGroup': 'VARCHAR',
    'Streckkod': 'VARCHAR',
    'PurinaCategory': 'VARCHAR',
    'InPriceExVAT': 'VARCHAR',
    'OutPriceExVAT': 'VARCHAR',
    'Margin': 'VARCHAR',
    'EmergencyAndOnCall': 'VARCHAR',
    'IsDeleted': 'VARCHAR',
    'ProductGroupL1Name': 'VARCHAR',
    'ProductGroupL2Name': 'VARCHAR',
    'ProductGroupL3Name': 'VARCHAR',
    'ProductGroupL4Name': 'VARCHAR'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'dim_Item' AS msg, COUNT(*) AS rows FROM dim_Item;


-- =========================
-- 3) Transaction Data (parquet)
-- =========================

DROP TABLE IF EXISTS transaction_data;
CREATE TABLE transaction_data AS
SELECT * FROM read_parquet(PARQUET_DIR() || '/transaction_data.parquet');
SELECT 'transaction_data' AS msg, COUNT(*) AS rows FROM transaction_data;

-- -- =========================
-- 4) Sweden Cluster Data (CSV)
-- =========================
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



-- =========================
-- 5) Sweden Updated Site Cluster Data for Fallback(CSV)
-- =========================
DROP TABLE IF EXISTS sweden_cluster_fallback;
CREATE TABLE sweden_cluster_fallback AS
SELECT *
FROM read_csv(
  INPUT_DIR() || '/Updated_site_cluster.csv',
  columns = {"ID_Department":"INT",
             "Cluster":"VARCHAR",
             "New_Cluster":"VARCHAR"
  },
  header = true, sep = ',', nullstr = ['', 'NULL']
);
SELECT 'sweden_cluster_fallback' AS msg, COUNT(*) AS rows FROM sweden_cluster_fallback;


-- =========================
-- 6) Sweden Interpolated Data (CSV)
-- =========================
DROP TABLE IF EXISTS fte_weekly;
-- Create table from the new CSV
CREATE TABLE fte_weekly AS
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
SELECT 'fte_weekly' AS msg, COUNT(*) AS rows FROM fte_weekly;
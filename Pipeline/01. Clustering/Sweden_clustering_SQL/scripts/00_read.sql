PRAGMA enable_object_cache;

-- =========================
-- Folders (adjust if needed)
-- =========================
CREATE OR REPLACE MACRO INPUT_DIR()  AS 'input';
CREATE OR REPLACE MACRO OUTPUT_DIR() AS 'output';
CREATE OR REPLACE MACRO PARQUET_DIR() AS 'parquet';  

-- =========================
-- 1) Sweden Geo  Data(CSV)
-- =========================

-- NO-PARTITION read (use this if you wrote to ..._nopart above)
DROP TABLE IF EXISTS Sweden_Hospitals_geodata;
CREATE TABLE Sweden_Hospitals_geodata AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/Sweden_Hospitals_geodata.csv',
  columns = {
  'Clinic': 'VARCHAR',
  'Clinic_ID': 'BIGINT',
  '_2024_Total_Population': 'BIGINT',
  'Area_of_catchment': 'DOUBLE',
  'Population_density': 'BIGINT',
  '_2024_Total_Population_Age_0_14': 'BIGINT',
  '_2024_Total_Population_Age_15_29': 'BIGINT',
  '_2024_Total_Population_Age_30_44': 'BIGINT',
  '_2024_Total_Population_Age_45_59': 'BIGINT',
  '_2024_Total_Population_Age_60_': 'BIGINT',
  '_2024_Purchasing_Power_Per_Capita': 'DOUBLE'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false, null_padding=true
);
SELECT 'Sweden_Hospitals_geodata' AS msg, COUNT(*) AS rows FROM Sweden_Hospitals_geodata;

-- Cluster Area mapping
DROP TABLE IF EXISTS Sweden_Hospitals_cluster_business_area_mapping;
CREATE TABLE Sweden_Hospitals_cluster_business_area_mapping AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/Sweden_Hospitals_cluster_business_area_mapping.csv',
  columns ={
  'ID': 'BIGINT',
  'Clinic': 'VARCHAR',
  'Cluster': 'VARCHAR',
  'City': 'VARCHAR',
  'Clinic_ID': 'BIGINT',
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
  'City2': 'VARCHAR',
  'NoofDaysOpen': 'DOUBLE',
  'RunDateDW': 'DOUBLE',
  'ByUser': 'VARCHAR',
  'BusinessArea': 'VARCHAR'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'Sweden_Hospitals_cluster_business_area_mapping' AS msg, COUNT(*) AS rows FROM Sweden_Hospitals_cluster_business_area_mapping;

-- Competitor Count
DROP TABLE IF EXISTS Sweden_Competitor_data;
CREATE TABLE Sweden_Competitor_data AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/Sweden_Competitor_data.csv',
  columns ={
  'Clinic_ID': 'BIGINT',
  'Latitude': 'DOUBLE',
  'Longitude': 'DOUBLE',
  'total_competitor': 'BIGINT'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'Sweden_Competitor_data' AS msg, COUNT(*) AS rows FROM Sweden_Competitor_data;

-- Competitor Analysis
DROP TABLE IF EXISTS Sweden_Competitor_Analysis;
CREATE TABLE Sweden_Competitor_Analysis AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/Sweden_Competitor_Analysis.csv',
  columns ={
  'Proxy': 'VARCHAR',
  'Product': 'VARCHAR',
  'Clinic_Name': 'VARCHAR',
  'Clinic_Price': 'BIGINT',
  'Competitor': 'VARCHAR',
  'Competitor_Price': 'DOUBLE',
  'Clinic_ID': 'BIGINT'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'Sweden_Competitor_Analysis' AS msg, COUNT(*) AS rows FROM Sweden_Competitor_Analysis;

-- =========================
-- 2) VET FTE (CSV)
-- =========================

DROP TABLE IF EXISTS FACT_FullTimeEquivalentKPIsByCompanyAndCostCode;
CREATE TABLE FACT_FullTimeEquivalentKPIsByCompanyAndCostCode AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/beta.FACT_FullTimeEquivalentKPIsByCompanyAndCostCode.csv',
  columns ={
  'CountryKey': 'BIGINT',
  'FiscalYearKey': 'BIGINT',
  'CompanyKey': 'BIGINT',
  'CostCodeKey': 'BIGINT',
  'CountryCode': 'VARCHAR',
  'CCC': 'BIGINT',
  'COMPANY_CODE': 'BIGINT',
  'COST_CODE': 'BIGINT',
  'COUNTRY': 'VARCHAR',
  'BRAND': 'VARCHAR',
  'BRAND_DESCRIPTION': 'VARCHAR',
  'BUSINESS_AREA': 'VARCHAR',
  'BUSINESS_AREA2': 'VARCHAR',
  'COUNTRY_REPORTING': 'VARCHAR',
  'REPORTING_ENTITY': 'VARCHAR',
  'FTE_TYPE': 'VARCHAR',
  'BALANCE_TYPE': 'VARCHAR',
  'FISCAL_YEAR': 'BIGINT',
  '10': 'DOUBLE',
  '11': 'DOUBLE',
  '12': 'DOUBLE',
  '1': 'DOUBLE',
  '2': 'DOUBLE',
  '3': 'DOUBLE',
  '4': 'DOUBLE',
  '5': 'DOUBLE',
  '6': 'DOUBLE',
  '7': 'DOUBLE',
  '8': 'DOUBLE',
  '9': 'DOUBLE'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'FACT_FullTimeEquivalentKPIsByCompanyAndCostCode' AS msg, COUNT(*) AS rows FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode;

-- =========================
-- 3) NPS Data (CSV)
-- =========================

DROP TABLE IF EXISTS sweden_nps;
CREATE TABLE sweden_nps AS
SELECT * 
FROM read_csv(
  INPUT_DIR() || '/NPS_Data_SE.csv',
  columns ={
    'OaSurgeryCostCode': 'VARCHAR',
    'CostCodeandName': 'VARCHAR',
    '_2023_08_01': 'DOUBLE',
    '_2023_09_01': 'DOUBLE',
    '_2023_10_01': 'DOUBLE',
    '_2023_11_01': 'DOUBLE',
    '_2023_12_01': 'DOUBLE',
    '_2024_01_01': 'DOUBLE',
    '_2024_02_01': 'DOUBLE',
    '_2024_03_01': 'DOUBLE',
    '_2024_04_01': 'DOUBLE',
    '_2024_05_01': 'DOUBLE',
    '_2024_06_01': 'DOUBLE',
    '_2024_07_01': 'DOUBLE',
    '_2024_08_01': 'DOUBLE',
    '_2024_09_01': 'DOUBLE',
    '_2024_10_01': 'DOUBLE',
    '_2024_11_01': 'DOUBLE',
    '_2024_12_01': 'DOUBLE',
    '_2025_01_01': 'DOUBLE',
    '_2025_02_01': 'DOUBLE',
    '_2025_03_01': 'DOUBLE',
    '_2025_04_01': 'DOUBLE',
    '_2025_05_01': 'DOUBLE',
    '_2025_06_01': 'DOUBLE',
    '_2025_07_01': 'DOUBLE'
},
  header = true, sep = ',', nullstr = ['', 'NULL'], encoding='UTF-8',
  strict_mode=false,null_padding=true
);
SELECT 'sweden_nps' AS msg, COUNT(*) AS rows FROM sweden_nps;

-- =========================
-- 4) Department Dimension Data (CSV)
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
-- 5) Master Data (parquet)
-- =========================

DROP TABLE IF EXISTS master_data;
CREATE TABLE master_data AS
SELECT * FROM read_parquet(PARQUET_DIR() || '/sweden_master_data.parquet');
SELECT 'master_data' AS msg, COUNT(*) AS rows FROM master_data;
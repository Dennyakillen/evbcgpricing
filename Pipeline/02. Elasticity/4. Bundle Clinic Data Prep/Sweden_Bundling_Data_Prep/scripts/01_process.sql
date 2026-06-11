PRAGMA enable_object_cache;

-- Data Processsing
DROP TABLE IF EXISTS raw_data;
CREATE TABLE raw_data AS
  SELECT *,
    CONCAT(
      STRFTIME(DATE(InvoiceDate), '%Y-%m-%d'), '|',
      CAST(ID_Patient AS VARCHAR), '|',
      CAST(ID_Department AS VARCHAR)
    ) AS VisitIdPatient,
    CASE
      WHEN ProductGroupL4Name IN ('Anaesthesia', 'Consult') THEN
        REGEXP_REPLACE(UPPER(TRIM(ItemCode)), '[0-9].*$', '')
      ELSE
        UPPER(TRIM(ItemCode))
    END AS ItemCode_clean
  FROM sweden_master_data
  WHERE 
    -- G7 (Jens 2026-06-11): constant anchor LF.2, NO upper bound -> inherits the
    -- window the masterdata parquet already carries (built by replicate_dataprep.py).
    -- Cannot silently cap future fresh-data runs; YearFlag column kept for GROUP BY.
    -- CAST: masterdata parquet written all_varchar=true (LB.49) -> week col is TEXT.
    CAST(week_starting_monday AS DATE) >= DATE '2022-07-01'
    AND ProductGroupL4Name IN (
      'Anaesthesia','Hospitalisation','Imaging','Surgery','Other','Consult'
    )
    AND CAST(SalesTotal AS DOUBLE) > 0
    AND CAST(SoldQuantity AS DOUBLE) > 0
;

DROP TABLE IF EXISTS cleaned;
CREATE TABLE cleaned AS
  SELECT
    *,
    CASE 
      WHEN ProductGroupL4Name = 'Consult' AND UPPER(TRIM(ItemCode_clean)) != 'HEM' THEN 0
      ELSE 1
    END AS ItemCodeToConsider
  FROM raw_data
;

DROP TABLE IF EXISTS filtered_txn;
CREATE TABLE filtered_txn AS
  SELECT *
  FROM cleaned
  WHERE ItemCodeToConsider = 1
;

-- BUNDLE DATA PREPARATION -----------------------------------------------
DROP TABLE IF EXISTS bundle_raw;
CREATE TABLE bundle_raw AS
  SELECT *
  FROM sweden_bundles
  WHERE To_run_elasticity_analysis = 1
;

DROP TABLE IF EXISTS bundle_exploded;
CREATE TABLE bundle_exploded AS
  SELECT 
    br.*,
    TRIM(UPPER(b.value)) AS ProductCode
  FROM bundle_raw br,
  UNNEST(STRING_SPLIT(br.Bundle, ',')) AS b(value)
;

DROP TABLE IF EXISTS bundles;
CREATE TABLE bundles AS
  SELECT DISTINCT ProductCode
  FROM bundle_exploded
  WHERE ProductCode IS NOT NULL
;

-- CLUSTER MAPPING --------------------------------------------------------
DROP TABLE IF EXISTS cluster_mapping;
CREATE TABLE cluster_mapping AS
  SELECT 
    CAST(ID_Department AS INTEGER) AS ID_Department,
    Cluster,
    New_Cluster
  FROM sweden_cluster
;

-- JOIN TRANSACTION, BUNDLES & CLUSTERS -----------------------------------
DROP TABLE IF EXISTS joined_data;
CREATE TABLE joined_data AS
  SELECT 
    t.*,
    c.New_Cluster AS Cluster,
    DATE(t.InvoiceDate)
    - INTERVAL (
        CASE
            WHEN EXTRACT(DOW FROM DATE(t.InvoiceDate)) = 0 THEN 6
            ELSE EXTRACT(DOW FROM DATE(t.InvoiceDate)) - 1
        END
      ) DAY AS week_starting_monday
  FROM filtered_txn t
  INNER JOIN bundles b
    ON t.ItemCode_clean = b.ProductCode
  INNER JOIN cluster_mapping c
    ON CAST(t.ID_Department AS INTEGER) = c.ID_Department
;

-- AGGREGATE FINAL DATASET FOR BUNDLE-CLUSTER MODEL ----------------------
DROP TABLE IF EXISTS bundle_cluster_data;
CREATE TABLE bundle_cluster_data AS
  SELECT 
    Cluster AS Clusters,
    YearFlag,
    week_starting_monday,
    ID_Department,
    VisitIdPatient,
    ItemCode_clean AS ProductCode,
    ItemDescription,
    ProductGroupL4Name,
    SUM(CAST(SoldQuantity AS DOUBLE)) AS SoldQuantity,
    SUM(CAST(SalesTotal AS DOUBLE)) AS SalesTotal
  FROM joined_data
  GROUP BY 
    Clusters, YearFlag, week_starting_monday,
    ID_Department, VisitIdPatient, ProductCode,
    ItemDescription, ProductGroupL4Name
;

-- FTE 
DROP TABLE IF EXISTS fte_raw;
CREATE TABLE fte_raw AS
  SELECT 
    CAST(ID_Department AS INTEGER) AS ID_Department,
    DATE(week_starting_monday) AS week_starting_monday,
    CAST(FTE_Interpolated AS DOUBLE) AS FTE_Interpolated,
    Cluster
  FROM Sweden_Interpolated_Productivity_time
;

DROP TABLE IF EXISTS fte_joined;
CREATE TABLE fte_joined AS
  SELECT 
    a.Cluster,
    a.week_starting_monday,
    f.FTE_Interpolated,
    a.ID_Department
  FROM (
    SELECT DISTINCT 
      Cluster,
      week_starting_monday,
      ID_Department
    FROM joined_data
  ) a
  INNER JOIN fte_raw f
    ON CAST(a.ID_Department AS INTEGER) = f.ID_Department
    AND a.week_starting_monday = f.week_starting_monday
;

DROP TABLE IF EXISTS fte_final;
CREATE TABLE fte_final AS
SELECT 
  Cluster,
  week_starting_monday,
  SUM(FTE_Interpolated) AS total_FTE,
  COUNT(DISTINCT ID_Department) AS no_of_sites
FROM fte_joined
GROUP BY Cluster, week_starting_monday;


-- Bundle Group
DROP TABLE IF EXISTS sales_summary;
CREATE TABLE sales_summary AS
  SELECT 
    UPPER(TRIM(ItemCode_clean)) AS ItemCode,
    ProductGroupL4Name,
    SUM(CAST(SalesTotal AS DOUBLE)) AS Sum_SalesTotal
  FROM filtered_txn
  GROUP BY 1, 2
;

DROP TABLE IF EXISTS bundle_sales_join1;
CREATE TABLE bundle_sales_join1 AS
  SELECT 
    b.ProductCode,
    s.ItemCode,
    s.ProductGroupL4Name,
    s.Sum_SalesTotal
  FROM bundles b
  INNER JOIN sales_summary s
    ON UPPER(TRIM(b.ProductCode)) = s.ItemCode
;

DROP TABLE IF EXISTS bundle_sales_join;
CREATE TABLE bundle_sales_join AS
  SELECT 
    s.Bundle,
    b.ProductCode,
    b.ItemCode,
    b.ProductGroupL4Name,
    b.Sum_SalesTotal
  FROM bundle_sales_join1 b
  INNER JOIN bundle_exploded s
    ON UPPER(TRIM(s.ProductCode)) = b.ItemCode
;

DROP TABLE IF EXISTS ranked;
CREATE TABLE ranked AS
  SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY Bundle ORDER BY Sum_SalesTotal DESC) AS rn
  FROM bundle_sales_join
;

DROP TABLE IF EXISTS unique_bundle;
CREATE TABLE unique_bundle AS
  SELECT Bundle, ProductGroupL4Name
  FROM ranked
  WHERE rn = 1
;

DROP TABLE IF EXISTS bundles_final;
CREATE TABLE bundles_final AS
SELECT 
  Bundle,
  STRING_AGG(ProductGroupL4Name, ' | ') AS Bundle_Group
FROM unique_bundle
GROUP BY Bundle;

SELECT 'bundle_cluster_data' AS msg, COUNT(*) AS rows FROM bundle_cluster_data;
SELECT 'bundle_exploded' AS msg, COUNT(*) AS rows FROM bundle_exploded;
SELECT 'fte_final' AS msg, COUNT(*) AS rows FROM fte_final;
SELECT 'bundles_final' AS msg, COUNT(*) AS rows FROM bundles_final;
PRAGMA enable_object_cache;
-- =====================================================================
-- SWEDEN Elasticity PIPELINE 
-- =====================================================================

-- 1. fact_base
CREATE OR REPLACE TABLE fact_base AS
SELECT
  CAST(ID_Customer AS BIGINT) AS ID_Customer,
  CAST(ID_Department AS BIGINT) AS ID_Department,
  CAST(ID_Item AS BIGINT) AS ID_Item,
  CAST(ID_Patient AS BIGINT) AS ID_Patient,
  CAST(SUBSTR(CAST(InvoiceDate AS VARCHAR), 1, 10) AS DATE) AS InvoiceDate,
  CAST(NoofUnits AS DOUBLE) AS NoofUnits,
  Unit,
  CAST(SalesTotal AS DOUBLE) AS SalesTotal,
  CAST(SoldQuantity AS DOUBLE) AS SoldQuantity,
  CAST(PercentageChange AS DOUBLE) AS PercentageChange,
  SUBSTR(CAST(InvoiceDate AS VARCHAR), 1, 10)
    || '|' || CAST(ID_Customer AS VARCHAR)
    || '|' || CAST(ID_Department AS VARCHAR) AS VisitID,
  '12M ending Jun ' ||
    LPAD(
      CAST(
        CASE
          WHEN CAST(strftime('%m', CAST(SUBSTR(CAST(InvoiceDate AS VARCHAR), 1, 10) AS DATE)) AS INTEGER) >= 7 THEN
            CAST(strftime('%Y', CAST(SUBSTR(CAST(InvoiceDate AS VARCHAR), 1, 10) AS DATE)) AS INTEGER) + 1
          ELSE
            CAST(strftime('%Y', CAST(SUBSTR(CAST(InvoiceDate AS VARCHAR), 1, 10) AS DATE)) AS INTEGER)
        END % 100
      AS VARCHAR),
      2, '0'
    ) AS YearFlag,
  date_trunc('week', CAST(SUBSTR(CAST(InvoiceDate AS VARCHAR), 1, 10) AS DATE)) AS week_starting_monday
FROM transaction_data;

-- -- 2. patient_sel
-- CREATE OR REPLACE TABLE patient_sel AS
-- SELECT
--   CAST(ID_Patient AS BIGINT) AS ID_Patient,
--   CAST(ID_Customer AS BIGINT) AS ID_Customer,
--   CAST(BirthDate AS DATE) AS Pet_BirthDate,
--   Name,
--   OfficialName,
--   ID_Gender,
--   ID_Species,
--   ID_Breed,
--   CAST(PatientSinceDate AS DATE) AS PatientSinceDate,
--   Deceased,
--   CAST(DeceasedDate AS DATE) AS DeceasedDate,
--   ReasonOfDeath,
--   FarmAnimal,
--   Insured,
--   ID_InsuranceCompany,
--   Insurance
-- FROM DIM_Patient;

-- -- 3. customer_sel
-- CREATE OR REPLACE TABLE customer_sel AS
-- SELECT
--   CAST(ID_Customer AS BIGINT) AS ID_Customer,
--   CAST(CustomerSinceDate AS DATE) AS CustomerSinceDate,
--   City,
--   Country,
--   CAST(ActiveCustomer AS BIGINT) AS ActiveCustomer,
--   CAST(ID_CustomerType AS BIGINT) AS ID_CustomerType,
--   CustomerType,
--   CAST(HasAlivePatient AS BIGINT) AS HasAlivePatient,
--   CAST(FirstInvoiceDate AS DATE) AS FirstInvoiceDate,
--   CAST(LatestInvoiceDate AS DATE) AS LatestInvoiceDate,
--   OrganizationName,
--   VATNumber
-- FROM DIM_Customer;

-- 4. item_sel
CREATE OR REPLACE TABLE item_sel AS
SELECT
  CAST(ID_Item AS BIGINT) AS ID_Item,
  ItemDescription,
  ItemType,
  UPPER(TRIM(ItemCode)) AS ItemCode,
  ProductGroupL1Name,
  ProductGroupL2Name,
  ProductGroupL3Name,
  ProductGroupL4Name
FROM Dim_Item;

-- 5. dept_sel
CREATE OR REPLACE TABLE dept_sel AS
SELECT
  CAST(ID_Department AS BIGINT) AS ID_Department,
  "Group" AS DeptGroup,
  CostCenterCode,
  DepartmentType,
  StreetAddress,
  ZipCode,
  City AS DepartmentCity,
  BusinessArea
FROM dim_department;

-- 6. cluster_map
CREATE OR REPLACE TABLE cluster_map AS
SELECT
  CAST(ID_Department AS BIGINT) AS ID_Department,
  Cluster,
  New_Cluster
FROM sweden_cluster;

-- 7. master_core
CREATE OR REPLACE TABLE master_core AS
SELECT
  f.*,
  i.*,
  d.*,
  m.Cluster,
  m.New_Cluster
FROM fact_base f
LEFT JOIN item_sel i USING (ID_Item)
LEFT JOIN dept_sel d USING (ID_Department)
INNER JOIN cluster_map m USING (ID_Department);

-- Saving master data
CREATE OR REPLACE TABLE master_core_save AS
SELECT
  f.*,
  i.*,
  d.*
FROM fact_base f
LEFT JOIN item_sel i USING (ID_Item)
LEFT JOIN dept_sel d USING (ID_Department);


-- 8. filtered_master
CREATE OR REPLACE TABLE filtered_master AS
SELECT *
FROM master_core
WHERE
  YearFlag IN ('12M ending Jun 23', '12M ending Jun 24', '12M ending Jun 25')
  AND SalesTotal > 0
  AND SoldQuantity > 0
  AND COALESCE(UPPER(TRIM(ProductGroupL4Name)), '') NOT IN ('', 'DISCOUNTS', 'NULL')
  AND ItemCode IS NOT NULL
  AND LOWER(TRIM(ItemCode)) <> 'ta bort';
-- 9. pg4_by_item
CREATE OR REPLACE TABLE pg4_by_item AS
SELECT
  ProductGroupL4Name,
  ItemCode,
  SUM(SalesTotal) AS Sum_SalesTotal
FROM filtered_master
GROUP BY ProductGroupL4Name, ItemCode;

-- 10. pg4_choice
CREATE OR REPLACE TABLE pg4_choice AS
SELECT ItemCode, ProductGroupL4Name
FROM (
  SELECT
    ItemCode,
    ProductGroupL4Name,
    Sum_SalesTotal,
    ROW_NUMBER() OVER (PARTITION BY ItemCode ORDER BY Sum_SalesTotal DESC) AS rn
  FROM pg4_by_item
)
WHERE rn = 1;

-- 11. filtered_master_1 (override PG4)
CREATE OR REPLACE TABLE filtered_master_1 AS
SELECT
  fm.* REPLACE (pc.ProductGroupL4Name AS ProductGroupL4Name)
FROM filtered_master fm
JOIN pg4_choice pc USING (ItemCode);

-- 12. latest_desc
CREATE OR REPLACE TABLE latest_desc AS
SELECT
  ItemCode,
  ProductGroupL4Name,
  ItemDescription
FROM (
  SELECT
    ItemCode,
    ProductGroupL4Name,
    ItemDescription,
    InvoiceDate,
    ROW_NUMBER() OVER (
      PARTITION BY ItemCode, ProductGroupL4Name
      ORDER BY InvoiceDate DESC
    ) AS rn
  FROM filtered_master_1
)
WHERE rn = 1;

-- 13. filtered_master_2 (override description)
CREATE OR REPLACE TABLE filtered_master_2 AS
SELECT
  fm.* REPLACE (pc.ItemDescription AS ItemDescription)
FROM filtered_master_1 fm
JOIN latest_desc pc USING (ItemCode);

CREATE OR REPLACE TABLE item_desciption AS
SELECT
  ProductGroupL4Name,
  ItemCode,
  ItemDescription,
  SUM(SalesTotal) AS Sum_SalesTotal
FROM filtered_master_2
GROUP BY ProductGroupL4Name, ItemCode, ItemDescription;

-- 14. item_total
CREATE OR REPLACE TABLE item_total AS
SELECT
  ProductGroupL4Name,
  ItemCode,
  SUM(SalesTotal) AS item_total
FROM filtered_master_2
GROUP BY ProductGroupL4Name, ItemCode;

-- 15. group_total
CREATE OR REPLACE TABLE group_total AS
SELECT
  ProductGroupL4Name,
  SUM(SalesTotal) AS total
FROM filtered_master_2
GROUP BY ProductGroupL4Name;

-- 16. ranked
CREATE OR REPLACE TABLE ranked AS
SELECT
  it.ProductGroupL4Name,
  it.ItemCode,
  it.item_total,
  gt.total,
  SUM(it.item_total) OVER (
    PARTITION BY it.ProductGroupL4Name
    ORDER BY it.item_total DESC
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_sum
FROM item_total it
JOIN group_total gt USING (ProductGroupL4Name);

-- 17. top80
CREATE OR REPLACE TABLE top80 AS
SELECT
  ProductGroupL4Name,
  ItemCode,
  item_total,
  total,
  cumulative_sum,
  cumulative_sum / total AS perc,
  LAG(cumulative_sum / total) OVER (
    PARTITION BY ProductGroupL4Name ORDER BY item_total DESC
  ) AS perc_prev,
  CASE
    WHEN cumulative_sum / total <= 0.81
         OR LAG(cumulative_sum / total) OVER (
              PARTITION BY ProductGroupL4Name ORDER BY item_total DESC
            ) <= 0.80
         OR LAG(cumulative_sum / total) OVER (
              PARTITION BY ProductGroupL4Name ORDER BY item_total DESC
            ) IS NULL
    THEN 1
    ELSE 0
  END AS Top80Flag
FROM ranked;

-- 18. filtered_master_3
CREATE OR REPLACE TABLE filtered_master_3 AS
SELECT
  md.*,
  COALESCE(t.Top80Flag, 0) AS Top80Flag
FROM filtered_master_2 md
JOIN top80 t USING (ProductGroupL4Name, ItemCode)
WHERE t.Top80Flag = 1;

-- 19. weekly_base
CREATE OR REPLACE TABLE weekly_base AS
SELECT
  ProductGroupL4Name,
  ItemCode,
  ItemDescription,
  week_starting_monday,
  Cluster,
  New_Cluster,
  ID_Department,
  SUM(SoldQuantity) AS SoldQuantity,
  SUM(NoofUnits) AS NoofUnits,
  SUM(SalesTotal) AS TotalNet,
  SUM(CASE WHEN SalesTotal >= 0 THEN SoldQuantity ELSE 0 END) AS QuantitySold_SalesTotal_grtr_thn_0
FROM filtered_master_3
WHERE week_starting_monday BETWEEN DATE '2022-07-01' AND DATE '2025-06-28'
GROUP BY 1,2,3,4,5,6,7;

-- 20. weekly_cluster
CREATE OR REPLACE TABLE weekly_cluster AS
SELECT
  wb.ProductGroupL4Name,
  wb.ItemCode,
  wb.ItemDescription,
  wb.week_starting_monday,
  wb.Cluster,
  SUM(wb.SoldQuantity) AS SoldQuantity,
  SUM(wb.NoofUnits) AS NoofUnits,
  SUM(wb.TotalNet) AS TotalNet,
  SUM(wb.QuantitySold_SalesTotal_grtr_thn_0) AS "QuantitySold(SalesTotal>0)",
  SUM(f.FTE_Interpolated) AS Sum_FTE_Interpolated,
  COUNT(DISTINCT wb.ID_Department) AS No_of_Sites
FROM weekly_base wb
LEFT JOIN fte_weekly f USING (ID_Department, week_starting_monday)
GROUP BY 1,2,3,4,5;
select count(*) from weekly_cluster;

-- 21. weekly_ch (new cluster grouping)
CREATE OR REPLACE TABLE weekly_ch AS
SELECT
  wb.ProductGroupL4Name,
  wb.ItemCode,
  wb.ItemDescription,
  wb.week_starting_monday,
  wb.New_Cluster AS New_Cluster,
  SUM(wb.SoldQuantity) AS SoldQuantity,
  SUM(wb.NoofUnits) AS NoofUnits,
  SUM(wb.TotalNet) AS TotalNet,
  SUM(wb.QuantitySold_SalesTotal_grtr_thn_0) AS "QuantitySold(SalesTotal>0)",
  SUM(f.FTE_Interpolated) AS Sum_FTE_Interpolated,
  COUNT(DISTINCT wb.ID_Department) AS No_of_Sites
FROM weekly_base wb
LEFT JOIN fte_weekly f USING (ID_Department, week_starting_monday)
GROUP BY 1,2,3,4,5;
select count(*) from weekly_ch;


-- 22. weekly_site (per site)
CREATE OR REPLACE TABLE weekly_site AS
SELECT
  wb.ProductGroupL4Name,
  wb.ItemCode,
  wb.ItemDescription,
  wb.week_starting_monday,
  wb.ID_Department AS Cluster,
  SUM(wb.SoldQuantity) AS SoldQuantity,
  SUM(wb.NoofUnits) AS NoofUnits,
  SUM(wb.TotalNet) AS TotalNet,
  SUM(wb.QuantitySold_SalesTotal_grtr_thn_0) AS "QuantitySold(SalesTotal>0)",
  SUM(f.FTE_Interpolated) AS Sum_FTE_Interpolated
FROM weekly_base wb
LEFT JOIN fte_weekly f USING (ID_Department, week_starting_monday)
GROUP BY 1,2,3,4,5;
select count(*) from weekly_site;


-- 23. cluster_map_new
CREATE OR REPLACE TABLE cluster_map_new AS
SELECT
  CAST(ID_Department AS BIGINT) AS ID_Department,
  Cluster,
  New_Cluster
FROM sweden_cluster_fallback;

-- 24. master_core_fallback
CREATE OR REPLACE TABLE master_core_fallback AS
SELECT
  f.*,
  i.*,
  d.*,
  m.Cluster,
  m.New_Cluster
FROM fact_base f
LEFT JOIN item_sel i USING (ID_Item)
LEFT JOIN dept_sel d USING (ID_Department)
INNER JOIN cluster_map_new m USING (ID_Department);

-- 25. filtered_master_fallback
CREATE OR REPLACE TABLE filtered_master_fallback AS
SELECT *
FROM master_core_fallback
WHERE
  YearFlag IN ('12M ending Jun 23', '12M ending Jun 24', '12M ending Jun 25')
  AND SalesTotal > 0
  AND SoldQuantity > 0
  AND COALESCE(UPPER(TRIM(ProductGroupL4Name)), '') NOT IN ('', 'DISCOUNTS', 'NULL')
  AND ItemCode IS NOT NULL
  AND LOWER(TRIM(ItemCode)) <> 'ta bort';

-- 26. fallback_pg4_by_item
CREATE OR REPLACE TABLE fallback_pg4_by_item AS
SELECT
  ProductGroupL4Name,
  ItemCode,
  SUM(SalesTotal) AS Sum_SalesTotal
FROM filtered_master_fallback
GROUP BY ProductGroupL4Name, ItemCode;

-- 27. fallback_pg4_choice
CREATE OR REPLACE TABLE fallback_pg4_choice AS
SELECT ItemCode, ProductGroupL4Name
FROM (
  SELECT
    ItemCode,
    ProductGroupL4Name,
    Sum_SalesTotal,
    ROW_NUMBER() OVER (PARTITION BY ItemCode ORDER BY Sum_SalesTotal DESC) AS rn
  FROM fallback_pg4_by_item
)
WHERE rn = 1;

-- 28. fallback_filtered_master_1
CREATE OR REPLACE TABLE fallback_filtered_master_1 AS
SELECT
  fm.* REPLACE (pc.ProductGroupL4Name AS ProductGroupL4Name)
FROM filtered_master_fallback fm
JOIN fallback_pg4_choice pc USING (ItemCode);

-- 29. fallback_latest_desc
CREATE OR REPLACE TABLE fallback_latest_desc AS
SELECT
  ItemCode,
  ProductGroupL4Name,
  ItemDescription
FROM (
  SELECT
    ItemCode,
    ProductGroupL4Name,
    ItemDescription,
    InvoiceDate,
    ROW_NUMBER() OVER (
      PARTITION BY ItemCode, ProductGroupL4Name
      ORDER BY InvoiceDate DESC
    ) AS rn
  FROM fallback_filtered_master_1
)
WHERE rn = 1;

-- 30. fallback_filtered_master_2
CREATE OR REPLACE TABLE fallback_filtered_master_2 AS
SELECT
  fm.* REPLACE (pc.ItemDescription AS ItemDescription)
FROM fallback_filtered_master_1 fm
JOIN fallback_latest_desc pc USING (ItemCode);


-- 31. complete_product_all
CREATE OR REPLACE TABLE complete_product_all AS
SELECT
  ItemCode,
  ItemDescription,
  ProductGroupL4Name,
  ID_Department,
  Cluster,
  New_Cluster,
  SUM(SalesTotal) AS SalesTotal
FROM fallback_filtered_master_2
GROUP BY ItemCode, ItemDescription, ProductGroupL4Name, ID_Department, Cluster, New_Cluster;

-- 33. complete_product_25
CREATE OR REPLACE TABLE complete_product_25 AS
SELECT
  ItemCode,
  ItemDescription,
  ProductGroupL4Name,
  ID_Department,
  Cluster,
  New_Cluster,
  SUM(SalesTotal) AS SalesTotal_YearEnding25
FROM fallback_filtered_master_2
WHERE YearFlag = '12M ending Jun 25'
GROUP BY ItemCode, ItemDescription, ProductGroupL4Name, ID_Department, Cluster, New_Cluster;

-- 34. fallback_base_final
CREATE OR REPLACE TABLE fallback_base_final AS
SELECT
  a.*,
  y.SalesTotal_YearEnding25
FROM complete_product_all a
LEFT JOIN complete_product_25 y USING (
  ItemCode, ProductGroupL4Name, ID_Department, Cluster, New_Cluster
);

-- Final: you can inspect fallback_base_final or weekly_cluster or other tables
SELECT * FROM fallback_base_final LIMIT 100;
SELECT count(*) FROM fallback_base_final LIMIT 100;


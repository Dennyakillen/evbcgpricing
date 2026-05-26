PRAGMA enable_object_cache;

-- ================================================================
-- 1. GEO DATA (Demographics + Business Area + Geo Cluster)
-- ================================================================
DROP TABLE IF EXISTS geo_demographics;
CREATE TABLE geo_demographics AS 
  -- Aggregate population and income data per clinic
  SELECT
    Clinic_ID,
    SUM(
      _2024_Total_Population_Age_15_29
      + _2024_Total_Population_Age_30_44
      + _2024_Total_Population_Age_45_59
      + _2024_Total_Population_Age_0_14
      + _2024_Total_Population_Age_60_
    ) AS TotalPopulation,
    SUM(Population_density) AS PopulationDensity,
    SUM(_2024_Purchasing_Power_Per_Capita) AS HouseHoldIncome,
    SUM(_2024_Total_Population_Age_15_29) AS Pop_15_29,
    SUM(_2024_Total_Population_Age_30_44) AS Pop_30_44,
    SUM(_2024_Total_Population_Age_45_59) AS Pop_45_59,
    SUM(_2024_Total_Population_Age_0_14) AS Pop_0_14,
    SUM(_2024_Total_Population_Age_60_) AS Pop_60_plus
  FROM Sweden_Hospitals_geodata  
  GROUP BY Clinic_ID
;
DROP TABLE IF EXISTS geo_cluster_info;
CREATE TABLE geo_cluster_info AS 
  -- Join mapping of clinics to business area and cluster
  SELECT
    Clinic_ID,
    MAX(BusinessArea) AS BusinessArea,
    MAX(Cluster) AS Geo_Cluster
  FROM Sweden_Hospitals_cluster_business_area_mapping
  GROUP BY Clinic_ID
;
DROP TABLE IF EXISTS geo_joined;
CREATE TABLE geo_joined AS 
  -- Combine the two geo sources
  SELECT
    d.Clinic_ID,
    c.BusinessArea,
    c.Geo_Cluster,
    d.TotalPopulation,
    d.PopulationDensity,
    d.HouseHoldIncome,
    d.Pop_15_29,
    d.Pop_30_44,
    d.Pop_45_59,
    d.Pop_0_14,
    d.Pop_60_plus
  FROM geo_demographics AS d
  LEFT JOIN geo_cluster_info AS c USING (Clinic_ID)
;
DROP TABLE IF EXISTS geo_filtered;
CREATE TABLE geo_filtered AS 
  SELECT * FROM geo_joined
  WHERE TotalPopulation > 0
;
DROP TABLE IF EXISTS geo_percentages;
CREATE TABLE geo_percentages AS 
  -- Calculate population percentages by age group
  SELECT
    *,
    CASE WHEN TotalPopulation = 0 THEN NULL ELSE Pop_0_14 * 1.0 / TotalPopulation END AS perc_Pop_0_14,
    CASE WHEN TotalPopulation = 0 THEN NULL ELSE Pop_15_29 * 1.0 / TotalPopulation END AS perc_Pop_15_29,
    CASE WHEN TotalPopulation = 0 THEN NULL ELSE Pop_30_44 * 1.0 / TotalPopulation END AS perc_Pop_30_44,
    CASE WHEN TotalPopulation = 0 THEN NULL ELSE Pop_45_59 * 1.0 / TotalPopulation END AS perc_Pop_45_59,
    CASE WHEN TotalPopulation = 0 THEN NULL ELSE Pop_60_plus * 1.0 / TotalPopulation END AS perc_Pop_60_plus
  FROM geo_filtered
;

-- ================================================================
-- 2. COMPETITOR DATA (Count per clinic)
-- ================================================================
DROP TABLE IF EXISTS competitor_summary;
CREATE TABLE competitor_summary AS 
  SELECT
    Clinic_ID,
    SUM(total_competitor) AS total_competitor
  FROM Sweden_Competitor_data
  GROUP BY Clinic_ID
;
-- ================================================================
-- 3. PRICE FEATURES (Clinic vs Competitor)
-- ================================================================
DROP TABLE IF EXISTS clinic_price_avg;
CREATE TABLE clinic_price_avg AS 
  -- Average clinic prices per product
  SELECT
    Clinic_ID,
    Product,
    AVG(CAST(Clinic_Price AS DOUBLE)) AS Avg_Clinic_Price
  FROM Sweden_Competitor_Analysis
  GROUP BY Clinic_ID, Product
;
DROP TABLE IF EXISTS competitor_level_price;
CREATE TABLE competitor_level_price AS 
  -- Average competitor price per competitor and product
  SELECT
    Clinic_ID,
    Competitor,
    Product,
    AVG(CAST(Competitor_Price AS DOUBLE)) AS Competitor_Avg_Price
  FROM Sweden_Competitor_Analysis
  GROUP BY Clinic_ID, Competitor, Product
;
DROP TABLE IF EXISTS competitor_price;
CREATE TABLE competitor_price AS 
  -- Average across competitors, ignoring 0 values
  SELECT
    Clinic_ID,
    Product,
    AVG(NULLIF(Competitor_Avg_Price, 0)) AS AvgNo0_Competitor_Price
  FROM competitor_level_price
  GROUP BY Clinic_ID, Product
;
DROP TABLE IF EXISTS clinic_price_pivot;
CREATE TABLE clinic_price_pivot AS 
  -- Pivot clinic prices by product
  SELECT
    Clinic_ID,
    MAX(CASE WHEN Product = 'Bitch Spay (20kg)' THEN Avg_Clinic_Price END) AS Bitch_Spay_20kg,
    MAX(CASE WHEN Product = 'Castrate Dog (20kg)' THEN Avg_Clinic_Price END) AS Castrate_Dog_20kg,
    MAX(CASE WHEN Product = 'Cat Castrate' THEN Avg_Clinic_Price END) AS Cat_Castrate,
    MAX(CASE WHEN Product = 'Cat Spay' THEN Avg_Clinic_Price END) AS Cat_Spay,
    MAX(CASE WHEN Product = 'Cat Vaccination' THEN Avg_Clinic_Price END) AS Cat_Vaccination,
    MAX(CASE WHEN Product = 'Consultation' THEN Avg_Clinic_Price END) AS Consultation,
    MAX(CASE WHEN Product = 'Dog Vaccination DHPPI' THEN Avg_Clinic_Price END) AS Dog_Vaccination_DHPPI,
    MAX(CASE WHEN Product = 'X-Ray & Sedation (HD)' THEN Avg_Clinic_Price END) AS X_Ray_Sedation_HD,
    MAX(CASE WHEN Product = 'X-Ray & Sedation (HD)' THEN Avg_Clinic_Price END) AS "X-Ray & Sedation (HD)"
  FROM clinic_price_avg
  GROUP BY Clinic_ID
;
DROP TABLE IF EXISTS competitor_price_pivot;
CREATE TABLE competitor_price_pivot AS 
  -- Pivot competitor prices by product
  SELECT
    Clinic_ID,
    MAX(CASE WHEN Product = 'Bitch Spay (20kg)' THEN AvgNo0_Competitor_Price END) AS Bitch_Spay_20kg_Competitor,
    MAX(CASE WHEN Product = 'Castrate Dog (20kg)' THEN AvgNo0_Competitor_Price END) AS Castrate_Dog_20kg_Competitor,
    MAX(CASE WHEN Product = 'Cat Castrate' THEN AvgNo0_Competitor_Price END) AS Cat_Castrate_Competitor,
    MAX(CASE WHEN Product = 'Cat Spay' THEN AvgNo0_Competitor_Price END) AS Cat_Spay_Competitor,
    MAX(CASE WHEN Product = 'Cat Vaccination' THEN AvgNo0_Competitor_Price END) AS Cat_Vaccination_Competitor,
    MAX(CASE WHEN Product = 'Consultation' THEN AvgNo0_Competitor_Price END) AS Consultation_Competitor,
    MAX(CASE WHEN Product = 'Dog Vaccination DHPPI' THEN AvgNo0_Competitor_Price END) AS Dog_Vaccination_DHPPI_Competitor,
    MAX(CASE WHEN Product = 'X-Ray & Sedation (HD)' THEN AvgNo0_Competitor_Price END) AS X_Ray_Sedation_HD_Competitor
  FROM competitor_price
  GROUP BY Clinic_ID
;
DROP TABLE IF EXISTS price_joined;
CREATE TABLE price_joined AS 
  SELECT
    c.*,
    p.*
  FROM clinic_price_pivot AS c
  LEFT JOIN competitor_price_pivot AS p USING (Clinic_ID)
;
DROP TABLE IF EXISTS price_index_features;
CREATE TABLE price_index_features AS 
  -- Compute price indexes (Clinic ÷ Competitor)
  SELECT
    Clinic_ID,
    CASE WHEN Bitch_Spay_20kg_Competitor = 0 THEN NULL ELSE Bitch_Spay_20kg * 1.0 / Bitch_Spay_20kg_Competitor END AS Bitch_Spay_20kg_Index,
    CASE WHEN Castrate_Dog_20kg_Competitor = 0 THEN NULL ELSE Castrate_Dog_20kg * 1.0 / Castrate_Dog_20kg_Competitor END AS Castrate_Dog_20kg_Index,
    CASE WHEN Cat_Castrate_Competitor = 0 THEN NULL ELSE Cat_Castrate * 1.0 / Cat_Castrate_Competitor END AS Cat_Castrate_Index,
    CASE WHEN Cat_Spay_Competitor = 0 THEN NULL ELSE Cat_Spay * 1.0 / Cat_Spay_Competitor END AS Cat_Spay_Index,
    CASE WHEN Cat_Vaccination_Competitor = 0 THEN NULL ELSE Cat_Vaccination * 1.0 / Cat_Vaccination_Competitor END AS Cat_Vaccination_Index,
    CASE WHEN Consultation_Competitor = 0 THEN NULL ELSE Consultation * 1.0 / Consultation_Competitor END AS Consultation_Index,
    CASE WHEN Dog_Vaccination_DHPPI_Competitor = 0 THEN NULL ELSE Dog_Vaccination_DHPPI * 1.0 / Dog_Vaccination_DHPPI_Competitor END AS Dog_Vaccination_DHPPI_Index,
    CASE WHEN X_Ray_Sedation_HD_Competitor = 0 THEN NULL ELSE X_Ray_Sedation_HD * 1.0 / X_Ray_Sedation_HD_Competitor END AS X_Ray_Sedation_HD_Index
  FROM price_joined
;

-- ================================================================
-- 4. VET FTE & TOTAL FTE FEATURES
-- ================================================================
-- ================================================================
-- 4. VET FTE & TOTAL FTE FEATURES (UNPIVOT using UNION ALL)
-- ================================================================
DROP TABLE IF EXISTS vet_fte_base;
CREATE TABLE vet_fte_base AS 
  -- UNPIVOT logic by UNION ALL for months 1 to 12
  SELECT COST_CODE, FISCAL_YEAR, 1 AS MonthNum, CAST("1" AS DOUBLE) AS Value FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("1" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 2, CAST("2" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("2" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 3, CAST("3" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("3" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 4, CAST("4" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("4" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 5, CAST("5" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("5" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 6, CAST("6" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("6" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 7, CAST("7" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("7" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 8, CAST("8" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("8" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 9, CAST("9" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("9" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 10, CAST("10" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("10" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 11, CAST("11" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("11" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 12, CAST("12" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE FTE_TYPE = 'VET FTE' AND BALANCE_TYPE = 'AQ' AND CAST("12" AS DOUBLE) <> 0
;
DROP TABLE IF EXISTS total_fte_base;
CREATE TABLE total_fte_base AS 
  -- Same unpivot logic for all FTE types
  SELECT COST_CODE, FISCAL_YEAR, 1 AS MonthNum, CAST("1" AS DOUBLE) AS Value FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("1" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 2, CAST("2" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("2" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 3, CAST("3" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("3" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 4, CAST("4" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("4" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 5, CAST("5" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("5" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 6, CAST("6" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("6" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 7, CAST("7" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("7" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 8, CAST("8" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("8" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 9, CAST("9" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("9" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 10, CAST("10" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("10" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 11, CAST("11" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("11" AS DOUBLE) <> 0
  UNION ALL
  SELECT COST_CODE, FISCAL_YEAR, 12, CAST("12" AS DOUBLE) FROM FACT_FullTimeEquivalentKPIsByCompanyAndCostCode
    WHERE BALANCE_TYPE = 'AQ' AND CAST("12" AS DOUBLE) <> 0
;
-- Vet FTE Median for 12M ending May 2025
DROP TABLE IF EXISTS vet_fte_may25_raw;
CREATE TABLE vet_fte_may25_raw AS 
  SELECT *
  FROM vet_fte_base
  WHERE (FISCAL_YEAR = 2024 AND MonthNum IN (6,7,8,9))
     OR (FISCAL_YEAR = 2025 AND MonthNum IN (10,11,12,1,2,3,4,5))
;
DROP TABLE IF EXISTS vet_fte_12M_ending_may25;
CREATE TABLE vet_fte_12M_ending_may25 AS 
  SELECT
    COST_CODE,
    quantile_cont(Value, 0.5) AS Median_VET_FTE_12M_ending_May25
  FROM vet_fte_may25_raw
  WHERE Value IS NOT NULL AND Value <> 0
  GROUP BY COST_CODE
;
DROP TABLE IF EXISTS total_fte_may25_raw;
CREATE TABLE total_fte_may25_raw AS 
  SELECT *
  FROM total_fte_base
  WHERE (FISCAL_YEAR = 2024 AND MonthNum IN (6,7,8,9))
     OR (FISCAL_YEAR = 2025 AND MonthNum IN (10,11,12,1,2,3,4,5))
;
DROP TABLE IF EXISTS total_fte_12M_ending_may25;
CREATE TABLE total_fte_12M_ending_may25 AS 
  SELECT
    COST_CODE,
    quantile_cont(Value, 0.5) AS Median_Total_FTE_12M_ending_May25
  FROM total_fte_may25_raw
  WHERE Value IS NOT NULL AND Value <> 0
  GROUP BY COST_CODE
;
DROP TABLE IF EXISTS nps_unpivoted;
CREATE TABLE nps_unpivoted AS 
  SELECT 
  OaSurgeryCostCode, CAST(_2024_07_01 AS DOUBLE) AS Value FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2024_08_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2024_09_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2024_10_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2024_11_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2024_12_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2025_01_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2025_02_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2025_03_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2025_04_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2025_05_01 AS DOUBLE) FROM sweden_nps
  UNION ALL SELECT OaSurgeryCostCode, CAST(_2025_06_01 AS DOUBLE) FROM sweden_nps
;
-- ================================================================
-- 5. NPS FEATURES (Exact MedianNo0)
-- ================================================================
DROP TABLE IF EXISTS nps_median;
CREATE TABLE nps_median AS 
  SELECT
    OaSurgeryCostCode,
    quantile_cont(Value, 0.5) AS Median_NPS_calculated
  FROM nps_unpivoted
  WHERE Value IS NOT NULL AND Value <> 0
  AND try_cast(OaSurgeryCostCode AS BIGINT) IS NOT NULL
  GROUP BY OaSurgeryCostCode
;

-- ================================================================
-- 6. REVENUE FEATURES (SUM SalesTotal by Clinic and YearFlag)
-- ================================================================
DROP TABLE IF EXISTS revenue_by_year;
CREATE TABLE revenue_by_year AS 
  SELECT
    ID_Department,
    YearFlag,
    SUM(CAST(SalesTotal AS DOUBLE)) AS Revenue
  FROM master_data
  GROUP BY ID_Department, YearFlag
;
DROP TABLE IF EXISTS revenue_pivoted;
CREATE TABLE revenue_pivoted AS 
  SELECT
    ID_Department,
    MAX(CASE WHEN YearFlag = '12M ending Jun 17' THEN Revenue END) AS revenue_12M_ending_Jun_17,
    MAX(CASE WHEN YearFlag = '12M ending Jun 18' THEN Revenue END) AS revenue_12M_ending_Jun_18,
    MAX(CASE WHEN YearFlag = '12M ending Jun 19' THEN Revenue END) AS revenue_12M_ending_Jun_19,
    MAX(CASE WHEN YearFlag = '12M ending Jun 20' THEN Revenue END) AS revenue_12M_ending_Jun_20,
    MAX(CASE WHEN YearFlag = '12M ending Jun 21' THEN Revenue END) AS revenue_12M_ending_Jun_21,
    MAX(CASE WHEN YearFlag = '12M ending Jun 22' THEN Revenue END) AS revenue_12M_ending_Jun_22,
    MAX(CASE WHEN YearFlag = '12M ending Jun 23' THEN Revenue END) AS revenue_12M_ending_Jun_23,
    MAX(CASE WHEN YearFlag = '12M ending Jun 24' THEN Revenue END) AS revenue_12M_ending_Jun_24,
    MAX(CASE WHEN YearFlag = '12M ending Jun 25' THEN Revenue END) AS revenue_12M_ending_Jun_25
  FROM revenue_by_year
  GROUP BY ID_Department
;
DROP TABLE IF EXISTS department_dim;
CREATE TABLE department_dim AS 
  SELECT
    ID_Department,
    CostCenterCode,
    DepartmentDescription,
    BusinessArea,
    DepartmentType,
    DepartmentManager,
    ChiefVeterinarian,
    ReceptionManager
  FROM dim_department
;
CREATE TABLE final_data AS 
  SELECT
    g.Clinic_ID as "Clinic ID",
    g.BusinessArea,
    g.Geo_Cluster,
    g.TotalPopulation,
    g.PopulationDensity,
    g.HouseHoldIncome,
    g.perc_Pop_0_14 as "perc_2024 Total Population Age 0-14", 
    g.perc_Pop_15_29 as "perc_2024 Total Population Age 15-29", 
    g.perc_Pop_30_44 as "perc_2024 Total Population Age 30-44", 
    g.perc_Pop_45_59 as "perc_2024 Total Population Age 45-59", 
    g.perc_Pop_60_plus as "perc_2024 Total Population Age 60+",
    geo_demographics.Pop_0_14 AS "2024 Total Population Age 0-14",
    geo_demographics.Pop_15_29 AS "2024 Total Population Age 15-29",
    geo_demographics.Pop_30_44 AS "2024 Total Population Age 30-44",
    geo_demographics.Pop_45_59 AS "2024 Total Population Age 45-59",
    geo_demographics.Pop_60_plus AS "2024 Total Population Age 60+",
    c.total_competitor as "total competitor",
    p.Consultation_Index,
    p.Cat_Vaccination_Index as "Cat Vaccination_Index",
    p.Cat_Spay_Index as "Cat Spay_Index",
    p.Cat_Castrate_Index as "Cat Castrate_Index",
    p.Dog_Vaccination_DHPPI_Index as "Dog Vaccination DHPPI_Index",
    p.Bitch_Spay_20kg_Index as "Bitch_Spay_20kg_Index",
    p.Castrate_Dog_20kg_Index as "Castrate Dog (20kg)_Index",
    v25.Median_VET_FTE_12M_ending_May25 as "Median_VET_FTE_12M_ending_may25",
    t25.Median_Total_FTE_12M_ending_May25 as "Median_Total_FTE_12M_ending_may25",
    n.Median_NPS_calculated,
    r.revenue_12M_ending_Jun_17 as "12M_ending_Jun_17",
    r.revenue_12M_ending_Jun_18 as "12M_ending_Jun_18",
    r.revenue_12M_ending_Jun_19 as "12M_ending_Jun_19",
    r.revenue_12M_ending_Jun_20 as "12M_ending_Jun_20",
    r.revenue_12M_ending_Jun_21 as "12M_ending_Jun_21",
    r.revenue_12M_ending_Jun_22 as "12M_ending_Jun_22",
    r.revenue_12M_ending_Jun_23 as "12M_ending_Jun_23",
    r.revenue_12M_ending_Jun_24 as "12M_ending_Jun_24",
    r.revenue_12M_ending_Jun_25 as "12M_ending_Jun_25",
    d.CostCenterCode,
    cp.Bitch_Spay_20kg as "Bitch_Spay__20kg_", 
    cp.Castrate_Dog_20kg as "Castrate_Dog__20kg_", 
    cp.Cat_Castrate, cp.Cat_Spay,
    cp.Cat_Vaccination, cp.Consultation, cp.Dog_Vaccination_DHPPI, 
    cp.X_Ray_Sedation_HD as "X_Ray___Sedation__HD_",
    cp.X_Ray_Sedation_HD as "X-Ray & Sedation (HD)",
    cp.Bitch_Spay_20kg_Competitor as "Bitch_Spay__20kg__Competitor", 
    cp.Castrate_Dog_20kg_Competitor as "Castrate_Dog__20kg__Competitor",
    cp.Cat_Castrate_Competitor, cp.Cat_Spay_Competitor, 
    cp.Cat_Vaccination_Competitor,
    cp.Consultation_Competitor, 
    cp.Dog_Vaccination_DHPPI_Competitor as "Dog_Vaccination_DHPPI_Competitor", 
    cp.X_Ray_Sedation_HD_Competitor as "X_Ray___Sedation__HD__Competitor"
  FROM geo_percentages AS g
  LEFT JOIN geo_demographics USING (Clinic_ID)
  LEFT JOIN competitor_summary AS c USING (Clinic_ID)
  LEFT JOIN price_index_features AS p USING (Clinic_ID)
  LEFT JOIN price_joined AS cp USING (Clinic_ID)
  LEFT JOIN department_dim AS d ON g.Clinic_ID = d.ID_Department
  LEFT JOIN vet_fte_12M_ending_may25 AS v25 ON d.CostCenterCode = v25.COST_CODE
  LEFT JOIN total_fte_12M_ending_may25 AS t25 ON d.CostCenterCode = t25.COST_CODE
  LEFT JOIN nps_median AS n ON d.CostCenterCode = CAST(n.OaSurgeryCostCode AS BIGINT)
  LEFT JOIN revenue_pivoted AS r ON CAST(g.Clinic_ID AS STRING) = CAST(r.ID_Department AS STRING);
select * from final_data limit 10;


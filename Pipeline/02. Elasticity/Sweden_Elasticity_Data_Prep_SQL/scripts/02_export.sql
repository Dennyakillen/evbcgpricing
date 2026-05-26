PRAGMA enable_object_cache;

COPY master_core_save
TO (OUTPUT_DIR() || '/\\Sweden_masterdata.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported master data successfully' AS msg;

COPY item_desciption
TO (OUTPUT_DIR() || '/\item_description.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported Item Description data successfully' AS msg;


COPY weekly_cluster
TO (OUTPUT_DIR() || '/\Sweden_weekly_model_data_P_C.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported cluster level data successfully' AS msg;

COPY weekly_ch
TO (OUTPUT_DIR() || '/\Sweden_weekly_model_data_P_CH.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported clinic hospital level data successfully' AS msg;

COPY weekly_site
TO (OUTPUT_DIR() || '/\Sweden_weekly_model_data_site_level.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported site level data successfully' AS msg;

COPY fallback_base_final
TO (OUTPUT_DIR() || '/\Comple_Product_Data.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported fallback data successfully' AS msg;
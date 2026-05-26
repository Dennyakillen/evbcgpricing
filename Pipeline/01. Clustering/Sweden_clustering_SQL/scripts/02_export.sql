PRAGMA enable_object_cache;

COPY final_data
TO (OUTPUT_DIR() || '/\Clustering_Raw_Data_new.csv')
WITH (HEADER, DELIMITER ',');
SELECT 'Exported completed successfully' AS msg;

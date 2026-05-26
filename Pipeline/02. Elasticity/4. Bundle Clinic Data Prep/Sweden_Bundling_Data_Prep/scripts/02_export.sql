PRAGMA enable_object_cache;

COPY bundle_cluster_data
TO (OUTPUT_DIR() || '/Raw_Data_Clinic_Hospital.csv')
WITH (HEADER, DELIMITER ',');

COPY fte_final
TO (OUTPUT_DIR() || '/Sweden_Clinic_Hospital_FTE_Data.csv')
WITH (HEADER, DELIMITER ',');

COPY bundles_final
TO (OUTPUT_DIR() || '/bundlegroup_bundle_mapping.csv')
WITH (HEADER, DELIMITER ',');

COPY bundle_exploded
TO (OUTPUT_DIR() || '/Bundle_Clinic_Data.csv')
WITH (HEADER, DELIMITER ',');
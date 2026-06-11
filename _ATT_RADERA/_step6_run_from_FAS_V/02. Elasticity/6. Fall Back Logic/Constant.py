### All Product X Clinic Path
df_product_path = r".\output_data\Complete_Product_Data_Blended.xlsx"

### All product from Alteryx path 
df_all_product_path = r".\input_data\Complete_Product_Data.xlsx"

#### Cluster Level Granularity: Blended output path
blended_output_path = r"2. Product Cluster Level Models\output\final_model_cluster_granularity.xlsx"

### Blended Model Path
blended_model_path = r"2. Product Cluster Level Models\output\output_summary_ready.xlsx"

### Product Site level Path
prod_site_level_path = r"3. Product Site Level Models\output\model\output_summary.xlsx"


### Bundle Cluster Level Model Path
bundle_cluster_level_path = r"5. Bundle Clinic Models\output\model\output_summary.xlsx"

### Renaming Alteryx Columns for Fallback Logic
column_rename_dict_df_product = {'ItemCode':'ProductKey',
                                'ItemDescription':'ProductDescription',
                                'ProductGroupL4Name':'service',
                                'New_Cluster':'Clusters',
                                'ID_Department':'SiteCode',
                                'SalesTotal':'TotalNet',
                                'SalesTotal_YearEnding25':'year ending 2025 revenue'}

### Renaming Blended Model Columns
column_rename_dict_df_blended =  {'Cluster':'Clusters',
                                  'ItemCode':'ProductKey',
                                  'QuantitySold(SalesTotal>0)':'Sum_Qty(TotalNet>=0)',
                                  'PVALUE_Regular_Price_fwbw_max_6':'PVALUE_PRICE',
                                  'ELASTICITY_Regular_Price_fwbw_max_6':'ELASTICITY_PRICE'}
### Dfcluster Dataframe column order
dfcluster_column_order = ['KEY', 'TotalNet', 'Sum_Qty(TotalNet>=0)', 'Correl', 'RSQ', 'ADJ_RSQ', 'ELASTICITY_PRICE','PVALUE_PRICE', 'Clusters', 'ProductKey', 'significant_Clusters', 'service']


### Renaming dict for site level model
column_rename_dict_df_site = {'QuantitySold(SalesTotal>0)':'Sum_Qty(TotalNet>=0)',
                                'ELASTICITY_Regular_Price_fwbw_max_6':'ELASTICITY_PRICE',
                                'PVALUE_Regular_Price_fwbw_max_6':'PVALUE_PRICE'}

### Renaming Bundle Cluster level model dict
column_rename_dict_df_bundle = {'ELASTICITY_Regular_Price_fwbw_max_6':'ELASTICITY_PRICE',
                                'PVALUE_Regular_Price_fwbw_max_6':'PVALUE_PRICE'}

### Renaming of merged dataframes
rename_map_merged_dv7 = {
    "ELASTICITY_PRICE_site": "F1_site_level",
    "wt_elas_cluster_bundle": "F2_bundle_level",
    "ELASTICITY_PRICE_cluster": "F3_cluster_level",
    "wt_elas_bundle": "F4_bundle_across_clusters",
    "wt_elas_cluster": "F5_product_across_clusters",
    "wt_elas_within_cluster_service": "F6_service_within_cluster",
    "wt_elas_cluster_service": "F7_service_across_clusters"}

### columns to convert to numeric
numeric_cols = [
    "F1_site_level","F2_bundle_level","F3_cluster_level",
    "F4_bundle_across_clusters","F5_product_across_clusters",
    "F6_service_within_cluster","F7_service_across_clusters"]

### Elasticity Labels
elasticity_level_labels = ["F1 site level",
                           "F2 bundle level",
                           "F3 cluster level",
                           "F4 bundle across clusters",
                           "F5 product across clusters",
                           "F6 service within cluster",
                           "F7 service across clusters"]

elasticity_to_product_granularity = {
    "F1 site level": "Product Key",
    "F2 bundle level": "Bundle",
    "F3 cluster level": "Product Key",
    "F4 bundle across clusters": "Bundle",
    "F5 product across clusters": "Product Key",
    "F6 service within cluster": "Service",
    "F7 service across clusters": "Service"
}

# Mapping: elasticity_level to Site Granularity
elasticity_to_site_granularity = {
    "F1 site level": "Site",
    "F3 cluster level": "Cluster",
    "F2 bundle level": "Cluster",
    "F5 product across clusters": "Overall",
    "F4 bundle across clusters": "Overall",
    "F6 service within cluster": "Cluster",
    "F7 service across clusters": "Overall"}

### Column name used
service  =  "service"
Cluster = "Clusters"
ELASTICITY_PRICE = "ELASTICITY_PRICE"
TotalNet = "TotalNet"
ProductKey = "ProductKey"
Basket_Revenue = 'basket_revenue'
ELASTICITY_basket_price = 'ELASTICITY_basket_price'
SiteCode = 'SiteCode'
ITEMCODE = 'ItemCode'
ITEMDESCRIPTION = 'ItemDescription'
PRODUCTGROUPL4NAME = 'ProductGroupL4Name'
IDDEPARTMENT = 'ID_Department'


### Output Data
output_path = r".\output_data" 
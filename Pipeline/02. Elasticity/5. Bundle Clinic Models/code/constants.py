import os
from datetime import datetime, timedelta
import yaml
with open(r".\code\src\config.yml") as file:
    config = yaml.safe_load(file)

# Common constants
DATE = "week_starting_monday"
KEY = "KEY"
ADJUSTED_REGULAR_PRICE = "ADJUSTED_REGULAR_PRICE"
ALGO_REGULAR_PRICE = 'Regular_Price_fwbw_max_6'
DISCOUNT = "DISCOUNT"
HOLIDAY = "HOLIDAY"
OCCASION = "OCCASION"
YEAR = "YEAR"
MONTH = "MONTH"
WEEK = 'WEEK'
START_DATE = os.environ.get("BCG_START_DATE", "2022-07-01")
END_DATE   = os.environ.get("BCG_END_DATE",   "2025-06-29")
END_DATE2  = (datetime.strptime(END_DATE, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

### Special weeks where sweden clinics experienced low mewdia coverage
_DEFAULT_SPECIAL_WEEKS = '2025-01-27,2024-03-11,2024-03-18,2024-03-25,2024-04-01,2024-04-08,2024-04-15,2024-04-22'
SPECIAL_WEEKS = [w.strip() for w in os.environ.get("BCG_SPECIAL_WEEKS", _DEFAULT_SPECIAL_WEEKS).split(",") if w.strip()]
SPECIAL_WEEK_PERIOD_1 =  ['2025-01-27' ]
SPECIAL_WEEK_PERIOD_2 = ['2024-03-11','2024-03-18','2024-03-25','2024-04-01','2024-04-08','2024-04-15','2024-04-22']
### Major Holiday List
MAJOR_SWEDEN_HOLIDAY_LIST = [
        "Easter Monday","Christmas Eve","Christmas Eve; Sunday","Christmas Day","Christmas Day; Sunday",
        "Second Day of Christmas","Good Friday","Midsummer Day","Midsummer Eve","New Year's Eve",
        "New Year's Day","New Year's Eve; Sunday","New Year's Day; Sunday","Epiphany","Easter Sunday; Sunday"]

### data preparation constant after model output
RANK = "Rank"
KEY_WEEK = "Key-week"
TRAIN_TEST = "TRAIN_TEST"
APE = "APE"
REGULAR_PRICE_COL = "Regular_Price_fwbw_max_6"
ELASTICITY_COL = "ELASTICITY_Regular_Price_fwbw_max_6"
RSQ_COL = "RSQ"
ADJ_RSQ = "ADJ_RSQ"
Correl_col = 'Correl'
PVALUE_PREFIX = "PVALUE_"
# P-Value summary output schema
PVALUE_SUMMARY_COLS = ["feature_name","used_in_model","significant_in_model","pct_significant"]


print('Taking Constants for Bundle Level Models')
PRICE = "basket_price"
DOLLAR = "basket_revenue"
VOLUME = "VOLUME(KG)"
UNIT = "Bundle_visits"
Product_Code_var = 'Bundle_code'  # Bundle_code for bundle-level models
Cluster_Granularity = 'Clusters'  # Clusters for bundle-level models
Cluster_Granularity2 = 'Cluster'  # Clusters for bundle-level models
SERVICE_VAR = 'ProductGroupL4Name' # Name of the service column
YOY_SEASONALITY_GROUPBY_COL_NAMES = ['Clusters', 'Bundle_code']   ### List of column to aggregate for calculating YOY Seasonality
DESC_COL_PRODUCT = "Bundle_description"  ### Bundle Description
PRICE_COLS = [KEY_WEEK, PRICE, "num_of_sites"] ### Price-related columns to merge in model summary
# Final standardized output columns
FINAL_SUMMARY_COLS = [
    KEY_WEEK, KEY, DATE, TRAIN_TEST, UNIT,
    f"PRED_{UNIT}", APE, Cluster_Granularity,
    Product_Code_var, DESC_COL_PRODUCT, RANK,
    PRICE, "num_of_sites"]
### Output Column for model output summary
FINAL_OUTPUT_COLS = [
    KEY, DOLLAR, UNIT, Correl_col, RSQ_COL, ADJ_RSQ, ELASTICITY_COL, PVALUE_PREFIX + ALGO_REGULAR_PRICE, Cluster_Granularity2, 
    Product_Code_var, DESC_COL_PRODUCT, RANK,
    "Weighted elasticity", "Weighted  rsq", 'Bundle Group', 'Check', 'Significant ?', "Weighted Pvalue"]
# Bundle group mapping file path
BUNDLE_GROUP_MAPPING_PATH = r".\output\bundlegroup_bundle_mapping.xlsx"
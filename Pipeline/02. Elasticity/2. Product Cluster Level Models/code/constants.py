import os
from datetime import datetime, timedelta

# Common constants
PRICE = "PRICE"
DOLLAR = "TotalNet"
VOLUME = "VOLUME(KG)"
UNIT = "QuantitySold(SalesTotal>0)"
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

# ===========================================================================
# DATE WINDOW  (G7 fix, FAS F — Jens Palmö)
# ---------------------------------------------------------------------------
# Env-overridable so a fresh run needs NO code edit — set the end date and run.
#   BCG_START_DATE  fixed anchor of the growing window (default 2022-07-01)
#   BCG_END_DATE    last day of data to include (default = BCG's frozen 2025-06-29)
# Unset = BCG's original frozen window, so replication is reproduced EXACTLY
# (this is the easy way back to the old facit: run with no env vars set).
# Growing window by design (fixed anchor): elasticity gets more robust as months
# accrue; rolling windows are a deliberate later analytical step, not done here.
START_DATE = os.environ.get("BCG_START_DATE", "2022-07-01")
END_DATE   = os.environ.get("BCG_END_DATE",   "2025-06-29")
# END_DATE2 = exclusive upper bound (day after END_DATE) used by model.py filters.
# Derived, never hardcoded — follows END_DATE automatically on a fresh run.
END_DATE2 = (datetime.strptime(END_DATE, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
# ===========================================================================

### Special weeks where sweden clinics experienced low mewdia coverage
# Env-overridable (comma-separated) so new media periods can be added without
# editing code. Default = BCG's original media periods (reproduces old behaviour).
_DEFAULT_SPECIAL_WEEKS = ('2025-01-27,2024-03-11,2024-03-18,2024-03-25,'
                          '2024-04-01,2024-04-08,2024-04-15,2024-04-22')
SPECIAL_WEEKS = [w.strip() for w in
                 os.environ.get("BCG_SPECIAL_WEEKS", _DEFAULT_SPECIAL_WEEKS).split(",")
                 if w.strip()]
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
Product_Code_var = 'ItemCode'  # ItemCode for product-site level models
Cluster_Granularity = 'Cluster'  # Cluster for site-level models
SERVICE_VAR = 'ProductGroupL4Name' # Name of the service column
YOY_SEASONALITY_GROUPBY_COL_NAMES = ['service']   ### List of column to aggregate for calculating YOY Seasonality
DESC_COL_PRODUCT = "ItemDescription"   ### Product Description
PRICE_COLS = [KEY_WEEK, PRICE, DOLLAR, SERVICE_VAR]  ### Price-related columns to merge in model summary
### Output Column for model output summary
FINAL_OUTPUT_COLS = [
    KEY, DOLLAR, UNIT, Correl_col, RSQ_COL, ADJ_RSQ, ELASTICITY_COL, PVALUE_PREFIX + ALGO_REGULAR_PRICE,  
    "Weighted elasticity", "Weighted  rsq", "Weighted PValue",
     "Check", "Significant ?",
    Cluster_Granularity, Product_Code_var, DESC_COL_PRODUCT, SERVICE_VAR, RANK
   ]
SERVICE_OUTPUT_NAME = "Service"
### Constants for blending logic
KEY_WEEK_blended = "Datekey"
Product_Code_var_data_prep = "Product Description"
NO_OF_SITES = "No of Sites"
# Final standardized output columns
FINAL_SUMMARY_COLS = [
    KEY_WEEK_blended, KEY, DATE, TRAIN_TEST, UNIT,
    f"PRED_{UNIT}", APE, PRICE, ALGO_REGULAR_PRICE, Product_Code_var_data_prep, SERVICE_OUTPUT_NAME, Cluster_Granularity,
    Product_Code_var, RANK, NO_OF_SITES]
##blended    
cluster_h_map={'Clinics 0':'Clinics', 'Clinics 1':'Clinics', 'Clinics 2':'Clinics', 'Clinics':'Clinics_CH', 'Hospital':'Hospital_CH',
               'Sjukhus A':'Hospital', 'Sjukhus B':'Hospital', 'Sjukhus C':'Hospital', 'Sjukhus SÃ¶dran':'Hospital'}
clustermap={'Clinics':'Clinics','Clinics_CH':'Clinics', 'Hospital_CH':'Hospital', 'Hospital':'Hospital'}

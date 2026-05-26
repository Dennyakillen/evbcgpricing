### Specify Path For Raw Productive Files
productive_time_data_path = r".\input_data\250716 - Master Dict.xlsx"
### Specify sheetname For Raw Productive Files
productive_time_data_sheet_name = "QUINYX_YEAR_WEEK"
### Specify ID Department & Cluster mapping
cluster_mapping_sheet_name = "Cluster Mapping New"
### Specify Path For Raw Productive Files
old_productive_time_data_path = r".\input_data\0807_Sweden_ProductiveTime_Sweden.xlsx"
### Id Department & costCenterCode Mapping
iddepartment_cost_center_code_mapping_path = r".\input_data\Cost_center_code_iddepartment_mapping.xlsx"

### Column name to replace in Productive Time Data
productive_df_col_rename = {'CostCentreExtCode':'CostCenterCode', 'FTEs': 'SumProductiveTime'}

#### Removing week number and year due to wrong data
weeknumber_year_combination = [(15, 2023)]

### Column names
YEAR = "Year"
WEEKNUMBER = "Weeknumber"
COSTCENTERCODE = "CostCenterCode"
SUMPRODUCTIVETIME = "SumProductiveTime"
IDDEPARTMENT = "ID_Department"
WEEKSTARTINGMONDAY = "week_starting_monday"
DATE = "Date"
STAFFCATEGORYDESCRIPTION = "StaffCategoryDescription"
UPDATED_SUMPRODUCTIVETIME = "UpdatedSumProductiveTime"
CLUSTER = "Cluster"
UPDATED_SUMPRODUCTIVETIME = "Updated" + SUMPRODUCTIVETIME




### Old Productive Time file
# Column rename mapping for old productive time file
PRODUCTIVE_TIME_RENAME_MAP = {
    "Quinex[CostCentreCode]": COSTCENTERCODE,
    "Quinex[Date]": DATE,
    "Quinex[StaffCategoryDescription]": STAFFCATEGORYDESCRIPTION,
    "Quinex[ID_Date]": "ID_Date",
    "[SumTotalTime]": "SumTotalTime",
    "[SumVaccation]": "SumVaccation",
    "[SumShortTimeLeave]": "SumShortTimeLeave",
    "[SumOtherPlannedLeave]": "SumOtherPlannedLeave",
    "[SumProductiveTime]": UPDATED_SUMPRODUCTIVETIME,
}

# Filters for old productive time data
STAFF_CATEGORY_FILTER = "vets"  
# Considering Sites for which the new productive time data is missing from the old data
COST_CENTER_CODES_FILTER = [8081, 8091, 8078, 8029]  

# Cluster for the COST_CENTER_CODES_FILTER sites
DEFAULT_CLUSTER_NAME = "Clinics 1"

# Weeks to exclude from old productive time files
EXCLUDED_WEEKS = ["2023-04-10"]  

### FIlter date for 1st week of july 2022
filter_date = '2022-06-27'


### filling Missing Sites data for missing weeks
missing_weeks = '2025-06-01'
## cluster to be imputed from 
cluster_name  = "Clinics 1"
### Sites to impute missing data for
missing_sites = [115, 8091, 505, 108]


#### Output File Path
output_file = r".\output_data\Sweden__Interpolated_Productivity_time_date_june25.xlsx"
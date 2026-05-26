### Importing Libraries
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from pandas import ExcelWriter
import itertools
from ast import literal_eval
import ray
import json
from utils import *
from constants import *

# Path to this config file
config_file = Path(__file__).resolve().parent /"src"/ "config.yml"

# Load YAML
with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Resolve module_path relative to config file location
module_path = (config_file.parent / config["module_path"]).resolve()

print("Module Path:", module_path)

### Ray configuration
cpus = config['ray']['cpus']
store_memory = config['ray']['memory'] 
batch = config['ray']['batch']
### Initiating Ray
ray.init(
    ignore_reinit_error=True,
    num_cpus=cpus,  # Use 18 CPUs out of 20 (leaving 2 for system tasks)
    object_store_memory=store_memory * 1024**3,  # Allocate 32GB for object store memory
    _system_config={
        "object_spilling_config": json.dumps({
            "type": "filesystem",
            "params": {"directory_path": "C:\\ray_spill"}
        })
    }
)

# Global variables
model_group = config['unique_key_var']
date_var = config['date_var']
dep_var = config['dep_var']
train_perc = config['train_perc']
print("model_group:", model_group)
print("date_var:", date_var)
print("dep_var:", dep_var)


def get_model_groups_to_try(df):
    """
    Returns a list of model groups (KEYs) from the DataFrame where RUN is marked as 'YES'.

    Parameters:
    -----------
    df : pd.DataFrame
        Control DataFrame with columns 'RUN' and 'KEY'.

    Returns:
    --------
    List[str]
        Unique list of model group keys to be processed.
    """
    model_groups = df[df["RUN"] == "YES"]["KEY"].unique().tolist()
    return model_groups

### Reading Raw CSV Data
def read_data(file):
    """
    Reads a CSV file into a pandas DataFrame.

    Parameters:
    -----------
    file : str
        Path to the CSV file.

    Returns:
    --------
    pd.DataFrame
        Loaded data.
    """

    df = pd.read_csv(file)
    return df

### Reading Raw EXCEL Data
def read_excel(file):
    """
    Reads an Excel file into a pandas DataFrame.

    Parameters:
    -----------
    file : str
        Path to the Excel file.

    Returns:
    --------
    pd.DataFrame
        Loaded data.
    """

    df = pd.read_excel(file)
    return df

### Loading Control File
def load_or_create_feature_control_file(df, file):
    """
    Loads an existing model control file or creates a new one based on the DataFrame.

    Parameters:
    -----------
    df : pd.DataFrame
        Raw input DataFrame for model training.

    file : str
        Path to the control Excel file.

    Returns:
    --------
    pd.DataFrame
        Control DataFrame with feature selection and train-test split information.
    """

    if (Path(file)).exists():
        print("Model Control File exists")
        control_file = pd.read_excel(file)
        return control_file

    else:
        print(f"Created Model Control File, please update file at {file}")
        control_var_list = [x for x in list(df.columns) if x not in [date_var, dep_var, model_group]]
        control_var_list.insert(0, "TRAIN")
        control_var_list.insert(0, "RUN")

        train = train_perc
        test = 1 - train

        df.sort_values([KEY, DATE], inplace=True)

        control_file = pd.DataFrame(df_raw[model_group].unique(), columns=[model_group])
        for newcol in control_var_list:
            control_file[newcol] = np.nan

        control_file["RUN"] = "YES"
        for x in control_file[model_group]:
            control_file.loc[control_file[model_group] == x, "TRAIN"] = df_raw[df_raw[model_group] == x].tail(
                1 if round(df_raw[df_raw[model_group] == x].shape[0] * test) == 0 else round(
                    df_raw[df_raw[model_group] == x].shape[0] * test))[date_var].iloc[0]

        control_file.to_excel(file, index=False)
        
### Filtering Data for atleast 104 weeks
def filter_data(df,weeks):
    """
    Filters the DataFrame to only include KEYs with more than the specified number of weeks.

    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame with DATE and KEY columns.

    weeks : int
        Minimum number of unique weeks required.

    Returns:
    --------
    pd.DataFrame
        Filtered DataFrame.
    """

    check=df.groupby(KEY).agg({DATE:'nunique'}).reset_index()
    keys=check[check[DATE]>weeks][KEY].unique()
    df=df[df[KEY].isin(keys)]
    return df

### Implementing Ray
@ray.remote
def process_feature_batch(
    config, df_filter, features_list, i, details_path, count_iteration
):
    """
    Runs model training and evaluation for each feature combination in the batch.

    Parameters:
    -----------
    config : dict
        Model configuration settings.

    df_filter : pd.DataFrame
        Filtered data for one model group.

    features_list : list of lists
        List of feature combinations to try.

    i : int
        Index of the model group.

    details_path : str
        Path to save model run details.

    count_iteration : int
        Current batch iteration index.

    Returns:
    --------
    pd.DataFrame
        Concatenated performance results for the feature combinations.
    """

    
    batch_results = []
    batch_iteration = 1
    for features in features_list:
        perf = model_for_feature_selection(
            config,
            df_filter,
            features,
            i,
            details_path
        )
        batch_results.append(perf)
        batch_iteration += 1
    if batch_results:
        result = pd.concat(batch_results)
    else:
        result = pd.DataFrame()
    return result

@ray.remote
def process_model_group(
    mg,
    df_raw,
    df_control,
    cols_to_try , cols_needed, summary_path, details_path, batch_size, i
):
    """
    Runs feature selection and model evaluation for a single model group.

    Parameters:
    -----------
    mg : str
        Model group key.

    df_raw : pd.DataFrame
        Raw input data.

    df_control : pd.DataFrame
        Feature control file.

    cols_to_try : list
        List of features to try during selection.

    cols_needed : list
        Mandatory columns to always include in the model.

    summary_path : str
        Path to save summary output.

    details_path : str
        Path to save detailed model results.

    batch_size : int
        Number of combinations per batch.

    i : int
        Iteration index.

    Returns:
    --------
    pd.DataFrame
        Result DataFrame with model performance metrics.
    """


    df_filter = df_raw[df_raw["KEY"] == mg].copy()
    
    model_group_result = pd.DataFrame(
        columns=['i', "Model group", 'len', 'Variables', 'No. of Insignificant', 'Insignificant',
                    'No. of multicollinear', 'multicollinear features', 'MAPE', 'WMAPE', 'Adj R2', 'BASELINE_Std_Dev',
                    'INCREMENTAL_Std_Dev', "Multiple Seasonality"])
    
    print(i)
    print(mg,df_filter.shape)

    train_test_date = df_control.loc[df_control['KEY'] == mg, "TRAIN"].to_list()
    df_filter["TRAIN_TEST"] = np.where(df_filter[date_var] <= train_test_date[0], "TRAIN", "TEST")

    # Adding constant to the Dataframe to run the regression with intercept
    df_filter['CONST'] = 1

    all_features_combinations = []
    

    for L in range(1, len(cols_to_try) + 1):
        for subset in itertools.combinations(cols_to_try, L):

            seasonality_cols = [col for col in subset if 'SEASONALITY' in col.upper()]
            if len(seasonality_cols) > 1:
                continue

            else:
                features = cols_needed + list(subset)
                all_features_combinations.append(list(set(features)))

    # Batch processing feature combinations in parallel
    batch_results = []
    count_iteration = 0
    for batch_start in range(0, len(all_features_combinations), batch_size):
        batch = all_features_combinations[batch_start : batch_start + batch_size]
        res = process_feature_batch.remote(
            config,
            df_filter,
            batch,
            details_path,
            i,
            count_iteration,
        )
        batch_results.append(res)
        count_iteration += 1

    # Collect all parallel batch results
    results = ray.get(batch_results)
    model_group_result = pd.concat(results)

    model_group_result = model_group_result.reset_index(drop=True)

    model_group_result["i"] = model_group_result.index + 1

    try:
        if "/" in mg:
            mg = mg.replace("/", "or")
        model_group_result.to_excel(f"{summary_path}{mg}_All_itrs.xlsx", index=False)
    except:
        print(f"exception for {mg}, Saving with the name {mg[:40]}")
        if "/" in mg:
            mg = mg.replace("/", "or")
        model_group_result.to_excel(f"{summary_path}{mg[:30]}_All_itrs.xlsx", index=False)

    return model_group_result


def iterative_combination(df_raw, df_control, models_groups, cols_to_try, cols_needed, summary_path, details_path):
    """
    Runs the modeling pipeline for multiple model groups in parallel.

    Parameters:
    -----------
    df_raw : pd.DataFrame
        Raw dataset.

    df_control : pd.DataFrame
        Control file for model configuration.

    models_groups : list
        List of model groups to run.

    cols_to_try : list
        List of candidate features to evaluate.

    cols_needed : list
        List of mandatory features to always include.

    summary_path : str
        Path to save summary output files.

    details_path : str
        Path to save detailed run information.

    Returns:
    --------
    pd.DataFrame
        Combined model results across all model groups.
"""

    batch_size = batch
    # Run all model groups in parallel
    
    eligible_model_groups = [mg for mg in model_groups if df_raw[df_raw["KEY"] == mg].shape[0]!=0]
    print(eligible_model_groups)
    
    results = ray.get(
        [
            process_model_group.remote(
                mg,
                df_raw,
                df_control,
                cols_to_try, cols_needed, summary_path, details_path, batch_size, i
            )
            for i, mg in enumerate(eligible_model_groups, 1)
        ]
    )
    
    # Combine results
    result_df = pd.concat(results)

    result_df = result_df.reset_index(drop=True)

    result_df["i"] = result_df.index + 1

    result_df.to_excel(f"{summary_path}All_combinations.xlsx", index=False)
    
    return result_df


def update_control_file(df_control, X_for_models):
    """
    Updates the control file based on selected features from best models.

    Parameters:
    -----------
    df_control : pd.DataFrame
        Control file to be updated.

    X_for_models : pd.DataFrame
        Result DataFrame containing selected features for each model group.

    Returns:
    --------
    pd.DataFrame
        Updated control file with feature selections marked as 1.
    """

    df_control.loc[:, df_control.columns[3:]] = 0

    for key in X_for_models['Model group'].unique():

        tmp = X_for_models[X_for_models['Model group'] == key].copy()
        tmp.reset_index(drop=True, inplace=True)

        try:
            features = [col for col in literal_eval(tmp['Variables'][0]) if col != "CONST"]
            df_control.loc[df_control['KEY'] == key, features] = 1

        except:
            features = [col for col in tmp['Variables'][0] if col != "CONST"]
            df_control.loc[df_control['KEY'] == key, features] = 1

    return df_control


def features_for_left_over(df_control, models_with_no_sigs, result_df):
    """
    Updates the control file with best available features for model groups with no significant variables.

    Parameters:
    -----------
    df_control : pd.DataFrame
        Feature control file.

    models_with_no_sigs : list
        List of model groups that had no significant features.

    result_df : pd.DataFrame
        Full model run result DataFrame.

    Returns:
    --------
    pd.DataFrame
        Updated control file.
    """

    remaining_mg = result_df[result_df["Model group"].isin(models_with_no_sigs)]
    remaining_mg.sort_values('Adj R2', inplace=True)
    remaining_mg.drop_duplicates(subset="Model group", inplace=True)
    print(remaining_mg)
    for key in remaining_mg['Model group'].unique():
        tmp = remaining_mg[remaining_mg["Model group"] == key]

        try:
            features = [col for col in literal_eval(tmp['Variables'][0]) if col != "CONST"]
            df_control.loc[df_control['KEY'] == key, features] = 1

        except:
            features = [col for col in tmp['Variables'][0] if col != "CONST"]
            df_control.loc[df_control['KEY'] == key, features] = 1
    return df_control

def check_nulls(df, df_control):
    """
    Checks whether any of the selected variables in the control file contain null values.

    Parameters:
    -----------
    df : pd.DataFrame
        Full dataset.

    df_control : pd.DataFrame
        Control file with selected variables marked.

    Returns:
    --------
    None
        Prints status of nulls in selected variables.
    """

    df_control_t = df_control.melt([model_group, 'RUN', 'TRAIN'], var_name='VARIABLE',
                                   value_name="VALUE").sort_values(by=model_group).reset_index(drop=True)

    null_check_var = (df_control_t[df_control_t['VALUE'] == 1]['VARIABLE']).unique().tolist()
    if df_raw[null_check_var].isnull().sum().sum() == 0:
        print("Varibles contain no-null values")
    else:
        print("Varibles contain null values")

### Imputing Missing Values
def impute_missing(df, config):
    """
    Fills missing values in the dataset based on the specified imputation technique.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with missing values.

    config : dict
        Configuration dictionary specifying imputation technique and column types.

    Returns:
    --------
    pd.DataFrame
        DataFrame with missing values imputed.
    """
    technique = config['imputation']['technique']
    df = df.copy()
    for col in df.drop(DOLLAR,axis=1).columns:
        df[col] = df[col].astype(config['col_type'][col])
        if config['col_type'][col]!='float64':
            continue
        if col in [HOLIDAY]:
            df[col]=df[col].fillna(0)
        n_missing_before = df[col].isnull().sum()
        if n_missing_before:
            if technique == 'mean':
                df[col] = df[col].fillna(df[col].mean())
            elif technique == 'median':
                df[col] = df[col].fillna(df[col].median())
            elif technique == 'zero':
                df[col] = df[col].fillna(0)
            elif technique == 'ffill':
                df[col] = df[col].fillna(method='ffill')
            elif technique == 'bfill':
                df[col] = df[col].fillna(method='bfill')
            n_missing_after = df[col].isnull().sum()
    return df


def save_data(df, file):
    """
    Saves a DataFrame to a CSV file.

    Parameters:
    -----------
    df : pd.DataFrame
        Data to save.

    file : str
        File path to write the CSV.

    Returns:
    --------
    None
    """

    df.to_csv(file, index=False)
    
def save_results_excel(df, file):
    """
    Saves a DataFrame to an Excel file.

    Parameters:
    -----------
    df : pd.DataFrame
        Data to save.

    file : str
        File path to write the Excel file.

    Returns:
    --------
    None
    """

    df.to_excel(file, index=False)

if __name__ == '__main__':
    # Resolve module_path relative to config file location
    module_path = (config_file.parent / config["module_path"]).resolve()

    # Define the path for the raw input data dynamically based on the model type
    raw_input_data = os.path.join(module_path, config['feature_selection']['raw_input_data'].lstrip("/\\"))

    # Define the control file path dynamically based on the model type
    control_file_path = os.path.join( module_path, config['feature_selection']['control_file_path'].lstrip("/\\"))

    # Define the save path for AutoML summary dynamically based on the model type
    automl_save_path = os.path.join(module_path, config['feature_selection']['automl_summary'].lstrip("/\\"))

    # Define the save path for detailed AutoML results dynamically based on the model type
    automl_details_save_path = os.path.join( module_path,config['feature_selection']['automl_details'].lstrip("/\\"))

    # Retrieve columns to try based on the model type
    cols_to_try = config['feature_selection']['cols_to_try']

    # Retrieve necessary columns based on the model type
    cols_needed = config['feature_selection']['cols_needed']

    # Define the save path for the final control file dynamically based on the model type
    control_file_save_path = os.path.join(module_path, config['feature_selection']['final_results'].lstrip("/\\"))

    # Define the save path for selected features dynamically based on the model type
    selected_feature_save_path = os.path.join(module_path,config['feature_selection']['selected_features_save_path'].lstrip("/\\"))

    # Define the save path for all features dynamically based on the model type
    all_feature_save_path = os.path.join(module_path, config['feature_selection']['all_features_save_path'].lstrip("/\\"))

    # Read data
    df_raw = read_data(raw_input_data)
    
    # Control file
    control_file = load_or_create_feature_control_file(df_raw, control_file_path)

    # Checking if null in input features
    check_nulls(df_raw, control_file)
    df_raw = df_raw.replace([np.inf, -np.inf], np.nan)
    
    df_raw=impute_missing(df_raw,config)
    check_nulls(df_raw, control_file)
    print(f"Shape before week filter = {df_raw.shape}")
    df_raw=filter_data(df_raw,103)
    print(f"Shape after week filter = {df_raw.shape}")

    # Read Control File
    control_file = read_excel(control_file_path)

    model_groups = get_model_groups_to_try(control_file)

    print(f"Shape before removing 0 Units = {df_raw.shape}")
    print(f"Unique KEY before removing 0 Units = {df_raw.KEY.nunique()}")

    df_raw=clean_columns(df_raw)

    print(f"\nShape After removing 0 Units = {df_raw.shape}")
    print(f"Unique KEY After removing 0 Units = {df_raw.KEY.nunique()}")

    # Iterative Combination
    result_df = iterative_combination(df_raw, control_file, model_groups, cols_to_try, cols_needed, automl_save_path,
                                     automl_details_save_path)
    save_data(result_df, all_feature_save_path)
    
    # Get best features
    X_for_models, models_with_no_sigs = get_best_features(result_df, model_groups)
    print(models_with_no_sigs)

    # Update control file automatically
    df_control = update_control_file(control_file, X_for_models)

    # Remaining Models
    df_control = features_for_left_over(df_control, models_with_no_sigs, result_df)

    # Save Selected Features
    save_data(X_for_models, selected_feature_save_path)

    # Save Control File
    save_results_excel(df_control, control_file_save_path)
    # Saving Control File in Control Folder
    save_results_excel(df_control, control_file_path)
    
    
# Importing Libraries

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import accuracy_score
from sklearn import tree
from sklearn.metrics import pairwise_distances
from sklearn import metrics as met
import warnings
warnings.filterwarnings('ignore')
import os
import yaml
from pathlib import Path


if __name__ == '__main__':
    
    # Get base dir
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent 
    config_file_path = base_dir/"config.yaml"
    # Load config file
    with open(config_file_path) as file:
        config = yaml.safe_load(file)

    input_file_path = project_root/"Input"
    print(input_file_path)
    geo_data_file_path = input_file_path/config['geo_data_filename']

    # Read geo data
    seg_input2 = pd.read_excel(geo_data_file_path)
    print("Geo Data read complete", seg_input2.shape)
    ## Filtering Data for clinics
    seg_input2 = seg_input2[seg_input2['Geo_Cluster'].isin(config['geo_cluster'])]

    seg_input2 = seg_input2[~seg_input2['Clinic ID'].isin(config['hospital_sites_to_be_removed'])]

    # Caculating Revenue Metrics
    seg_input2['24-23YoY_Revenue'] = ((seg_input2['12M_ending_Jun_24'] / seg_input2['12M_ending_Jun_23']) - 1)*100
    seg_input2['25-24YoY_Revenue'] = ((seg_input2['12M_ending_Jun_25'] / seg_input2['12M_ending_Jun_24']) - 1)*100
    seg_input2['CAGR'] = ((seg_input2['12M_ending_Jun_25'] / seg_input2['12M_ending_Jun_23']) ** (1/2)) - 1

    # Create a dictionary for renaming
    rename_dict = {col: f'Revenue_{col}' for col in config['revenue_cols']}
    # Rename in your DataFrame
    seg_input2 = seg_input2.rename(columns=rename_dict)
    print('shape of dataframe: ', seg_input2.shape)

    df=seg_input2.copy()

    # replacing 0 by null for index metrics
    df[config['index_features']]=df[config['index_features']].replace(0,None)

    # Imputing missing values by MEDIAN BY DIVISION
    median_df = df.groupby('BusinessArea')[config['features_median_imputation']].median().reset_index()

    for col in config['features_median_imputation']:
        # Use the transform method to align the median values to each group
        df[col] = df.groupby('BusinessArea')[col].transform(lambda x: x.fillna(x.median()))


    overall_med = df[config['features_median_imputation']].median()
    overall_df = overall_med.rename_axis('column').reset_index(name='median')

    # Impute missing values with overall median for which there are no imputation made at Region/GroupCode level
    for col in config['features_median_imputation']:
        # Use the transform method to align the median values to each group
        df[col] = df[col].transform(lambda x: x.fillna(x.median()))

    # Imputing competitor columns with 0
    df[config['competitor_features']]=df[config['competitor_features']].fillna(0)


    # Getting capping_values for each variable
    bounds = (
        df[config['outlier_capping_features']]
        .quantile([0.05, 0.95])     # computes both percentiles
        .T                          # columns -> rows
        .rename(columns={0.05: 'Lower_Bound', 0.95: 'Upper_Bound'})
    )
    bounds_df = bounds.reset_index().rename(columns={'index': 'column'})


    # Loop through each column and cap values between the 5th and 95th percentiles
    for col in config['outlier_capping_features']:
        # Calculate the 5th and 95th percentiles
        lower_bound = df[col].quantile(0.05)
        upper_bound = df[col].quantile(0.95)
        
        # Use clip to cap the values between the percentiles
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    # Export overall median
    overall_median_output_file_path = project_root/"Output/overall_median.csv"
    overall_df.to_csv(overall_median_output_file_path, index=False)

    # export regional median dataframe
    region_median_output_file_path = project_root/"Output/region_median.csv"
    median_df.to_csv(region_median_output_file_path, index=False)

    # Export bounds
    bounds_file_path = project_root/"Output/bounds.csv"
    bounds_df.to_csv(bounds_file_path, index = False)

    # Export pre-processed data
    preprocessed_file_path = project_root/"Output/Sweden_Clustering_Data_Treated_new.csv"
    df.to_csv(preprocessed_file_path, index=False)
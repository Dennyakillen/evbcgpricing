import pandas as pd
import numpy as np
from datetime import datetime
import seaborn as sns
from datetime import datetime
import os

from statsmodels.stats import diagnostic as diag
import statsmodels.stats.api as sms
import statsmodels.api as sm
from statsmodels.compat import lzip
from statsmodels.stats.outliers_influence import variance_inflation_factor

import warnings
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
from scipy import stats
import pickle
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
from pandas import ExcelWriter

import warnings

warnings.filterwarnings("ignore")


# from assumptions_check import get_report

def clean_columns(df, date_format=None):
    df["week_starting_monday"] = pd.to_datetime(df["week_starting_monday"], format=date_format)
    return df


def reg_price_calc(df, avg_price_col, level_col, date_col, window_size, minimum_window, grouping_method, calc_method,
                   percentile_value=0.95, smoothing_weeks_window=0):
    """
    This function is used to calculate the regular price basis the promo price.
    regular price is calculated using different rolling aggregation with different calculation methods like max, percentile etc.

    :param df: raw data in which you'd want to add the regular price column
    :param avg_price_col: specify the name of the promo price column on which the operation will be done
    :param level_col: specify the level at which regular price needs to be calculated (SKU, Sub-brand, Unique key ,etc.)
    :param date_col: specify the date/ any time identifier column in the data
    :param window_size: specify the window size of the rolling calculation
    :param minimum_window: specify the minimum window for the rolling calculation
    :param grouping_method: "bw" (backward rolling) or "fwbw" (forward-backward rolling)
    :param calc_method: "max" or "percentile"
    :param percentile_value: 0 to 1
    :param smoothing_weeks_window: 0 if smoothing is not required otherwise # weeks (typically 4) for smoothing regular price
    :return: a dataframe with regular price variable added to the raw dataframe
    """
    # -------------------- Backward-only (bw) + max --------------------
    if (grouping_method == "bw") & (calc_method == "max"):
        # Build the output column name using method details
        name_of_regular_price_col = "Regular_Price" + "_" + str(grouping_method) + "_" + str(calc_method) + "_" + str(
            window_size)

        # Sort by product level and date ascending to ensure correct backward rolling
        df = df.sort_values([level_col, date_col], ascending=True)
        df = df.reset_index(drop=True)

        # Compute rolling max within each level group
        df[name_of_regular_price_col] = \
            df.groupby(by=[level_col])[avg_price_col].rolling(window_size, minimum_window).max().reset_index()[
                avg_price_col]

    # -------------------- Backward-only (bw) + percentile --------------------
    if (grouping_method == "bw") & (calc_method == "percentile"):
        # Column name includes the percentile value and window
        name_of_regular_price_col = "Regular_Price" + "_" + str(grouping_method) + "_" + str(calc_method) + "_" + str(
            percentile_value) + "_" + str(window_size)

        # Sort ascending for backward roll
        df = df.sort_values([level_col, date_col], ascending=True)
        df = df.reset_index(drop=True)

        # Compute rolling quantile per level
        df[name_of_regular_price_col] = \
            df.groupby(by=[level_col], as_index=False)[avg_price_col].rolling(window_size, minimum_window).quantile(
                percentile_value)[avg_price_col]

    # -------------------- Forward-backward (fwbw) + max --------------------
    if (grouping_method == "fwbw") & (calc_method == "max"):
        name_of_regular_price_col = "Regular_Price" + "_" + str(grouping_method) + "_" + str(calc_method) + "_" + str(
            window_size)

        # Forward roll: sort dates descending (simulate future-looking window), then rolling max
        df = df.sort_values([level_col, date_col], ascending=[True, False])  ## used for forward rolling
        df = df.reset_index(drop=True)
        df["FORWARD_ROLLING"] = \
            df.groupby(by=[level_col], as_index=False)[avg_price_col].rolling(window_size, minimum_window).max()[
                avg_price_col]

        # Backward roll: sort dates ascending, then rolling max
        df = df.sort_values([level_col, date_col], ascending=[True, True])
        df = df.reset_index(drop=True)
        df["BACKWARD_ROLLING"] = \
            df.groupby(by=[level_col], as_index=False)[avg_price_col].rolling(window_size, minimum_window).max()[
                avg_price_col]

        # Take the conservative estimate: min of forward and backward
        df[name_of_regular_price_col] = df[["FORWARD_ROLLING", "BACKWARD_ROLLING"]].min(axis=1)
        

    # -------------------- Forward-backward (fwbw) + percentile --------------------
    if (grouping_method == "fwbw") & (calc_method == "percentile"):
        name_of_regular_price_col = "Regular_Price" + "_" + str(grouping_method) + "_" + str(calc_method) + "_" + str(
            percentile_value) + "_" + str(window_size)

        # Forward roll with quantile
        df = df.sort_values([level_col, date_col], ascending=[True, False])  ## used for forward rolling
        df = df.reset_index(drop=True)
        df["FORWARD_ROLLING"] = \
            df.groupby(by=[level_col], as_index=False)[avg_price_col].rolling(window_size, minimum_window).quantile(
                percentile_value)[avg_price_col]

        # Backward roll with quantile
        df = df.sort_values([level_col, date_col], ascending=[True, True])
        df = df.reset_index(drop=True)
        df["BACKWARD_ROLLING"] = \
            df.groupby(by=[level_col], as_index=False)[avg_price_col].rolling(window_size, minimum_window).quantile(
                percentile_value)[avg_price_col]

        # Conservative combine: take min of forward/backward
        df[name_of_regular_price_col] = df[["FORWARD_ROLLING", "BACKWARD_ROLLING"]].min(axis=1)
        df.drop(['FORWARD_ROLLING', 'BACKWARD_ROLLING'], axis=1, inplace=True)

    # -------------------- Optional smoothing --------------------
    if smoothing_weeks_window > 0:
        df = df.sort_values([level_col, date_col], ascending=True)
        df = df.reset_index(drop=True)
        df[name_of_regular_price_col] = \
            df.groupby(by=[level_col], as_index=False)[name_of_regular_price_col].rolling(smoothing_weeks_window).max()[
                name_of_regular_price_col]

    return df


def rolling_seasonality(df, seasonality_base_column, level_col, date_col, window_size, minimum_window, grouping_method):
    """
    This function is used to calculate the rolling seasonality basis the base column defined (quantity, revenue, etc.).
    Rolling seasonality is calculated using rolling aggregation like mean at different product levels

    :param df: raw data in which you'd want to add the seasonality column
    :param seasonality_base_column: specify the base column on which seasonality needs to be calculated
    :param level_col: specify the product level at which seasonality is to be calculated (SKU, Sub-brand, Unique key ,etc.)
    :param date_col: specify the date/ any time identifier column in the data
    :param window_size: specify the window size of the rolling calculation
    :param minimum_window: specify the minimum window for the rolling calculation
    :param grouping_method: "bw" (backward rolling) or "fwbw" (forward-backward rolling)
    :return: a dataframe with seasonality variable added to the raw dataframe
    """

    if grouping_method == "bw":
	# Name: Seasonality_KEY_bw_<window>
        name_of_seasonality_col = "Seasonality" + "_" + str(level_col) + "_" + str(grouping_method) + "_" + str(
            window_size)

        # Aggregate to (level, date) and treat zeros as NaN to avoid biasing means
        df_grouped = df.groupby(by=[level_col, date_col], as_index=False).agg({seasonality_base_column: 'sum'})
        df_grouped[seasonality_base_column] = df_grouped[seasonality_base_column].replace(0, np.nan)
        df_grouped.sort_values([level_col, date_col], inplace=True)

        # Shift (using original df per the existing logic) so current week uses prior period
        df_grouped[seasonality_base_column] = df.groupby(level_col)[seasonality_base_column].shift(1)

        # Ensure ascending order and clean index before rolling
        df_grouped = df_grouped.sort_values([level_col, date_col], ascending=True)



        df_grouped = df_grouped.reset_index(drop=True)

        # Rolling mean within each level
        df_grouped[name_of_seasonality_col] = \
            df_grouped.groupby(by=[level_col], as_index=False)[seasonality_base_column].rolling(window_size,
                                                                                                minimum_window).mean()[
                seasonality_base_column]

        # Fill gaps both backward and forward within each level
        df_grouped[name_of_seasonality_col] = df_grouped.groupby(by=[level_col], as_index=False)[
            name_of_seasonality_col].fillna(method='bfill')

        df_grouped[name_of_seasonality_col] = df_grouped.groupby(by=[level_col], as_index=False)[
            name_of_seasonality_col].fillna(method='ffill')

        # Merge seasonality back to original df
        df = df.merge(df_grouped[[level_col, date_col, name_of_seasonality_col]], on=[level_col, date_col])

    if grouping_method == "fwbw":
        # Name: Seasonality_KEY_fwbw_<window>
        name_of_seasonality_col = "Seasonality" + "_" + str('KEY') + "_" + str(grouping_method) + "_" + str(
            window_size)

        # Aggregate to (level, date) sums; convert zeros to NaN
        df_grouped = df.groupby(by=[level_col, date_col], as_index=False).agg({seasonality_base_column: 'sum'}).replace(0,np.nan)

        # Forward-looking mean: sort descending by date, then roll
        df_grouped = df_grouped.sort_values([level_col, date_col], ascending=[True, False])  ## used for forward rolling
        df_grouped = df_grouped.reset_index(drop=True)
        df_grouped["FW_SEASONALITY"] = \
            df_grouped.groupby(by=[level_col], as_index=False)[seasonality_base_column].rolling(window_size,
                                                                                        minimum_window).mean()[
                seasonality_base_column]

        # Backward-looking mean: sort ascending by date, then roll
        df_grouped = df_grouped.sort_values([level_col, date_col], ascending=True)
        df_grouped = df_grouped.reset_index(drop=True)
        df_grouped["BW_SEASONALITY"] = \
            df_grouped.groupby(by=[level_col], as_index=False)[seasonality_base_column].rolling(window_size,
                                                                                                minimum_window).mean()[
                seasonality_base_column]

        # Combine forward/backward estimates via simple average (as in original)
        df_grouped[name_of_seasonality_col] = df_grouped[["FW_SEASONALITY", "BW_SEASONALITY"]].mean(axis=1)

        # Merge combined seasonality back
        df = df.merge(df_grouped[[level_col, date_col, name_of_seasonality_col]], on=[level_col, date_col])

    return df



def period_seasonality(df, seasonality_base_column, level_col, date_col, period_col):
    """
    This function is used to calculate the period seasonality basis the base column defined (quantity, revenue, etc.).
    Period seasonality is calculated using aggregation like mean at different product levels for particular month, week, etc.

    :param df: raw data in which you'd want to add the seasonality column
    :param seasonality_base_column: raw data in which you'd want to add the seasonality column
    :param level_col: specify the product level at which seasonality is to be calculated (SKU, Sub-brand, Unique key ,etc.)
    :param date_col: specify the date/ any time identifier column in the data
    :param period_col: specify the column over which aggregation is to be done for the seasonality calculation
    :return: a dataframe with seasonality variable added to the raw dataframe
    """
    name_of_seasonality_col = "Period_Seasonality" + "_" + str(level_col)

    # Aggregate to (level, date, period) then take the mean within (level, period)
    df_grouped = df.groupby(by=[level_col, date_col, period_col], as_index=False).agg({seasonality_base_column: 'sum'})

    df_grouped = df_grouped.groupby(by=[level_col, period_col], as_index=False).agg({seasonality_base_column: 'mean'})

    # Rename aggregated metric to period seasonality column
    df_grouped.rename(columns={seasonality_base_column: name_of_seasonality_col}, inplace=True)

    # Merge back to original df on (level, period)
    df = df.merge(df_grouped[[level_col, period_col, name_of_seasonality_col]], on=[level_col, period_col])

    return df


def model(control, df, config, scale=False):
    df_coef = pd.DataFrame()  # coefficient Dataframe to store model group - variable coeff data
    df_avp = pd.DataFrame()  # Dataframe to store AvP, Baseline and Incremental Split
    df_summary = pd.DataFrame()  # Dataframe to store the summary of each model at model group level
    vif_data = pd.DataFrame()

    model_save_path = config['save_model']
    date_var = config['date_var']
    dep_var = config['dep_var']
    model_group = config['model_group']


    # Ensure the TRAIN cutoff in control is datetime
    control["TRAIN"] = pd.to_datetime(control["TRAIN"])

    # Iterate through model groups where RUN=="YES"
    for i, x in enumerate(
            control[control["RUN"] == "YES"][model_group].to_list()):  # iterate over chosen groups in control file

        print("-" * 20)
        print(x)
        # independent variable list (Value=1 in the control file for given model group)
        control_t = control.melt([model_group, 'RUN', 'TRAIN'], var_name='VARIABLE', value_name="VALUE").sort_values(
            by=model_group).reset_index(drop=True)
        ind_var = control_t.loc[(control_t[model_group] == x) & (control_t["VALUE"] == 1), "VARIABLE"].to_list()

        # train test split date specified in the control file
        train_test_date = control.loc[control[model_group] == x, "TRAIN"].to_list()

        # Filtering required data basis model group, date, dependent and independent variables
        df_filter = df.loc[df[model_group] == x, [model_group] + [date_var] + [dep_var] + ind_var]

        if df_filter.shape[0] == 0:
            print(f"Cant model {x}")
            continue
        print(df_filter.shape)
        print(f'Model running for {x}')

        if scale:
            std_scaler = StandardScaler()
            # Here only dependent variable is scaled if requested
            df_filter[dep_var] = std_scaler.fit_transform(df_filter[dep_var].to_numpy())


        # Flagging dates as train and test based upon train_test_date
        df_filter[date_var] = pd.to_datetime(df_filter[date_var])
        df_filter["TRAIN_TEST"] = np.where(df_filter[date_var] <= train_test_date[0], "TRAIN", "TEST")

        # Adding constant to the Dataframe to run the regression with intercept
        df_filter['CONST'] = 1

        # Splitting the data in train and test
        df_train = df_filter.loc[df_filter["TRAIN_TEST"] == "TRAIN"]
        df_test = df_filter.loc[df_filter["TRAIN_TEST"] == "TEST"]

        # If there is no test data, move the last train row into test to avoid empty split
        if df_test.shape[0] == 0:
            df_test = df_train.tail(1)
            df_train = df_train[:df_train.shape[0] - 1]

        # X_train, X_test, y_train, y_test splits
        X_train = df_train[["CONST"] + ind_var]
        X_test = df_test[["CONST"] + ind_var]
        y_train = df_train[dep_var]
        y_test = df_test[dep_var]
        X_train = X_train.replace([np.inf, -np.inf], np.nan)

        # Run model
     
        lin_model = sm.OLS(y_train, X_train.astype(float))

        # fit the model
        fit_train = lin_model.fit()

        # Predict on test and compute R2 for sanity (not stored in outputs here)
        y_predict_test = fit_train.predict(X_test)
        test_r2 = r2_score(y_test, y_predict_test)
        print(X_test.shape,(len(X_test) - len(X_test.columns) - 1))

        # ____COEFFICIENTS____

        # Extract coefficient table from statsmodels summary via HTML parsing
        df_coef_temp = pd.read_html(fit_train.summary().tables[1].as_html(), header=0, index_col=0)[0]
        df_coef_temp["VARIABLES"] = df_coef_temp.index
        # Re-arranging the columns to place variable name first
        df_coef_temp = df_coef_temp[df_coef_temp.columns.to_list()[-1:] + df_coef_temp.columns.to_list()[:-1]]
        df_coef_temp.columns = ['VARIABLE', 'ESTIMATE', 'STD_ERROR', 'TSTAT', 'PVALUE', 'P25', "P75"]
        df_coef_temp["RSQ"] = fit_train.rsquared  # adding the rsquare
        df_coef_temp["ADJ_RSQ"] = fit_train.rsquared_adj  # adding adjused rsquare
        df_coef_temp[model_group] = x  # adding the model grop information
        df_coef_temp.reset_index(drop=True, inplace=True)  # dropping the index since we have variable column now

        # df_coef = df_coef.append(df_coef_temp)  # appending the coef data for all model groups in one DF
        df_coef=pd.concat([df_coef,df_coef_temp])
        df_coef.reset_index(drop=True, inplace=True)

        ########################################

        ########################################

        # _________ACTUAL, PREDICTED, BASELINE & INCREMENTAL SALES SPLIT_________

        # Creating temporary dataframe with model group, date, train-test, actual and predicted information
        df_avp_temp = df_filter.loc[:, [model_group] + [date_var] + ["TRAIN_TEST"] + [dep_var]]
        df_avp_temp["PRED_" + dep_var] = pd.concat([fit_train.predict(X_train),(fit_train.predict(X_test))])

        # BASELINE VS INCREMENTAL
        X_temp=pd.concat([X_train,X_test])

        for var in X_temp.columns.to_list():
            X_temp[var] = X_temp[var] * fit_train.params[var]

        

        # Absolute Percentage Error (unweighted)
        df_avp_temp['APE'] = abs(df_avp_temp[dep_var] - df_avp_temp["PRED_" + dep_var]) / df_avp_temp[dep_var]
        # Appending the data in a dataframe to export
        df_avp=pd.concat([df_avp,df_avp_temp])
        df_avp.reset_index(drop=True, inplace=True)

        ########################################

        ########################################

        ## SUMMARY
        df_summary_temp = pd.DataFrame({model_group: [x]
                                           , "DATA_POINTS": [df_avp_temp.shape[0]]
                                           , "DEP_TOTAL": [df_avp_temp[dep_var].sum()]
                                           , "RSQ": [fit_train.rsquared]
                                           , "ADJ_RSQ": [fit_train.rsquared_adj]
                                        })

        df_summary=pd.concat([df_summary,df_summary_temp])
        df_summary.reset_index(drop=True, inplace=True)

        # Actual, Predicted, residual, 
        data = df_filter[[dep_var, 'CONST'] + ind_var].copy()
        data['Predicted'] = fit_train.predict(data[['CONST'] + ind_var])
        data.rename(columns={dep_var: 'Actual'}, inplace=True)
        data['Residuals'] = data['Actual'] - data['Predicted']

        # VIF dataframe
        tmp_vif = pd.DataFrame()
        tmp_vif["feature"] = X_temp.columns

        # calculating VIF for each feature
        tmp_vif["VIF"] = [variance_inflation_factor(X_temp.values, i)
                          for i in range(len(X_temp.columns))]

        tmp_vif["KEY"] = x

        vif_data = pd.concat([vif_data, tmp_vif])

    print("Total Models built: ", i + 1)

    return df_coef, df_avp, df_summary, vif_data


def model_for_feature_selection(config, df_filter, ind_var, i, save_path):
    df_coef = pd.DataFrame()
    df_avp = pd.DataFrame()
    df_summary = pd.DataFrame()

    model_group = config['unique_key_var']
    date_var = config['date_var']
    dep_var = config['dep_var']
    rev_var = config['rev_var']

    mg = df_filter[model_group].unique()[0]
    df_filter = df_filter[[model_group, date_var, dep_var] + ind_var + ["TRAIN_TEST", rev_var]].copy()

    # Fill any missing values with zeros to keep OLS happy (original behavior retained)
    if df_filter.isna().sum().sum() > 0:
        print(f"{mg} data have nulls in the following columns; filling with 0:")
        print(df_filter.columns[df_filter.isna().any()].tolist())
        df_filter.fillna(0, inplace=True)
    df_train = df_filter[df_filter["TRAIN_TEST"] == "TRAIN"]
    df_test = df_filter[df_filter["TRAIN_TEST"] == "TEST"]

    # Ensure we always have a test observation
    if df_test.shape[0] == 0:
        df_test = df_train.tail(1)
        df_train = df_train.iloc[:-1]

    X_train = df_train[ind_var]
    X_test = df_test[ind_var]
    y_train = df_train[dep_var]
    y_test = df_test[dep_var]
    lin_model = sm.OLS(y_train, X_train.astype(float))
    fit_train = lin_model.fit()
    adj_r2 = fit_train.rsquared_adj

    # Tidy coefficients table
    df_coef_temp = pd.read_html(fit_train.summary().tables[1].as_html(), header=0, index_col=0)[0]
    df_coef_temp["VARIABLES"] = df_coef_temp.index
    df_coef_temp = df_coef_temp[df_coef_temp.columns.to_list()[-1:] + df_coef_temp.columns.to_list()[:-1]]
    df_coef_temp.columns = ['VARIABLE', 'ESTIMATE', 'STD_ERROR', 'TSTAT', 'PVALUE', 'P25', "P75"]
    df_coef_temp["RSQ"] = fit_train.rsquared
    df_coef_temp["ADJ_RSQ"] = fit_train.rsquared_adj
    df_coef_temp["KEY"] = mg
    df_coef_temp.reset_index(drop=True, inplace=True)

    df_coef = pd.concat([df_coef, df_coef_temp], ignore_index=True)

    # Build AVP table with predictions for both splits
    df_avp_temp = df_filter[[model_group, date_var, "TRAIN_TEST", dep_var, rev_var]].copy()
    df_avp_temp["PRED_" + dep_var] = pd.concat([fit_train.predict(X_train), fit_train.predict(X_test)], ignore_index=True)

    mape = mean_absolute_percentage_error(df_avp_temp[dep_var], df_avp_temp["PRED_" + dep_var])

    # Build contributions matrix for VIF computation
    X_temp = pd.concat([X_train, X_test], ignore_index=True)
    for var in X_temp.columns:
        X_temp[var] *= fit_train.params[var]

    # Error metrics including weighted APE (by revenue)
    df_avp_temp['APE'] = abs(df_avp_temp[dep_var] - df_avp_temp["PRED_" + dep_var]) / df_avp_temp[dep_var]
    df_avp_temp['WAPE'] = df_avp_temp['APE'] * df_avp_temp[rev_var]
    wmape = np.average(df_avp_temp['APE'], weights=df_avp_temp[rev_var])

    df_avp = pd.concat([df_avp, df_avp_temp], ignore_index=True)

    # Summary table (not used downstream directly but kept as in original)
    df_summary_temp = pd.DataFrame({
        model_group: [mg],
        "DATA_POINTS": [df_avp_temp.shape[0]],
        "DEP_TOTAL": [df_avp_temp[dep_var].sum()],
        "RSQ": [fit_train.rsquared],
        "ADJ_RSQ": [fit_train.rsquared_adj],
    })

    df_summary = pd.concat([df_summary, df_summary_temp], ignore_index=True)

    # Count insignificant variables and list them
    no_insig = len(df_coef_temp[df_coef_temp['PVALUE'] > 0.1])
    insignificant = ', '.join(df_coef_temp[df_coef_temp['PVALUE'] > 0.1]['VARIABLE'].tolist())

    # Compute VIFs to detect multicollinearity
    vif_data = pd.DataFrame()
    vif_data["feature"] = X_temp.columns
    vif_data["VIF"] = [variance_inflation_factor(X_temp.values, i) for i in range(len(X_temp.columns))]
    multicollinear_features = vif_data[vif_data['VIF'] > 10]["feature"].tolist()

    # Build a single-row output summarizing performance and diagnostics
    p = pd.DataFrame({
        "i": [i],
        "Model group": [mg],
        "len": [len(ind_var)],
        "Variables": [ind_var],
        "No. of Insignificant": [no_insig],
        "Insignificant": [insignificant],
        "No. of multicollinear": [len(multicollinear_features)],
        "multicollinear features": [', '.join(multicollinear_features)],
        "MAPE": [mape],
        "WMAPE": [wmape],
        "Adj R2": [adj_r2]
    })

    # Pivot coefficients to wide format with Elasticities and P-values
    coef_business = df_coef.pivot(index='KEY', columns='VARIABLE', values=['ESTIMATE', 'PVALUE']).reset_index()
    coef_business.columns = [f"{col1}_{col2}" if col2 else col1 for col1, col2 in coef_business.columns]
    coef_business.rename(columns={"KEY_": 'KEY'}, inplace=True)
    coef_business.columns = coef_business.columns.str.replace('ESTIMATE', 'ELASTICITY')

    p = p.merge(coef_business, right_on="KEY", left_on="Model group")

    return p


def mean_absolute_percentage_error(y_true, y_pred):
    ##Calculation mean absolute percentage error
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100


def baseline_imputation(df):
    df['Baseline_Null'] = df.apply(lambda x: np.nan if x < 0 else x)
    df['Baseline_ffill'] = df['Baseline_Null'].fillna(method='ffill')
    df['Baseline_ffill'] = df['Baseline_ffill'].fillna(method='bfill')
    df['Baseline_bfill'] = df['Baseline_Null'].fillna(method='bfill')
    df['Baseline_bfill'] = df['Baseline_bfill'].fillna(method='ffill')
    df['Baseline_Final'] = (df['Baseline_bfill'] + df['Baseline_ffill']) / 2
    return df['Baseline_Final']


def get_best_features(result_df, models_groups):
    """
    Select the best feature set per model group using business and statistical rules.

    Args:
        DataFrame with candidate model results per group. Must include
            columns:
              - 'ELASTICITY_Regular_Price_fwbw_max_6'
              - 'PVALUE_Regular_Price_fwbw_max_6'
              - 'Adj R2'
              - 'Model group'
        models_groups: List of all model group identifiers to ensure coverage.

    Returns:
            X_for_models: DataFrame containing the top-ranked row for each
                model group after sorting by:
                  1) negative price elasticity (preferred),
                  2) price p-value <= 0.2 (preferred),
                  3) higher Adjusted R^2.
    """
    
        
    result_df['elasticity_flag']=np.where(result_df['ELASTICITY_Regular_Price_fwbw_max_6']<0,1,0)
    result_df['p_value_price_flag'] = np.where(result_df['PVALUE_Regular_Price_fwbw_max_6']<=0.2,1,0)

    result_df = result_df.sort_values(['Model group','elasticity_flag','p_value_price_flag',"Adj R2"],
                                      ascending=[True,False,False,False])

    X_for_models = result_df.drop_duplicates(subset='Model group', keep='first')

    models_with_no_sigs = list(set(models_groups) - set(X_for_models['Model group'].unique().tolist()))

    return X_for_models, models_with_no_sigs


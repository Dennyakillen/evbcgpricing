# importing Libraries


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')
import yaml
from pathlib import Path
from Kmeans_Gen import Kmeans_Generator
from sklearn.preprocessing import StandardScaler
sc_x=StandardScaler()
from Overwrite_Excel import write_df_preserve_named_range

# Standalone function to save plots

def score_plot(df, name, ranges, output_dir):
    # Create figure
    plt.figure(figsize=(15,3))
    plt.plot(ranges, df, marker='o')
    plt.title(name)
    plt.xlabel('Number of clusters')
    plt.ylabel(name)

    # Make sure Output folder exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save plot
    file_path = output_dir / f"{name.replace(' ', '_')}.png"
    plt.savefig(file_path, bbox_inches="tight")
    plt.close()   # close so it doesn't stack up in memory

if __name__ == '__main__':
    
    # Get base dir
    # base_dir = Path.cwd()
    base_dir = Path(__file__).resolve().parent 
    
    project_root = base_dir.parent 
    output_dir = project_root / "Output"
    config_file_path = base_dir/"config.yaml"
    
    # Load config file
    with open(config_file_path) as file:
        config = yaml.safe_load(file)

    # Reading pre processed file
    preprocessed_file_path = project_root/"Output"/config['pre_processed_filename']
    df = pd.read_csv(preprocessed_file_path)
    print("Read pre-processed file ", df.shape)

    # Initializing object
    km=Kmeans_Generator(df,config['clust_cols'],config['prof_cols'])

    if config['experiment_iteration'] == "Yes":        

        num_cluster=[2,3,4,5,6,7,8,9,10]
        wwss,silht_scr,ch_score,db_index,row_sdf_kmeans=km.multi_kmeans(num_cluster)
        clustering_metrics_file_path = output_dir/"metrics_collated.csv"
        row_sdf_kmeans.to_csv(clustering_metrics_file_path, index=False)
        score_plot(wwss, 'WCSS', num_cluster, output_dir)
        score_plot(silht_scr, 'Silhouette Score', num_cluster, output_dir)
        score_plot(ch_score, 'Calinski-Harabasz', num_cluster, output_dir)
        score_plot(db_index, 'Davies-Bouldin Index', num_cluster, output_dir)
    else:
        it,dat,full_data,data,scaler_params,centroid = km.single_kmeans(config['optimal_clusters'])
        scalar_params_file_path = output_dir/"scaler_params_Sweden.csv"
        centroid_file_path = output_dir/"centroids_cluster_Sweden.csv"
        scaler_params.reset_index().to_csv(scalar_params_file_path,index=False)
        centroid.reset_index().to_csv(centroid_file_path,index=False)
        
        data.columns=config['clust_cols'] + ['Clusters']

        print(data.groupby(['Clusters']).agg({'TotalPopulation':'count'}).reset_index())
        
        # Get Mean of clustering variables

        df1=full_data.groupby('Clusters')[config['clust_cols']].mean().reset_index()
        melted_df = pd.melt(df1, 
                            id_vars='Clusters', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df['Metric']='Mean'

        # Get median of clustering variables
        df2=full_data.groupby('Clusters')[config['clust_cols']].median().reset_index()
        melted_df1 = pd.melt(df2, 
                            id_vars='Clusters', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df1['Metric']='Median'

        final_df=pd.concat([melted_df,melted_df1])

        cdf1=pd.pivot_table(final_df,index=['Columns','Metric'],columns='Clusters',values='Values',aggfunc='sum').reset_index()

        # Getting overall median and mean
        full_data['Group']='Overall'
        df1=full_data.groupby('Group')[config['clust_cols']].mean().reset_index()
        melted_df = pd.melt(df1, 
                            id_vars='Group', 
                            var_name='Columns', 
                            value_name='Values')
        
        # Getting overall mean of clustering variables
        melted_df['Metric']='Mean'
        df2=full_data.groupby('Group')[config['clust_cols']].median().reset_index()
        melted_df1 = pd.melt(df2, 
                            id_vars='Group', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df1['Metric']='Median'

        final_df=pd.concat([melted_df,melted_df1])

        cdf=pd.pivot_table(final_df,index=['Columns','Metric'],columns='Group',values='Values',aggfunc='sum').reset_index()

        # For clustering variables
        final=cdf1.merge(cdf,on=['Columns','Metric'])

        clustering_var_file_path = output_dir/"clustering_variables_summary.csv"
        final.to_csv(clustering_var_file_path,index=False)
        print("Clustering Variable summary generated ", final.shape)

               
        write_df_preserve_named_range(
            file_path = project_root / "Sweden_Clustering_Summary.xlsx",
            df = final,
            sheet_name = "Clustering_Variable",
            named_range = "clustering_variables_named_range",
            start_cell = "A1",
            refresh_pivots = False,
            visible = False  )

        profiling_cols_excel = [col for col in config['prof_cols'] if col not in ['Clinic ID', 'Region']]

        full_data_sc=full_data.copy()

        for col in profiling_cols_excel :
        # Calculate the 5th and 95th percentiles
            lower_bound = full_data_sc[col].quantile(0.05)
            upper_bound = full_data_sc[col].quantile(0.95)
            
            # Use clip to cap the values between the percentiles
            full_data_sc[col] = full_data_sc[col].clip(lower=lower_bound, upper=upper_bound)

        df1=full_data_sc.groupby('Clusters')[profiling_cols_excel].mean().reset_index()
        melted_df = pd.melt(df1, 
                            id_vars='Clusters', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df['Metric']='Mean'

        df2=full_data_sc.groupby('Clusters')[profiling_cols_excel].median().reset_index()
        melted_df1 = pd.melt(df2, 
                            id_vars='Clusters', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df1['Metric']='Median'

        final_df=pd.concat([melted_df,melted_df1])

        cdf1=pd.pivot_table(final_df,index=['Columns','Metric'],columns='Clusters',values='Values',aggfunc='sum').reset_index()


        full_data_sc['Group']='Overall'
        df1=full_data_sc.groupby('Group')[profiling_cols_excel].mean().reset_index()
        melted_df = pd.melt(df1, 
                            id_vars='Group', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df['Metric']='Mean'

        df2=full_data_sc.groupby('Group')[profiling_cols_excel].median().reset_index()
        melted_df1 = pd.melt(df2, 
                            id_vars='Group', 
                            var_name='Columns', 
                            value_name='Values')
        melted_df1['Metric']='Median'

        final_df=pd.concat([melted_df,melted_df1])

        cdf=pd.pivot_table(final_df,index=['Columns','Metric'],columns='Group',values='Values',aggfunc='sum').reset_index()

        ##profiling variables
        final = cdf1.merge(cdf,on=['Columns','Metric'])

        profiling_var_file_path = output_dir/"profiling_variables_summary.csv"
        final.to_csv(profiling_var_file_path,index=False)
        print("Profiling Varibales generated ", final.shape)

        

        # Merging total population column on full data
        full_data = pd.merge(full_data, df[['Clinic ID',  '2024 Total Population Age 0-14',
       '2024 Total Population Age 15-29', '2024 Total Population Age 30-44',
       '2024 Total Population Age 45-59', '2024 Total Population Age 60+']], on = 'Clinic ID', how = 'left')
        data_in_scope_var_file_path = output_dir/"clustered_data.csv"
        full_data.to_csv(data_in_scope_var_file_path,index=False)
        print("Clustering Complete ", full_data.shape)

        
        write_df_preserve_named_range(
            file_path = project_root / "Sweden_Clustering_Summary.xlsx",
            df = final,
            sheet_name = "Profiling_Variable",
            named_range = "profiling_variables_named_range",
            start_cell = "A1",
            refresh_pivots = False,
            visible = False  )
        
                
        write_df_preserve_named_range(
            file_path = project_root / "Sweden_Clustering_Summary.xlsx",
            df = full_data,
            sheet_name = "Data_in_scope",
            named_range = "Age",
            start_cell = "A1",
            refresh_pivots = False,
            visible = False  )

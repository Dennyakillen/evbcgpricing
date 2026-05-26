import time
start_time_master=time.time()
from sklearn.cluster import KMeans
from sklearn import metrics
import pandas as pd
from sklearn.preprocessing import StandardScaler
sc_x=StandardScaler()
from sklearn.model_selection import train_test_split
from sklearn.ensemble import ExtraTreesClassifier


class Kmeans_Generator: 
    data = pd.DataFrame()
    clust_var = []
    prof_var = []
      
    # parameterized constructor 
    def __init__(self,dat,clust_vars,prof_vars): 
        self.data = dat 
        self.clust_var = clust_vars
        self.prof_var = prof_vars


    def label_distribution(iter,size,clust):
        lb_kmeans=pd.Series(iter).value_counts().reset_index().sort_values('index')
        lb_kmeans.columns =['Cluster','Number']
        lb_kmeans['Percentage']= lb_kmeans['Number']/size
        lb_kmeans['Number_Perctge'] = (size/clust)/size
        lb_kmeans[['Cluster','Percentage','Number_Perctge']]
        lb_kmeans['Diff'] = lb_kmeans['Number_Perctge'] - lb_kmeans['Percentage']
        return lb_kmeans

# Returns all Evaluation metrics as individiual arrays        
    def multi_kmeans(self,clusters):
        wcss=[]
        silht_scr=[]
        ch_score =[]
        db_index =[]
        row_s =[]

        dat = self.data[self.clust_var]
        data = sc_x.fit_transform(dat)

        for i in clusters:
                #print(i)

                kmeans = KMeans(n_clusters=i, init = 'k-means++', random_state=20)

                iter_labels=kmeans.fit_predict(data)
                ch = round(metrics.calinski_harabasz_score(data, iter_labels),4)
                db=round(metrics.davies_bouldin_score(data, iter_labels),4)
                silhouette_avg= round(metrics.silhouette_score(data, iter_labels),4)

                wcss.append(kmeans.inertia_)
                silht_scr.append(silhouette_avg)
                ch_score.append(ch)
                db_index.append(db)

                #No of clusters and it's distribution
                lbls=pd.Series(iter_labels).value_counts().reset_index().sort_values('index')
                lbls.columns =['Cluster','Number']
                median = lbls['Number'].median()

                #Expected Number
                df = pd.DataFrame(data)
                rows = df.shape[0]
                exp_median = round(rows/i)

                #print('Kmeans',i,median,exp_median,Number_less)
                
                iteration = 'Kmeans-'+str(i)
                it = [iteration,'Kmeans',i,median,exp_median,silhouette_avg,ch,db,round(kmeans.inertia_,2)]
                #print(it)
                row_s.append(it)

        cls=['Iteration','Technique','No_of_clusters','Median','Expected median','silhouette score','CH-Index','DB-Index','Inertia']
        row_sdf= pd.DataFrame(row_s,columns=cls)
        row_sdf['Median_ratio'] = round(row_sdf['Median']/row_sdf['Expected median'],2)
        row_sdf = row_sdf[['Iteration','Technique','No_of_clusters','Median','Median_ratio','silhouette score','CH-Index','DB-Index','Inertia']]

        return wcss,silht_scr,ch_score,db_index,row_sdf
    
# # Returns a summary DataFrame includes all metrics at a Cluster-Iteration level
#     def visual_kmeans_distribution(self,num_clusters):
#         summry_df = pd.DataFrame([])
        
#         for i in num_clusters:
            
#             dat = self.data[self.clust_var]
#             data = sc_x.fit_transform(dat)

#             y=dat.iloc[:,0]
#             a,b,c,d=train_test_split(dat,y,test_size=0.3,random_state=20)

#             kmeans = KMeans(n_clusters=i,init = 'k-means++', random_state=20)
#             kmeans.fit(a)
            
#             kmeans2 = KMeans(n_clusters=i,init = 'k-means++', random_state=20)
#             dat['Clusters']=kmeans2.fit_predict(data)
#             data_summry=dat['Clusters'].value_counts().reset_index()

#             a['Clusters']=kmeans.predict(a)
#             train_summry=a['Clusters'].value_counts().reset_index()

#             b['Clusters']=kmeans.predict(b)
#             test_summry =b['Clusters'].value_counts().reset_index()

#             train_summry.rename(columns = {'index':'Clusters','Clusters':'Train_Count'}, inplace = True)
#             test_summry.rename(columns = {'index':'Clusters','Clusters':'Test_Count'}, inplace = True)
#             data_summry.rename(columns = {'index':'Clusters','Clusters':'Data_count'}, inplace = True)

#             train_summry = train_summry.sort_values('Clusters')
#             test_summry = test_summry.sort_values('Clusters')
#             data_summry = data_summry.sort_values('Clusters')

#             total_train=train_summry['Train_Count'].sum()
#             total_test=test_summry['Test_Count'].sum()
            
#             train_summry['Perc TrainCt'] = round((train_summry['Train_Count']/total_train)*100,1)
#             test_summry['Perc TestCt'] = round((test_summry['Test_Count']/total_test)*100,1)
            
#             summry = train_summry.merge(test_summry,on='Clusters',how='inner')
#             summry = summry.merge(data_summry,on='Clusters',how='inner')
            
#             summry['Diff_dis'] = abs(summry['Perc TrainCt']-summry['Perc TestCt'])
#             summry['Avg_diff']=summry['Diff_dis'].mean()
            
#             iteration = 'Kmeans-'+str(i)
#             summry['Iteration'] = iteration
#             summry = summry[['Iteration','Clusters','Train_Count','Test_Count','Data_count','Perc TrainCt','Perc TestCt','Avg_diff']]
#             summry_df = summry_df.append(summry)

#         return summry_df

# Returns Individual Cluster results & Clustered DataFrame and Full DataFrame 
    def single_kmeans(self,num_clusters):
 
        all_vars = self.clust_var + self.prof_var
        
        dat = self.data[self.clust_var]
        full_data = self.data[all_vars]
        data = sc_x.fit_transform(dat)

        kmeans = KMeans(n_clusters=num_clusters,init = 'k-means++', random_state=20)
        data_df = pd.DataFrame(data)
        data_df['iter_labels'] = kmeans.fit_predict(data)
        iter_labels = kmeans.fit_predict(data)
        dat['Clusters'] = kmeans.fit_predict(data)

        ch = round(metrics.calinski_harabasz_score(data, iter_labels),4)
        db = round(metrics.davies_bouldin_score(data, iter_labels),4)
        silhouette_avg = round(metrics.silhouette_score(data, iter_labels),4)
        
        single = dat[['Clusters']]
        full_data = full_data.merge(single, left_index=True, right_index=True)

        it = ['Kmeans',num_clusters,silhouette_avg,ch,db]

        # --- NEW: write interim CSVs ---
        scaler_params = pd.DataFrame(
            {'mean': sc_x.mean_, 'scale': sc_x.scale_},
            index=self.clust_var
        )
        centroids_scaled = pd.DataFrame(
            kmeans.cluster_centers_, columns=self.clust_var
        )
        centroids_scaled.index.name = 'cluster'

        return it,dat,full_data,data_df,scaler_params, centroids_scaled
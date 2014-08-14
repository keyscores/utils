import pandas as pd
import numpy as np
import argparse
from collections import OrderedDict as od


class city_stores:
    """
    Class that processes our data and puts stores it in standard form.
    """

    def __init__(self,filename,n_business_cols):

        df_cities = pd.read_excel(filename,sheetname="Cities")
        df_stores = pd.read_excel(filename,sheetname="Stores")

        #### Getting our data in standard form ####

        columns          = df_stores['Business Measure'].values[0:n_business_cols]
        n_entries        = len(df_stores.index.values)/n_business_cols

        main_dic = od()

        for i,column in enumerate(columns):
            main_dic[column]=np.empty(n_entries,dtype=type(df_stores.iloc[i,2]))

        stores = [] 

        for i in range(n_entries):
            #if i == 150:
            #import pdb;pdb.set_trace()
            if (df_stores['City'][i*n_business_cols] in stores):
                continue
            for j,column in enumerate(columns):
                main_dic[column][i]=df_stores.iloc[i*n_business_cols+j,2]
            stores.append(df_stores['City'][i*n_business_cols])

        # we ignored repeated entries
        n_real_entries = len(stores)

        for column in columns:
            main_dic[column] = main_dic[column][:n_real_entries]

        self.df_stores_std = pd.DataFrame(main_dic,index=stores)
        self.df_stores_std.sort_index(axis=0,inplace=True,ascending=True)
        #self.df_stores_std.to_excel("stores_test.xlsx")

        ## We repeat the process similarly for the cities ##

        #n_business_cols = 95
        columns          = np.unique(df_cities['City Statistic'].values)
        n_business_cols        = columns.size
        n_entries        = len(df_cities.index.values)/n_business_cols+100
        main_dic = od()

        # we assume to have the same number of cities as for the stores
        for i,column in enumerate(columns):
            main_dic[column]=np.empty(n_entries,dtype=type(df_cities.iloc[i,3]))
           
        city_data = od()
        n_rows    = df_cities.shape[0]
        i_city=0

        #reading the csv, looping through all rows
        for i in range(n_rows):    
            city=df_cities['City'][i]
            if city in city_data:
                city_data[city][df_cities.iloc[i,1]]=df_cities.iloc[i,3]
            else:
                city_data[city]={df_cities.iloc[i,1]:df_cities.iloc[i,3],'id':i_city}
                i_city+=1

        # data has been read, now we know what is missing or not
        # writing the final dataframe
        for city in city_data:
            i = city_data[city]['id']
            for column in columns:
                if column in city_data[city]:
                    main_dic[column][i]=city_data[city][column]
                else:
                    #column is missing
                    main_dic[column][i]=np.nan

        #we ignore repeated entries
        n_real_entries = len(city_data)

        for column in columns:
            main_dic[column] = main_dic[column][:n_real_entries]

        self.df_cities_std = pd.DataFrame(main_dic,index=list(city_data.keys()))
        self.df_cities_std.sort_index(axis=0,inplace=True,ascending=True)
        #self.df_cities_std.to_excel("cities_test.xlsx")

    def get_cities(self):
        return self.df_cities_std

    def get_stores(self):
        return self.df_stores_std

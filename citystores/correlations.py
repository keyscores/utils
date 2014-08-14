from city_stores import city_stores
import pandas as pd
import numpy as np
import argparse
from collections import OrderedDict as od

cli_parser = argparse.ArgumentParser(description='Correlations calculator')
cli_parser.add_argument('--input','-i', metavar='FILE', type=str, nargs=1,required=True,
                            help='Excel input spreadsheet')
cli_parser.add_argument('--n_vars', metavar='N', type=int, nargs='?',default=3,
                            help='number of client variables')
args = cli_parser.parse_args()

filename = args.input[0]
n_business_cols = args.n_vars


data = city_stores(filename,n_business_cols)

df_cities_std = data.get_cities()
df_stores_std = data.get_stores()

####

n_vars_cities = df_cities_std.shape[1]
n_vars_stores = df_stores_std.shape[1]

import numpy as np
import itertools

#here we create the df_corrs dataframe to contain the matrix of correlations between city and stores variables
corrs = np.zeros((n_vars_cities,n_vars_stores))
df_corrs = pd.DataFrame(corrs,index=df_cities_std.columns,columns=df_stores_std.columns)
for column_city,column_store in itertools.product(df_cities_std.columns,df_stores_std.columns):
    df_corrs[column_store].loc[column_city] = df_cities_std[column_city].corr(df_stores_std[column_store])

df_corrs.to_excel("corr.xlsx")

flat_corrs = []

for column in df_corrs.columns.values:
	corr_values = list(df_corrs[column].values)
	corr_cities = [column]*df_corrs.shape[0]
	corr_stores = df_corrs.index
	flat_corrs = flat_corrs + (zip(corr_values,corr_cities,corr_stores))

flat_corrs = sorted(flat_corrs,key=lambda x: abs(x[0]),reverse=True)

corr_values_t,corr_cities_t,corr_stores_t = zip(*flat_corrs)

corr_values = list(corr_values_t)
corr_labels = zip(list(corr_cities_t), list(corr_stores_t))
corr_labels = [label[0]+" vs. "+label[1] for label in corr_labels]

df_ordered_corrs = pd.DataFrame({'Correlations':corr_values},index=corr_labels)

df_ordered_corrs.to_excel("corr_ordered.xlsx")
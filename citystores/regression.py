from city_stores import city_stores
from sklearn import cross_validation
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.linear_model import Lasso

import argparse

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

df_cities_std2 = df_cities_std.dropna(axis=1)

missing_cols = set(df_cities_std.columns)-set(df_cities_std2.columns)

print "Warning:\tcolumns not considered in this analysis due to missing data:"
for col in missing_cols:
    print "\t\t",col

#normalizing the data
df_cities_normal = (df_cities_std2 - df_cities_std2.mean()) / (df_cities_std2.max() - df_cities_std2.min())

X = df_cities_normal.values
y = df_stores_std['Faturamento']

##

estimators = [Ridge(normalize=True),SVR(C=1.0, epsilon=0.2,max_iter=20000,kernel='rbf'),Lasso(alpha=0.1,max_iter=20000,normalize=True),SVR(C=1.0, epsilon=0.2,kernel='linear',max_iter=20000)]

for estimator in estimators:
    estimator.fit(X,y)
    score = estimator.score(X,y)
    score_cv = cross_validation.cross_val_score(estimator, X, y, cv=5)
    print estimator
    print "Regular score: ", score
    print "CV score: ", score_cv

from sklearn.feature_selection import RFE,RFECV

for estimator in estimators:
    for selector in [RFE(estimator, n_features_to_select=90)]:#,RFECV(estimator, step=1, cv=2)]:
        selector = selector.fit(X, y)
        print "RFE :"
        print selector
        print "\t With:"
        print "\t Score: ",selector.score(X,y)
        print "\t CV score: ",cross_validation.cross_val_score(estimator, X, y, cv=5)
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np

filename_apple="input/Apple-Complete.xlsx"
filename_cable="input/Cable.xlsx"
filename_lookup="input/Lookup.xlsx"
filename_balance="output/Balance.csv"
filename_accrual="output/Accrual.csv"

#### IMPORT WHAT WE NEED ####
df_sales = pd.read_excel(filename_apple)[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
df_cable = pd.read_excel(filename_cable)[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
df_sales = df_sales.append(df_cable)
df_encd  = pd.read_excel(filename_lookup,sheetname="Encoding")[['Vendor Identifier','Region',u'Comissão','Encoding U$','Media',u'Mês Início Fiscal','Tax Witholding','NOW Tax','Rights Holder']]
df_regions = pd.read_excel(filename_lookup,sheetname="Region")
df_currency = pd.read_excel(filename_lookup,sheetname="Currency")

'''
alternative recoup table
df_recoup  = pd.read_excel(filename_lookup,sheetname="Encoding")[['Vendor Identifier','Rights Holder','Encoding U$','Media',u'Mês Início Fiscal']]
df_recoup.set_index([u'Mês Início Fiscal','Vendor Identifier','Rights Holder'], inplace = True)
df_recoup['Recoupable'] = df_recoup['Encoding U$'] + df_recoup['Media'] 
'''


#### Clean unneeded data ####
df_sales = df_sales[df_sales['Royalty Price'] != 0]
df_sales = df_sales[df_sales['Download Date (PST)'] >= datetime.datetime(2013, 1, 1)]

# Make the dates uniform.
def first_day_of_month_converter(dt):
    return datetime.datetime(dt.year, dt.month, 1)

df_sales['month,year'] = df_sales['Download Date (PST)'].apply(first_day_of_month_converter)
df_encd[u'Mês Início Fiscal'] = df_encd[u'Mês Início Fiscal'].apply(first_day_of_month_converter)
df_currency['month,year']=pd.to_datetime(df_currency['Month'])

#### MERGES ####
# Merge region from country by merging with regions sheet
df_sales = pd.merge(df_sales,df_regions,on="Country Code")                

# Merge sales with encoding data, encoding, tax etc per sale
df_comb = pd.merge(df_sales,df_encd,on=['Vendor Identifier','Region'])

# Merge associated currency per sale, valid on the sale date
df_comb = pd.merge(df_comb,df_currency,on=['Customer Currency','month,year'])


#### ACCRUAL CALCULATIONS ######
df_comb['Net revenue']=df_comb['Royalty Price']*df_comb['Units']*df_comb['Exchange Rate']

# TAX The tax has a special rule. Where sales.provider=='Apple' the Value multuplied is 'Tax Witholding', if it is provider == 'Net Now' then it is encoding.Now_Tax
apple_provider = df_comb['Provider'] == 'APPLE'
net_now_provider = df_comb['Provider'] == 'NET NOW'
df_comb['Tax'] = (df_comb['Net revenue'] * df_comb['Tax Witholding']).where(apple_provider)
df_comb['Tax'] = (df_comb['Net revenue'] * df_comb['NOW Tax']).where(net_now_provider, other=df_comb['Tax'])

df_comb['Recoup']=df_comb['Encoding U$']+df_comb['Media']
df_comb['After tax']=df_comb['Net revenue']-df_comb['Tax']
df_comb['Fee value']=df_comb['After tax']*df_comb[u'Comissão']
df_comb['Royalty']=df_comb['After tax']-df_comb['Fee value']

columns_accrual = ['month,year','Region','Rights Holder','Vendor Identifier','Product Type Identifier','Asset/Content Flavor','Net revenue','Royalty', 'Units', 'Tax', 'After tax', 'Fee value', 'Media', 'Encoding U$', 'Recoup']
accrual_groupbycols = ['month,year','Vendor Identifier','Region','Rights Holder','Product Type Identifier','Asset/Content Flavor']

df_accrual_revenue   = df_comb[columns_accrual].groupby(accrual_groupbycols)['Net revenue'].sum()
df_accrual_royalty   = df_comb[columns_accrual].groupby(accrual_groupbycols)['Royalty'].sum()
df_accrual_units     = df_comb[columns_accrual].groupby(accrual_groupbycols)['Units'].sum()
df_accrual_tax       = df_comb[columns_accrual].groupby(accrual_groupbycols)['Tax'].sum()
df_accrual_after_tax = df_comb[columns_accrual].groupby(accrual_groupbycols)['After tax'].sum()
df_accrual_fee_value = df_comb[columns_accrual].groupby(accrual_groupbycols)['Fee value'].sum()
df_accrual_recoupable = df_comb[columns_accrual].groupby(accrual_groupbycols)['Recoup'].mean()


####  BALANCE CALCULATIONS ####
balance_groupby = ['month,year','Vendor Identifier','Rights Holder']

# Get Royalty and groupby only DATE,VENDOR ID,RIGHTS HOLDER
df_royalty = df_comb[columns_accrual].groupby(balance_groupby)['Royalty'].sum()

# CUMULATIVE ROYALTY Get the cumulative sum of Royalty
df_cumu_royalty = df_comb[columns_accrual].groupby(balance_groupby)['Royalty'].sum().groupby(level=[1,2]).cumsum()
df_cumu_royalty.name = "Royalty"

# CUMULATIVE RECOUPABLE Get the cumulative sum of Recoupable
df_cumu_recoupable = df_comb[columns_accrual].groupby(balance_groupby)['Recoup'].mean()

#BALANCE - Find the difference/balance of the cumulative royalty and cumulative recoupable
df_balance = df_cumu_royalty + df_cumu_recoupable
df_balance.name = "Balance"
#print df_balance

#POSITIVE BALANCE select only where Balances are Positive,
df_positive_balance = df_balance.mask(df_balance < 0)
# then replace the NaN for 0.
df_positive_balance = df_positive_balance.fillna(value=0)
df_positive_balance.name = "Positive Balance"

#CHANGE IN POSITIVE BALANCE - PAYMENT OWED#
#Find the difference between 2 months, considering vendorid and rightsholder. Means to groupby vendorid and rightsholder first. 

from dateutil.relativedelta import relativedelta
def diff_without_changing_first_month_value(series, groupby_level):
    zero_month = series.index.levels[0][0] - relativedelta(months=1)

    labels = []
    for label1, label2 in zip(series.index.labels[1], series.index.labels[2]):
        if (label1, label2) not in labels:
            labels.append((label1, label2))
    # reverse zip
    labels = zip(*labels)

    # no of values required for zero month
    values_count = len(labels[0])

    zero_month_index = pd.MultiIndex(
        levels = [[zero_month], series.index.levels[1], series.index.levels[2]],
        labels = [[0]*values_count, labels[0], labels[1]],
        names = series.index.names,
    )
    zero_month_series = pd.Series([0]*values_count, index=zero_month_index)
    series_with_zero_month = zero_month_series.append(series)

    diff = series_with_zero_month.groupby(level=groupby_level).diff()
    required_series = diff.ix[values_count:]
    return required_series

'''
Only working for small samples not working on Apple-Large.xlsx
'''
df_payment_owed = diff_without_changing_first_month_value(df_positive_balance, groupby_level=[1,2])
df_payment_owed.name = "Payment Owed"

'''
perhaps try with shifting back and forth...
'''
#print df_positive_balance.shift(periods=1, freq= 'M')
print df_payment_owed
#print df_positive_balance.groupby(level=[1,2]).diff()

#fill the NaN with 0
#df_payment_owed = df_payment_owed.fillna(value=0)
#print df_payment_owed

#### EXPORTING ACCRUAL REPORT ####
df_accrual = pd.DataFrame([df_accrual_revenue,df_accrual_units,df_accrual_tax,df_accrual_after_tax,df_accrual_fee_value,df_accrual_royalty,df_accrual_recoupable]).transpose()
df_accrual.to_csv(filename_accrual, encoding='utf-8')


#### EXPORTING BALANCE REPORT ####
df_balance_report = pd.DataFrame([df_cumu_royalty,df_cumu_recoupable,df_balance,df_positive_balance,df_payment_owed]).transpose()
df_balance_report.to_csv(filename_balance, encoding='utf-8')


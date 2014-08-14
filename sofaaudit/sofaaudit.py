#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np

filename_apple="input/Apple-Large.xlsx"
filename_cable="input/Cable.xlsx"
filename_lookup="input/Lookup.xlsx"
filename_balance="output/Balance.csv"
filename_accrual="output/Accrual.csv"

print 'Loading files....'
#### IMPORT ####
df_sales = pd.read_excel(filename_apple)[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
df_cable = pd.read_excel(filename_cable)[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
df_sales = df_sales.append(df_cable)
df_tax  = pd.read_excel(filename_lookup,sheetname="Encoding")[['Vendor Identifier','Region',u'Comissão','Tax Witholding','NOW Tax','Rights Holder']]
df_regions = pd.read_excel(filename_lookup,sheetname="Region")
df_currency = pd.read_excel(filename_lookup,sheetname="Currency")
df_recoup  = pd.read_excel(filename_lookup,sheetname="Encoding")[['Vendor Identifier','Rights Holder','Region','Encoding U$','Media',u'Mês Início Fiscal']]
df_recoup.rename(columns={u'Mês Início Fiscal':'month,year'}, inplace=True)
print 'Imported'

#### Clean  ####
# remove unneeded data
df_sales = df_sales[df_sales['Royalty Price'] != 0]
df_sales = df_sales[df_sales['Download Date (PST)'] >= datetime.datetime(2013, 1, 1)]
# Make the dates uniform format, First day of month.
def first_day_of_month_converter(dt):
    return datetime.datetime(dt.year, dt.month, 1)
df_sales['month,year'] = df_sales['Download Date (PST)'].apply(first_day_of_month_converter)
df_recoup['month,year'] = df_recoup['month,year'].apply(first_day_of_month_converter)
df_currency['month,year']=pd.to_datetime(df_currency['Month'])
print "Cleaned"

#### MERGE ####
# Merge region from country by merging with regions sheet
df_sales = pd.merge(df_sales,df_regions,on="Country Code")                
# Merge sales with encoding data, encoding, tax etc per sale
df_accrual = pd.merge(df_sales,df_tax,on=['Vendor Identifier','Region'])
# Merge associated currency per sale, valid on the sale date
df_accrual = pd.merge(df_accrual,df_currency,on=['Customer Currency','month,year'])
print "Merged"

#### ACCRUAL CALCULATIONS ######
df_accrual['Net revenue']=df_accrual['Royalty Price']*df_accrual['Units']*df_accrual['Exchange Rate']
# TAX The tax has a special rule. Where sales.provider=='Apple' the Value multuplied is 'Tax Witholding', if it is provider == 'Net Now' then it is encoding.Now_Tax
apple_provider = df_accrual['Provider'] == 'APPLE'
net_now_provider = df_accrual['Provider'] == 'NET NOW'
df_accrual['Tax'] = (df_accrual['Net revenue'] * df_accrual['Tax Witholding']).where(apple_provider)
df_accrual['Tax'] = (df_accrual['Net revenue'] * df_accrual['NOW Tax']).where(net_now_provider, other=df_accrual['Tax'])
df_accrual['After tax']=df_accrual['Net revenue']-df_accrual['Tax']
df_accrual['Fee value']=df_accrual['After tax']*df_accrual[u'Comissão']
df_accrual['Royalty']=df_accrual['After tax']-df_accrual['Fee value']
print "Accrual Calculated"

####  BALANCE CALCULATIONS ####
balance_groupby = ['month,year','Vendor Identifier','Rights Holder']
df_recoup['Recoupable'] = df_recoup['Encoding U$'] + df_recoup['Media'] 

# creating a new dataframe from the series. This could be simpler. Some cargo cult happening here.
s_accrual_royalty2 = df_accrual.groupby(balance_groupby)['Royalty'].sum()
s_recoupable = df_recoup.groupby(balance_groupby)['Recoupable'].sum()
df_recoupable= pd.concat([s_recoupable],axis=1)
df_balance = pd.concat([s_accrual_royalty2],axis=1).reset_index()
df_recoupable = df_recoupable.groupby(level=[1,2]).sum().reset_index()

#merging the tables along the columns that interest us. not sure why it needs unicode handling.
df_balance = df_balance.merge(df_recoupable, on = [u'Vendor Identifier', u'Rights Holder'])

# do the calcs
# it needs to be multiindex so that cumsum works properly
df_balance = df_balance.set_index(['month,year','Vendor Identifier','Rights Holder'])
df_balance['Cumu'] = df_balance['Royalty'].groupby(level=[1,2]).cumsum()
df_balance['Balance'] = df_balance['Recoupable'] + df_balance['Cumu']
df_balance['Positive'] = df_balance['Balance'].mask(df_balance['Balance']<0).fillna(0)
x = df_balance['Positive'].groupby(level=[1,2]).diff()
df_balance['Payment Owed'] = x.fillna(df_balance['Positive'])
print "Balance Calculated"

#### EXPORTING ACCRUAL REPORT ####
accrual_groupby = ['month,year','Vendor Identifier','Region','Rights Holder','Product Type Identifier','Asset/Content Flavor']
df_accrual.drop(['Download Date (PST)', 'Royalty Price','Tax Witholding', 'Provider', 'Customer Currency', 'Country Code', u'Comissão', 'NOW Tax', 'Exchange Rate', 'Month'],inplace=True,axis=1)
df_accrual = df_accrual.groupby(accrual_groupby).sum()
#df_accrual = df_accrual.set_index(accrual_groupby)
df_accrual.to_csv(filename_accrual, encoding='utf-8')

#### EXPORTING BALANCE REPORT ####
df_balance.to_csv(filename_balance, encoding='utf-8')
print "Done, files exported"


#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np

#filename="Sofa7Krecords-2.xlsx"
filename_in="input.xlsx"
filename_balance="Balance.csv"
filename_accrual="Accrual.csv"

df_sales = pd.read_excel(filename_in,sheetname="Sales")[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor']]
df_sales = df_sales[df_sales['Royalty Price'] != 0]
df_sales = df_sales[df_sales['Download Date (PST)'] >= datetime.datetime(2013, 1, 1)]

df_encd  = pd.read_excel(filename_in,sheetname="Encoding")[['Vendor Identifier','Region',u'Comissão','Encoding U$','Media',u'Mês Início Fiscal','Tax Witholding','Rights Holder']]
df_regions = pd.read_excel(filename_in,sheetname="Region")
df_currency = pd.read_excel(filename_in,sheetname="Currency")

# getting month,year tuples
df_sales['date']=pd.to_datetime(df_sales['Download Date (PST)'])
df_sales['month,year']=df_sales['date'].apply(lambda x: (x.year,x.month))
del df_sales['Download Date (PST)']

df_currency['month,year']=pd.to_datetime(df_currency['Month'])
df_currency['month,year']=df_currency['month,year'].apply(lambda x: (x.year,x.month))
del df_currency['Month']

# domains
# titles domain
titles = list(set(df_sales['Vendor Identifier'].values))
n_titles = len(titles)

# countries domain
countries = list(set(df_sales['Country Code'].values))
n_regions = len(countries)

# currencies domain
currencies = list(set(df_currency['Customer Currency'].values))
n_currencies = len(currencies)

# dates domain
min_date = df_sales['date'].min(axis=1)
max_date = df_sales['date'].max(axis=1)

min_date_p = (min_date.year,min_date.month)
max_date_p = (max_date.year,max_date.month)

# adding all possible in between dates

dates = [min_date_p]
while(1):
    if dates[-1]==max_date_p:
        break
    else:
        if dates[-1][1] is 12:
            dates.append((dates[-1][0]+1,1))
        else:
            dates.append((dates[-1][0],dates[-1][1]+1))

# getting region from country by merging with regions sheet
df_sales = pd.merge(df_sales,df_regions,on="Country Code")                
                
del df_sales['Country Code']
del df_sales['date']
del df_regions

# used regions domain
regions = list(set(df_sales['Region'].values))
n_regions = len(regions)

# filing empty dates 
for date in dates:
    for title in titles:    
        for region in regions:
            new_row = {'Vendor Identifier':title,'Units':0,'Royalty Price':0,'Customer Currency':'USD','month,year':date,'Region':region,'Product Type Identifier':'','Asset/Content Flavor': ''}
            df_sales = df_sales.append([new_row])
            #df_sales.append({'Vendor Identifier':title,'month,year':date,'Region':region,'Units':0,'Customer Currency':'USD','Royalty Price':0},ignore_index=True)


df_encd[u'Mês Início Fiscal'] = pd.to_datetime(df_encd[u'Mês Início Fiscal'])

# checking if we have all the encodings we need
for title in titles:    
    for region in regions:
        if df_encd[(df_encd['Vendor Identifier']==title) & (df_encd['Region']==region)].empty:
            print "Warning:\n\t We are missing the encoding value for vendor_id: ",title,"in region: ",region,"Rights Holder: ",rightsholder
            new_encoding={'Vendor Identifier':title,'Region':region,u'Comissão':0.0,'Encoding U$':0.0,'Media':0.0,u'Mês Início Fiscal':min_date,'Tax Witholding':0.0,'Rights Holder':''}
            df_encd = df_encd.append([new_encoding])

# getting associated encoding, tax etc per sale

df_comb = pd.merge(df_sales,df_encd,on=['Vendor Identifier','Region'])

del df_sales
del df_encd

# getting associated currency per sale, valid on the sale date
df_comb = pd.merge(df_comb,df_currency,on=['Customer Currency','month,year'])
del df_currency

def fiscal_year(row,column):
    '''
    Returning encoding depending if fiscal year started or not (0 if not)
    '''
    month_fiscal=row[u'Mês Início Fiscal'].month
    year_fiscal=row[u'Mês Início Fiscal'].year
    month_cur=row['month,year'][1]
    year_cur=row['month,year'][0]
    b_early=False
    
    if year_cur<year_fiscal:
        b_early=True
    elif year_cur==year_fiscal and month_cur<month_fiscal:
        b_early=True
    if b_early:
        return 0.0
    else:
        return row[column]

df_comb['Recoupable']=df_comb['Encoding U$']+df_comb['Media']

# setting Recoupable to 0 before the start of the fiscal year (by month)
df_comb['Recoupable'] = df_comb.apply(lambda x: fiscal_year(x,'Recoupable'),axis=1)
del df_comb[u'Mês Início Fiscal']
#del df_comb['Media']
#del df_comb['Encoding U$']

# output calculations
df_comb['Net revenue']=df_comb['Royalty Price']*df_comb['Units']*df_comb['Exchange Rate']
df_comb['Tax']=df_comb['Net revenue']*df_comb['Tax Witholding']
df_comb['After tax']=df_comb['Net revenue']-df_comb['Tax']
df_comb['Fee value']=df_comb['After tax']*df_comb[u'Comissão']
df_comb['Royalty']=df_comb['After tax']-df_comb['Fee value']

columns_accrual = ['month,year','Region','Rights Holder','Vendor Identifier','Product Type Identifier','Asset/Content Flavor','Net revenue','Royalty', 'Units', 'Tax', 'After tax', 'Fee value', 'Media', 'Encoding U$']
accrual_groupbycols = ['month,year','Vendor Identifier','Region','Rights Holder','Product Type Identifier','Asset/Content Flavor']

df_accrual_revenue   = df_comb[columns_accrual].groupby(accrual_groupbycols)['Net revenue'].sum()
df_accrual_royalty   = df_comb[columns_accrual].groupby(accrual_groupbycols)['Royalty'].sum()
df_accrual_units     = df_comb[columns_accrual].groupby(accrual_groupbycols)['Units'].sum()
df_accrual_tax       = df_comb[columns_accrual].groupby(accrual_groupbycols)['Tax'].sum()
df_accrual_after_tax = df_comb[columns_accrual].groupby(accrual_groupbycols)['After tax'].sum()
df_accrual_fee_value = df_comb[columns_accrual].groupby(accrual_groupbycols)['Fee value'].sum()
df_accrual_media     = df_comb[columns_accrual].groupby(accrual_groupbycols)['Media'].sum()
df_accrual_encoding  = df_comb[columns_accrual].groupby(accrual_groupbycols)['Encoding U$'].sum()
df_accrual = pd.DataFrame([df_accrual_revenue,df_accrual_royalty,df_accrual_units,df_accrual_tax,df_accrual_after_tax,df_accrual_fee_value,df_accrual_media,df_accrual_encoding]).transpose()
df_accrual.to_csv(filename_accrual, encoding='utf-8')
             

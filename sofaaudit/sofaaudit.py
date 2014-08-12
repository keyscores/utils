#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np

#filename="Sofa7Krecords-2.xlsx"
filename_in="input.xlsx"
filename_cable="Cable.xlsx"
filename_balance="Balance.csv"
filename_accrual="Accrual.csv"

df_sales = pd.read_excel(filename_in,sheetname="Sales")[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]

# NELSON: This line was added to append Cable.xslx another table similar to "input.Sales" 
df_cable = pd.read_excel(filename_cable)[['Vendor Identifier','Units','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
# append cable.xlsx
df_sales = df_sales.append(df_cable)

df_sales = df_sales[df_sales['Royalty Price'] != 0]
df_sales = df_sales[df_sales['Download Date (PST)'] >= datetime.datetime(2013, 1, 1)]

# NELSON: "input.Encoding.Now Tax" is another column being read. It's neceesary for accurate calculation of TAX further down.
df_encd  = pd.read_excel(filename_in,sheetname="Encoding")[['Vendor Identifier','Region',u'Comissão','Encoding U$','Media',u'Mês Início Fiscal','Tax Witholding','NOW Tax','Rights Holder']]
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

# NELSON: These warnings don't always make sense. It is possible that a title is sold in only 1 region. But this check tried to make it match all 4 regions.
# checking if we have all the encodings we need
for title in titles:    
    for region in regions:
        if df_encd[(df_encd['Vendor Identifier']==title) & (df_encd['Region']==region)].empty:
            print "Warning:\n\t We are missing the encoding value for vendor_id: ",title,"in region: ",region,"Rights Holder: "
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
#df_comb['Tax']=df_comb['Net revenue']*df_comb['Tax Witholding']

apple_provider = df_comb['Provider'] == 'APPLE'
net_now_provider = df_comb['Provider'] == 'NET NOW'

# NELSON: The tax has a special rule. Where sales.provider=='Apple' the Value multuplied is 'Tax Witholding', if it is provider == 'Net Now' then it is encoding.Now_Tax
df_comb['Tax']=df_comb['Net revenue']*df_comb['Tax Witholding']

df_comb['After tax']=df_comb['Net revenue']-df_comb['Tax']
df_comb['Fee value']=df_comb['After tax']*df_comb[u'Comissão']
df_comb['Royalty']=df_comb['After tax']-df_comb['Fee value']

columns_accrual = ['month,year','Region','Rights Holder','Vendor Identifier','Product Type Identifier','Asset/Content Flavor','Net revenue','Royalty', 'Units', 'Tax', 'After tax', 'Fee value', 'Media', 'Encoding U$']
accrual_groupbycols = ['month,year','Vendor Identifier','Region','Rights Holder','Product Type Identifier','Asset/Content Flavor']

df_accrual_revenue   = df_comb[columns_accrual].groupby(accrual_groupbycols)['Net revenue'].sum()
df_accrual_royalty   = df_comb[columns_accrual].groupby(accrual_groupbycols)['Royalty'].sum()
df_accrual_units     = df_comb[columns_accrual].groupby(accrual_groupbycols)['Units'].sum()


'''
### TODO : Create correct Tax logic #####
apple_provider = df_comb['Provider'] == 'APPLE'
net_now_provider = df_comb['Provider'] == 'NET NOW'
df_comb['Tax'] = df_comb['Net revenue'][apple_provider] * df_comb['Tax Witholding'][apple_provider]
df_comb['Tax2'] = df_comb['Net revenue'][net_now_provider] * df_comb['NOW Tax'][net_now_provider]

'''


df_accrual_tax       = df_comb[columns_accrual].groupby(accrual_groupbycols)['Tax'].sum()
df_accrual_after_tax = df_comb[columns_accrual].groupby(accrual_groupbycols)['After tax'].sum()
df_accrual_fee_value = df_comb[columns_accrual].groupby(accrual_groupbycols)['Fee value'].sum()
df_accrual_media     = df_comb[columns_accrual].groupby(accrual_groupbycols)['Media'].sum()
df_accrual_encoding  = df_comb[columns_accrual].groupby(accrual_groupbycols)['Encoding U$'].sum()

'''
# TODO Create Recoupable
df_comb['recoupable'] = df_accrual_encoding['Encoding U$'] + df_accrual_encoding['Media']
print df_comb['recoupable']
'''


'''
#### IGNORE EXPORTING ACCRUAL REPORT ####
#df_accrual = pd.DataFrame([df_accrual_royalty,df_accrual_recoupable]).transpose()
#df_accrual.to_csv(filename_accrual, encoding='utf-8')
'''

####  BALANCE CALCULATIONS ####
balance_groupby = ['month,year','Vendor Identifier','Rights Holder']

# Get Royalty and groupby only DATE,VENDOR ID,RIGHTS HOLDER
df_royalty = df_comb[columns_accrual].groupby(balance_groupby)['Royalty'].sum()
#print df_royalty

# ROYALTY BALANCE Get the cumulative sum of Royalty
df_cumu_royalty = df_comb[columns_accrual].groupby(balance_groupby)['Royalty'].sum().groupby(level=[0,1,2]).cumsum()
#print df_cumu_royalty

# RECOUPABLE BALANCE Get the cumulative sum of Recoupable
'''
TODO: Should be Recoupable. Using Encoding as a placeholder.
'''
df_cumu_recoupable = df_comb[columns_accrual].groupby(balance_groupby)['Encoding U$'].sum().groupby(level=[0,1,2]).cumsum()
#print df_cumu_recoupable

# BALANCE#
#Find the difference/balance of the cumulative royalty and cumulative recoupable
df_balance = df_cumu_royalty + df_cumu_recoupable
#print df_balance

# POSITIVE BALANCE#
# select only where Balances are Positive,
df_positive_balance = df_balance.mask(df_balance < 0)
# then replace the NaN for 0.
df_positive_balance = df_positive_balance.fillna(value=0)
#print df_positive_balance


#PAYMENT OWED#
#Find the difference between 2 months, considering vendorid and rightsholder. Means to groupby vendorid and rightsholder first. 
df_payment_owed = df_positive_balance.groupby(level=[1,2]).diff()
#fill the NaN with 0
df_payment_owed = df_payment_owed.fillna(value=0)
#print df_payment_owed


#### PREPARE BALANCE REPORT ####
df_balance_report = pd.DataFrame([df_payment_owed,df_positive_balance]).transpose()
print df_balance_report
df_balance_report.to_csv(filename_balance, encoding='utf-8')


'''
del df_accrual


#debug file
#df_comb.to_csv('debug.csv', encoding='utf-8')
df_comb = df_comb.drop(['Royalty Price','Product Type Identifier','Units','Exchange Rate','Fee value','After tax','Tax','Net revenue',u'Comissão','Tax Witholding','Customer Currency'],axis=1)

# Rights Holder domain
rightsholders = list(set(df_comb['Rights Holder'].values))


#print df_comb.columns
# checking if we have all the rights holders we need
for date in dates:
    for title in titles:    
        for region in regions:
            for rightsholder in rightsholders:
                if df_comb[(df_comb['month,year']==date) & (df_comb['Vendor Identifier']==title) & (df_comb['Region']==region) & (df_comb['Rights Holder']==rightsholder)].empty:
                    new_encoding={'Vendor Identifier':title,'month,year':date,'Region':region,'Rights Holder':rightsholder,'Recoupable':0,'Royalty':0}
                    df_comb = df_comb.append([new_encoding])
#df_comb.to_csv('debug1.csv', encoding='utf-8')                   

# summing up different sales by month, vendor and region
df_groupby=df_comb.groupby(['month,year','Vendor Identifier','Region','Rights Holder'])
del df_comb

df_cmbg = df_groupby['Royalty'].sum()
# assuming constant encodings
df_enc  = df_groupby['Recoupable'].first()

df_grouped = pd.DataFrame([df_cmbg,df_enc]).transpose()
del df_cmbg
del df_enc

df_grouped['Royalty Balance']=df_grouped['Royalty']

# rolling sum Royalty Balance
for title in titles:
    for region in regions:
        for rightsholder in rightsholders:        
            for i in range(1, len(dates)):
                date = dates[i]
                previous_row = df_grouped.loc[dates[i-1]].loc[title].loc[region].loc[rightsholder]
                #for debugging:
                #print "date:",date,"region: ",region,"title: ",title,"rightsholder: ",rightsholder
                this_row = df_grouped.loc[date].loc[title].loc[region].loc[rightsholder]
                
                df_grouped.loc[date].loc[title].loc[region].loc[rightsholder, 'Royalty Balance'] = \
                    df_grouped.loc[dates[i-1]].loc[title].loc[region].loc[rightsholder,'Royalty Balance'] + df_grouped.loc[date].loc[title].loc[region].loc[rightsholder,'Royalty']

# encoding balance
df_grouped['Recoupable Balance']=df_grouped['Recoupable']+df_grouped['Royalty Balance']
del df_grouped['Recoupable']

# Payment Owed
df_grouped['Payment Owed']=0.0

for title in titles:
    for region in regions:
        for rightsholder in rightsholders:
            prev_nonzero_balance=0
            for i in range(len(dates)):
                date = dates[i]
                this_row = df_grouped.loc[date].loc[title].loc[region].loc[rightsholder]
                this_balance=this_row['Recoupable Balance']
                
                if i>0:
                    previous_row = df_grouped.loc[dates[i-1]].loc[title].loc[region].loc[rightsholder] 
                    previous_balance=previous_row['Recoupable Balance']            
                    diff_balance=this_balance-prev_nonzero_balance
                else:
                    diff_balance=this_balance
                
                b_payment = ((this_balance>0) and (i==0 or (diff_balance>0)))

                if b_payment:
                    df_grouped.loc[date].loc[title].loc[region].loc[rightsholder, 'Payment Owed'] = diff_balance
                    prev_nonzero_balance=this_balance

del df_grouped['Royalty']

df_grouped.to_csv(filename_balance, encoding='utf-8')                
'''
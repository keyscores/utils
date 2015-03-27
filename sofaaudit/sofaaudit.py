#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np

filename_apple="input/Nossa_Vendas_FORECAST_COMPLETE.xlsx"
filename_cable="input/Cable-Complete.xlsx"
filename_google="input/Import_transactional_Google.xlsx"
filename_lookup="input/DeParaSofaDigital.xlsx"
filename_balance="output/Balance.xlsx"
filename_accrual="output/Accrual.xlsx"
filename_recoupable="output/Recoupable.xlsx"
filename_nometadata="Output/nometadata.xlsx"
filename_nosales="Output/nosales.xlsx"

print 'Loading files....'
#### IMPORT ####
df_titles  = pd.read_excel(filename_lookup,sheetname="Titles")[['Vendor Identifier','Region','Titles',u'Comissão','Tax Witholding','NOW Tax','Rights Holder','Regime']]
df_regions = pd.read_excel(filename_lookup,sheetname="Regions")
df_currency = pd.read_excel(filename_lookup,sheetname="Currency")
df_recoup  = pd.read_excel("input/DeParaSofaDigital.xlsx",sheetname="Recoupable")[['Date','Vendor Identifier','Titles','Rights Holder','Region','Encoding U$','Media U$']]
df_recoup.rename(columns={u'Date':'month,year'}, inplace=True)
df_tax = pd.read_excel(filename_lookup,sheetname="Regime")
print "...lookup tables loaded"
df_sales = pd.read_excel(filename_apple)[['Vendor Identifier','Units','Customer Price','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
print "...Apple Loaded"
df_cable = pd.read_excel(filename_cable)[['Vendor Identifier','Units','CUSTOMER PRICE','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
df_cable.rename(columns={'CUSTOMER PRICE':'Customer Price'}, inplace=True)
print "...Cable Loaded"
#add google
df_google = pd.read_excel(filename_google)[['Vendor UPC','Resolution','Retail Price (USD)','Purchase Location', 'Transaction Type', 'Transaction Date', 'Country','Final Partner Earnings (USD)']]
print "...Google Loaded"
df_google = df_google.rename(columns={'Vendor UPC': 'Vendor Identifier','Retail Price (USD)':'Customer Price','Resolution': 'Asset/Content Flavor','Transaction Type': 'Product Type Identifier','Country': 'Country Code','Purchase Location':'Provider','Final Partner Earnings (USD)':'Royalty Price','Transaction Date':'Download Date (PST)'})
# google has no column units, must assume each row equals 1
df_google['Units']="1"
df_google['Units'] = df_google['Units'].astype('float64')
#doesn't have a currency column needs to add it.
df_google['Customer Currency']="USD"
df_google['Product Type Identifier']=df_google['Product Type Identifier'].map({'VOD':'D','EST':'M'})
print 'Loaded'

#add cable and google to the sales dataframe
df_sales = df_sales.append(df_cable)
df_sales = df_sales.append(df_google)

print 'Appended'

#### Clean  ####
# remove unneeded data
df_sales = df_sales[df_sales['Royalty Price'] != 0]
df_sales = df_sales[df_sales['Download Date (PST)'] >= datetime.datetime(2013, 1, 1)]
# Make the dates uniform format, First day of month.
def first_day_of_month_converter(dt):
    return datetime.datetime(dt.year, dt.month, 1)
df_sales['month,year'] = df_sales['Download Date (PST)'].apply(first_day_of_month_converter)
df_recoup['month,year'] = df_recoup['month,year'].apply(first_day_of_month_converter)
#if there are excel formulas in the columns that need to be ignored
#df_recoup['Media']=df_recoup['Media'].convert_objects(convert_numeric=True)
#df_recoup['Encoding U$']=df_recoup['Encoding U$'].convert_objects(convert_numeric=True)


'''#uncomment to enable 
df_google['month,year'] = df_google['Download Date (PST)'].apply(first_day_of_month_converter)
'''

df_currency['month,year']=pd.to_datetime(df_currency['Month'])



print "Cleaned"


### AUDIT ###
#THAT ALL THE VENDOR IDs in sales are in the DePara File
df_sales.to_excel("Output/AuditSales.xlsx")

checksales = df_sales['Vendor Identifier']
checklookup = df_titles['Vendor Identifier']
#produce a list of what titles had transactions but no metadata in lookup
nometadata = checksales[~checksales.isin(checklookup)]
#nometadata=nometadata.drop_duplicates
nometadata.to_frame(name='column_name').to_excel(filename_nometadata)


#produce a list of what titles never had transactions
nosales = checklookup[~checklookup.isin(checksales)]
nosales.to_frame(name='column_name').to_excel(filename_nosales)

print "Audit"

'''Uncomment when date ranges are effective
### FIND DATE RANGES #### Every film belongs to a rights holder only on between start date and end date
df_ranges = pd.read_excel(filename_lookup,sheetname="Titles")[['Vendor Identifier','Region','Rights Holder','Start Date','End Date']]

#pivot the values into position using melt
df_ranges = pd.melt(df_ranges, id_vars=['Vendor Identifier', 'Region','Rights Holder'], value_name='Month')

#needs to be a datetime index to be able to resample below
df_ranges = df_ranges.set_index('Month')

#a function to resample an index
f = lambda df_ranges: df_ranges.resample(rule='MS', how='first')
# apply the resample rule to each groupby level
df_ranges = df_ranges.groupby(['Vendor Identifier','Region','Rights Holder']).apply(f)

# format the output, and drop unnecessary columns
df_ranges = df_ranges.drop(['Vendor Identifier','Region','Rights Holder','variable'], axis=1)
df_ranges = df_ranges.reset_index()
#print df_ranges

df_ranges.to_excel('test.xlsx')

print "Date Range Matched"
'''

#### MERGE ####
print "Merging..."
# From df_sales, create a year column so we can easily Tax regime merge on that.
df_sales['Year'] = pd.DatetimeIndex(df_sales['month,year']).year

# Merge to get tax rate, per year, per contract (vendor id, righstholder, region) in one table
df_titles = pd.merge(df_titles,df_tax,on="Regime")
print "...Regime done"
# Merge region from country by merging with regions sheet
df_sales = pd.merge(df_sales,df_regions,on="Country Code")     
print "...Country Code done"
# Merge sales with encoding data, encoding, tax etc per sale
df_accrual = pd.merge(df_sales,df_titles,on=['Vendor Identifier','Region', 'Year'])
print "...Vendor ID, Region, Year"

# Merge associated currency per sale, valid on the sale date
df_accrual = pd.merge(df_accrual,df_currency,on=['Customer Currency','month,year'])
print "...Customer Currency"

df_accrual.to_excel("accrual.xlsx")


print "Merged"

#### ACCRUAL CALCULATIONS ######
df_accrual['Customer Gross']=df_accrual['Customer Price']*df_accrual['Units']*df_accrual['Exchange Rate']
df_accrual['Net revenue']=df_accrual['Royalty Price']*df_accrual['Units']*df_accrual['Exchange Rate']

# TAX The tax has a special rule. Where sales.provider=='Apple' the Value multuplied is 'Tax Witholding', if it is provider == 'Net Now' then it is encoding.Now_Tax
#should be: "if matches apple or google" <> 'Net Now' is cheating
#apple_provider = df_accrual['Provider'] <> 'NET NOW'
#net_now_provider = df_accrual['Provider'] == 'NET NOW'
#df_accrual['Tax'] = (df_accrual['Net revenue'] * df_accrual['Tax Witholding']).where(apple_provider)
#df_accrual['Tax'] = (df_accrual['Net revenue'] * df_accrual['NOW Tax']).where(net_now_provider, other=df_accrual['Tax'])

# Select which rate applies; "offshore" or "brasil" according to the vendors
brasil_case = df_accrual['Provider'].isin(['NET NOW', 'GVT'])
offshore_case = df_accrual['Provider'].isin(['APPLE','Google Play', 'YouTube'])

#df_sales['rate'] = df_sales['Brasil'].where(brasil_case)
# note: other= will fill in nan's with whatever array you place there
#df_sales['rate'] = df_sales['Offshore'].where(offshore_case, other=df_sales['rate'])


df_accrual['Tax'] = (df_accrual['Net revenue'] * df_accrual['Brasil']).where(brasil_case)
# note: other= will fill in nan's with whatever array you place there
df_accrual['Tax'] = (df_accrual['Net revenue'] * df_accrual['Offshore']).where(offshore_case, other=df_accrual['Tax'])


df_accrual['After tax']=df_accrual['Net revenue']-df_accrual['Tax']
df_accrual['Fee value']=df_accrual['After tax']*df_accrual[u'Comissão']
df_accrual['Royalty']=df_accrual['After tax']-df_accrual['Fee value']
print "Accrual Calculated"

####  BALANCE CALCULATIONS ####
#alternate recoupable
df_recoup['Recoupable'] = df_recoup['Encoding U$'] + df_recoup['Media U$']

balance_groupby = ['month,year','Titles','Rights Holder']
# creating a new dataframe from the series. This could be simpler. Some cargo cult happening here.
s_accrual_royalty2 = df_accrual.groupby(balance_groupby)['Royalty'].sum()
s_recoupable = df_recoup.groupby(balance_groupby)['Recoupable'].sum()
df_recoupable= pd.concat([s_recoupable],axis=1)
df_balance = pd.concat([s_accrual_royalty2],axis=1).reset_index()
df_recoupable = df_recoupable.groupby(level=[1,2]).sum().reset_index()

#merging the tables along the columns that interest us. not sure why it needs unicode handling.
df_balance = df_balance.merge(df_recoupable, on = [u'Titles', u'Rights Holder'])

# do the calcs
# it needs to be multiindex so that cumsum works properly
df_balance = df_balance.set_index(['month,year','Titles','Rights Holder'])
df_balance['Cumu'] = df_balance['Royalty'].groupby(level=[1,2]).cumsum()
df_balance['Balance'] = df_balance['Recoupable'] + df_balance['Cumu']
df_balance['Positive'] = df_balance['Balance'].mask(df_balance['Balance']<0).fillna(0)
x = df_balance['Positive'].groupby(level=[1,2]).diff()
df_balance['Payment Owed'] = x.fillna(df_balance['Positive'])
print "Balance Calculated"

#### EXPORTING ACCRUAL REPORT ####
accrual_groupby = ['month,year','Provider','Country Code', 'Titles','Region','Rights Holder','Product Type Identifier','Asset/Content Flavor']
df_accrual.drop(['Download Date (PST)', 'Royalty Price','Tax Witholding','Customer Currency','Customer Price', u'Comissão', 'NOW Tax', 'Exchange Rate', 'Month','Vendor Identifier','Brasil', 'Offshore', 'Year'],inplace=True,axis=1)
df_accrual = df_accrual.groupby(accrual_groupby).sum()
#df_accrual = df_accrual.set_index(accrual_groupby)
df_accrual.to_excel(filename_accrual, encoding='utf-8',merge_cells=False)

#### EXPORTING BALANCE REPORT ####
df_balance.to_excel(filename_balance, encoding='utf-8',merge_cells=False)


#### EXPORTING RECOUPABLE REPORT ####
df_recoup = df_recoup[df_recoup['Recoupable'] != 0]
df_recoup = df_recoup.groupby(['month,year','Titles','Rights Holder']).sum()
df_recoup.to_excel(filename_recoupable, encoding='utf-8',merge_cells=False)
print "Done, files exported"

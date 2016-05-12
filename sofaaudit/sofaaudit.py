#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np

usePickle = False
# filename_apple="input/historic_report_itunes.xlsx"
# filename_apple2="input/Report_Itunes_2016.xlsx"
# filename_cable="input/Cable-Complete.xlsx"
# filename_google="input/Import_transactional_Google.xlsx"

#test data
filename_apple="input/apple.xlsx"
filename_apple2="input/apple.xlsx"
filename_cable="input/cable.xlsx"
filename_google="input/google.xlsx"

filename_lookup="input/DeParaSofaDigital.xlsx"

filename_balance="output/Balance.xlsx"
filename_accrual="output/Accrual.xlsx"
filename_recoupable="output/Recoupable.xlsx"
filename_nometadata="output/nometadata.xlsx"
filename_nosales="output/nosales.xlsx"


print 'Loading files....'
#### IMPORT ####
df_titles  = pd.read_excel(filename_lookup,sheetname="Titles")[['Vendor Identifier','Region','Titles',u'Comissão','Tax Witholding','NOW Tax','Rights Holder','Regime']]
df_regions = pd.read_excel(filename_lookup,sheetname="Regions")
df_currency = pd.read_excel(filename_lookup,sheetname="Currency")
df_recoup  = pd.read_excel("input/DeParaSofaDigital.xlsx",sheetname="Recoupable")[['Date','Vendor Identifier','Titles','Rights Holder','Region','Encoding U$','Media U$']]
df_recoup.rename(columns={u'Date':'month,year'}, inplace=True)
df_tax = pd.read_excel(filename_lookup,sheetname="Regime")
print "...lookup tables loaded"

if usePickle:
	df_cable = pd.read_pickle("cable.pkl")

else:
	df_cable = pd.read_excel(filename_cable)[['Vendor Identifier','Units','CUSTOMER PRICE','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
	df_cable.rename(columns={'CUSTOMER PRICE':'Customer Price'}, inplace=True)
	df_cable.to_pickle("cable.pkl")

print "...Cable Loaded"

#add google
if usePickle:
	df_google = pd.read_pickle("google.pkl")
else:
	df_google = pd.read_excel(filename_google)[['Vendor UPC','Resolution','Retail Price (USD)','Purchase Location', 'Transaction Type', 'Transaction Date', 'Country','Final Partner Earnings (USD)']]
	df_google.to_pickle("google.pkl")

print "...Google Loaded"

if usePickle:
	df_sales= pd.read_pickle("sales.pkl")
	df_apple2=pd.read_pickle("apple2.pkl")
else:
	df_sales = pd.read_excel(filename_apple)[['Vendor Identifier','Units','Customer Price','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
	df_apple2 = pd.read_excel(filename_apple2)[['Vendor Identifier','Units','Customer Price','Royalty Price','Download Date (PST)','Customer Currency','Country Code','Product Type Identifier', 'Asset/Content Flavor', 'Provider']]
	df_sales.to_pickle("sales.pkl")
	df_apple2.to_pickle("apple2.pkl")


# df_sales = pd.concat([df_sales,df_apple2])

print "...Apple Loaded"

df_google = df_google.rename(columns={'Vendor UPC': 'Vendor Identifier','Retail Price (USD)':'Customer Price','Resolution': 'Asset/Content Flavor','Transaction Type': 'Product Type Identifier','Country': 'Country Code','Purchase Location':'Provider','Final Partner Earnings (USD)':'Royalty Price','Transaction Date':'Download Date (PST)'})
# google has no column units, must assume each row equals 1
df_google['Units']="1"
df_google['Units'] = df_google['Units'].astype('float64')
#doesn't have a currency column needs to add it.
df_google['Customer Currency']="USD"
df_google['Product Type Identifier']=df_google['Product Type Identifier'].map({'VOD':'D','EST':'M'})
print 'Loaded'

#add cable and google to the sales dataframe
df_sales = df_sales.append([df_google,df_cable,df_apple2], ignore_index=True)
# df_sales = df_sales.append(df_cable, ignore_index=True)

# df_sales.to_excel("Output/AuditSales.xlsx")
print df_sales['Provider'].unique()

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

#
# ### AUDIT ###
# #THAT ALL THE VENDOR IDs in sales are in the DePara File
# df_sales.to_excel("Output/AuditSales.xlsx")

print "AuditSales to excel"


checksales = df_sales['Vendor Identifier']
checklookup = df_titles['Vendor Identifier']
 #produce a list of what titles had transactions but no metadata in lookup
nometadata = checksales[~checksales.isin(checklookup)]
 #nometadata=nometadata.drop_duplicates
nometadata.to_frame(name='column_name').to_excel(filename_nometadata)
#
#
# #produce a list of what titles never had transactions
nosales = checklookup[~checklookup.isin(checksales)]
nosales.to_frame(name='column_name').to_excel(filename_nosales)

print "Audit"

###Uncomment when date ranges are effective
### FIND DATE RANGES #### Every film belongs to a rights holder only on between start date and end date
df_ranges = pd.read_excel(filename_lookup,sheetname="Titles")[['Titles', u'Comissão', 'Regime', 'Vendor Identifier','Region','Rights Holder',u'Mês Início Fiscal','End Date']]

#pivot the values into position using melt
df_ranges = pd.melt(df_ranges, id_vars=['Vendor Identifier', 'Region','Rights Holder', 'Titles', 'Regime', u'Comissão'], value_name='Month')

#needs to be a datetime index to be able to resample below
df_ranges = df_ranges.set_index('Month')

#a function to resample an index
f = lambda df_ranges: df_ranges.resample(rule='MS', how='first')
# apply the resample rule to each groupby level
df_ranges = df_ranges.groupby(['Vendor Identifier','Region','Rights Holder', 'Titles', 'Regime', u'Comissão']).apply(f)

# print(df_ranges) 

# format the output, and drop unnecessary columns
df_ranges = df_ranges.drop(['Vendor Identifier','Region','Rights Holder','Titles',  'Regime',u'Comissão', 'variable'], axis=1)
df_ranges = df_ranges.reset_index()
#print df_ranges
df_ranges.rename(columns={'Month':'month,year'}, inplace=True)

df_ranges.to_excel('test.xlsx')

print "Date Range Matched"


#### MERGE ####
print "Merging..."


# Merge region from country by merging with regions sheet
df_sales = pd.merge(df_sales,df_regions,on="Country Code")
print "...Country Code done"
# Merge sales with encoding data, encoding, tax etc per sale
df_sales = pd.merge(df_sales,df_ranges,on=['Vendor Identifier','Region', 'month,year'])
print "...Vendor ID, Region, Date Range"

# df_sales = pd.merge(df_sales,df_titles,on=['Vendor Identifier','Region', 'month,year'])
# print "...Tax Regime"

# From df_sales, create a year column so we can easily Tax regime merge on that.
df_sales['Year'] = pd.DatetimeIndex(df_sales['month,year']).year
# 
# Merge to get tax rate, per year, per contract (vendor id, righstholder, region) in one table
df_sales = pd.merge(df_sales,df_tax,on=["Regime", "Year"])
print "...Regime done"


# Merge associated currency per sale, valid on the sale date
df_accrual = pd.merge(df_sales,df_currency,on=['Customer Currency','month,year'])
print "...Customer Currency"

#df_accrual.to_excel("testmerge.xlsx")


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
print "!!!!!!!RECOUPABLE!!!!!!!!!!"

df_recoup.rename(columns={'month,year':'monthyear'}, inplace=True)

df_recoup['Recoupable'] = df_recoup['Encoding U$'] + df_recoup['Media U$']
#df_recoup.drop(['Encoding U$','Media U$', 'Titles'],inplace=True,axis=1)
groupbyList = ['Region', 'Rights Holder','Titles','monthyear']

# df_recoup.reset_index(inplace = True)

df_accrual.to_excel(filename_accrual, encoding='utf-8',merge_cells=False)


print "!!!!!!!ROYALTY!!!!!!!!!!"
# df_accrual.reset_index(inplace = True)

df_accrual.rename(columns={'Month':'monthyear'}, inplace=True)


df_accrual_cumsum = df_accrual

dates = df_accrual['monthyear']

df_accrual.set_index(['monthyear'], inplace = True)
df_recoup.set_index(['monthyear'], inplace = True)

df_balance = pd.concat([df_accrual,df_recoup ])
df_balance.to_excel('testbalance.xlsx', encoding='utf-8',merge_cells=False)


df_balance.drop(['month,year'],inplace=True,axis=1)

df_balance.reset_index(inplace = True)
df_balance.set_index(groupbyList, inplace = True)
df_balance = df_balance.groupby(level=[0,1,2,3]).sum()

###Sums don't work over Nan values, need to fill.
df_balance['Recoupable'].fillna(0, inplace=True)
df_balance['Royalty'].fillna(0,inplace=True)
df_balance['Diff'] = df_balance['Recoupable'] + df_balance['Royalty']

df_balance = df_balance[['Recoupable','Royalty', 'Diff']]
# test_dataframe = df_balance[['Recoupable','Royalty', 'Diff']]
# test_dataframe.reset_index(inplace = True)
# test_dataframe.set_index(groupbyList, inplace = True)
#test_dataframe['Cumu Balance'] = test_dataframe['Diff'].groupby(level=[0,1,2]).cumsum()
df_balance['Cumu Balance'] = df_balance['Diff'].groupby(level=[0,1,2]).cumsum()

# test_dataframe['Cumu Units'] = test_dataframe['Units'].groupby(level=[0,1,2]).cumsum()
df_balance['Positive'] = df_balance['Cumu Balance'].mask(df_balance['Cumu Balance']<0).fillna(0)
# diff() subtracts from the previous value in the series.
x = df_balance['Positive'].groupby(level=[0,1,2]).diff()
df_balance['Payment Owed'] = x.fillna(df_balance['Positive'])

df_balance.to_excel('output/testing_balance.xlsx', encoding='utf-8',merge_cells=False)

#Merging currency info for BRL and MXN
df_balance.reset_index(inplace = True)
df_currency.rename(columns={'month,year':'monthyear'}, inplace=True)

df_brl = df_currency[df_currency['Customer Currency'].isin(['BRL'])]
df_brl = df_brl[[ 'monthyear', 'Exchange Rate']]
df_brl = df_brl.rename(columns = {'Exchange Rate':'BRL'})
df_balance = df_balance.merge(df_brl, on = ['monthyear'])

df_mxn = df_currency[df_currency['Customer Currency'].isin(['MXN'])]
df_mxn = df_mxn[['monthyear', 'Exchange Rate']]
df_mxn = df_mxn.rename(columns = {'Exchange Rate':'MXN'})
df_balance = df_balance.merge(df_mxn, on = ['monthyear'])

# print df_balance[: 3]

df_balance['Payment Owed BRL'] = df_balance['Payment Owed'] / df_balance['BRL']
df_balance['Payment Owed MXN'] = df_balance['Payment Owed'] / df_balance['MXN']


# dates = pd.date_range(df.index.min(), df.index.max())
# test_dataframe.reindex(dates).ffill()

# test_series = df_new['Diff'].groupby(level=[0,1,2,3]).sum().groupby(level=[0,1,3]).cumsum()
# test_dataframe = pd.concat([test_series], axis=1)
# # test_dataframe = test_dataframe.groupby(level=[0,1,2,3]).sum()
# test_dataframe['Cumu Balance'] = test_dataframe['Diff'].groupby(level=[0,1,2,3]).cumsum()

# print test_dataframe[:3]

df_accrual_cumsum = df_accrual_cumsum[['Units','Net revenue', 'Titles']]
df_accrual_cumsum.reset_index( inplace=True)

df_accrual_cumsum.set_index(['Titles', 'monthyear'], inplace=True)
df_accrual_cumsum = df_accrual_cumsum.groupby(level=[0,1]).sum()
df_accrual_cumsum['Unit Balance'] = df_accrual_cumsum['Units'].groupby(level=[0]).cumsum()
df_accrual_cumsum['Revenue Balance'] = df_accrual_cumsum['Net revenue'].groupby(level=[0]).cumsum()
#print df_accrual_cumsum[:3]

# df_new['Cumu Balance'] = df_new['Diff'].groupby(level=[0,1,2,3]).cumsum()
#
# print df_new[:3]
# df_new = pd.merge(df_recoup, df_accrual, how="inner", on=['Vendor Identifier', 'monthyear'])
#
# print small_accrual
# print df_new
# # df_balance = pd.merge(small_accrual,df_new, how='left', left_index=True, right_index=True)
#df_new['Recoupable'] = s_recoupable
# df_new = pd.merge(df_recoup, small_accrual,how='inner',left_index=True, right_index=True)
# df_balance['CUMU Units'] = df_balance['Units'].groupby(level=[1,2]).cumsum()
print "!!!!!!!BALANCE!!!!!!!!!!"


# print df_new[:3]

# # df_new.rename(columns={0:"Royalty"}, inplace=True)
# # df_new.reset_index(inplace=True)
# # df_new.set_index(groupbyList,inplace=True)
# # df_new['test'] = df_new['Royalty'].groupby(['Region']).sum()
# # df_new['Cumu Recoup'] = df_new['Recoupable'].cumsum()
# # df_new['Recoupable'].fillna(0)
# # df_new['Royalty'].fillna(0)
# df_new.set_index(groupbyList,inplace=True);
#
#
# df_new = df_new.groupby(level=[0,1,2,3]).sum()
# # df_new['Cumu Royalty'] = df_new['Royalty'].groupby(level=[0,1,2,3]).cumsum()
# # df_new['New Recoup'] = df_new['Recoupable'] * 1
# # df_new['Cumu Recoupable'] = df_new['New Recoup'].groupby(level=[0,1,2,3]).cumsum()
# df_new['Diff'] = df_new['Recoupable'] + df_new['Royalty']
# df_new['Cumu Balance'] = df_new['Diff'].groupby(level=[0,1,2,3]).cumsum()
#
#
#
# print df_new[:3]
# print df_new.dtypes


# df_new = df_new.groupby(level=[0,1]).sum()
# print df_new


# balance_groupby = ['month,year','Titles','Rights Holder']
#
#
# # creating a new dataframe from the series. This could be simpler. Some cargo cult happening here.
# # Groupby with Sum of the dimensions we want to preserve from ACCRUAL
# s_accrual_royalty2 = df_accrual.groupby(balance_groupby)['Royalty', 'Units','Net revenue'].sum()
# # ...same for recopable
# s_recoupable = df_recoup.groupby(balance_groupby)['Recoupable'].sum()
# df_recoupable= pd.concat([s_recoupable],axis=1)
# df_balance = pd.concat([s_accrual_royalty2],axis=1).reset_index()
# df_recoupable = df_recoupable.groupby(level=[1,2]).sum().reset_index()
#



# #merging the tables along the columns that interest us. not sure why it needs unicode handling.
# df_balance = df_balance.merge(df_recoupable, on = [u'Titles', u'Rights Holder'])
#
# # do the calcs
# # it needs to be multiindex so that cumsum works properly
# df_balance = df_balance.set_index(['month,year','Titles','Rights Holder'])
# # Get the actual columns we want for balance.
# # df_balance['Cumu Royalty'] = df_balance['Royalty'].groupby(level=[1,2]).cumsum()
# # these columns are not used in subsequent calculations, just nice-to-have
# df_balance['CUMU Units'] = df_balance['Units'].groupby(level=[1,2]).cumsum()
#
# # print df_balance
# # df_balance['Cumu Net revenue'] = df_balance['Net revenue'].groupby(level=[1,2]).cumsum()
# #
# # df_balance['Balance'] = df_balance['Recoupable'] + df_balance['Cumu Royalty']
# # df_balance['Positive'] = df_balance['Balance'].mask(df_balance['Balance']<0).fillna(0)
# # x = df_balance['Positive'].groupby(level=[1,2]).diff()
# # df_balance['Payment Owed'] = x.fillna(df_balance['Positive'])
print "Balance Calculated"

#### EXPORTING ACCRUAL REPORT ####
df_accrual.drop(['Download Date (PST)', 'Royalty Price','Customer Currency','Customer Price', 'Brasil', 'Offshore', 'Year'],inplace=True,axis=1)
# df_accrual.drop(['Download Date (PST)', 'Royalty Price','Customer Currency','Customer Price', u'Comissão','Vendor Identifier','Brasil', 'Offshore', 'Year'],inplace=True,axis=1)

accrual_groupby = ['month,year','Vendor Identifier','Provider','Country Code', 'Titles','Region','Rights Holder','Product Type Identifier','Asset/Content Flavor']
df_accrual = df_accrual.groupby(accrual_groupby).sum()
#df_accrual = df_accrual.set_index(accrual_groupby)
df_accrual.to_excel(filename_accrual, encoding='utf-8',merge_cells=False)

#### EXPORTING BALANCE REPORT ####
df_balance.to_excel(filename_balance, encoding='utf-8',merge_cells=False)


#### EXPORTING RECOUPABLE REPORT ####
df_recoup.reset_index(inplace = True)

df_recoup = df_recoup[df_recoup['Recoupable'] != 0]
df_recoup = df_recoup.groupby(['monthyear','Titles','Rights Holder']).sum()
df_recoup.to_excel(filename_recoupable, encoding='utf-8',merge_cells=False)

df_accrual_cumsum.to_excel('output/rolling_sum.xlsx', encoding='utf-8',merge_cells=False)
print "Done, files exported"

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import pandas as pd
import numpy as np

file = "input/DeParaSofaDigital.xlsx"

df_ranges = pd.read_excel(file,sheetname="Titles")[['Vendor Identifier','Region','Rights Holder','Start Date','End Date']]

#pivot the values into position using melt
df_ranges = pd.melt(df_ranges, id_vars=['Vendor Identifier', 'Region','Rights Holder'], value_name='Month')

#needs to be a datetime index to be able to resample below
df_ranges = df_ranges.set_index('Month')

#a function to resample an index
f = lambda df_ranges: df_ranges.resample(rule='MS', how='first')
# apply the resample rule to each groupby level
df_ranges = df_ranges.groupby(['Vendor Identifier','Region','Rights Holder']).apply(f)

# format the output, and drop unnecessary columns
df_ranges =df_ranges.drop(['Vendor Identifier','Region','Rights Holder','variable'], axis=1)

#print df_ranges
#df_ranges.to_excel('out.xlsx', encoding='utf-8',merge_cells=False)
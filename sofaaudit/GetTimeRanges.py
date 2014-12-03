#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import pandas as pd
import numpy as np

file = "input/DeParaSofaDigital.xlsx"

df = pd.read_excel(file,sheetname="Titles")[['Vendor Identifier','Region','Rights Holder','Start Date','End Date']]

#pivot the values into position using melt
df = pd.melt(df, id_vars=['Vendor Identifier', 'Region','Rights Holder'], value_name='Months')

#needs to be a datetime index to be able to resample below
df = df.set_index('Months')

#a function to resample an index
f = lambda df: df.resample(rule='M', how='first')
# apply the resample rule to each groupby level
df = df.groupby(['Vendor Identifier','Region','Rights Holder']).apply(f)

# format the output, and drop unnecessary columns
df =df.drop(['Vendor Identifier','Region','Rights Holder','variable'], axis=1)

#print df
df.to_excel('out.xlsx', encoding='utf-8',merge_cells=False)
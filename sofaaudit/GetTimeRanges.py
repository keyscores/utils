#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import pandas as pd
import numpy as np

filename_apple="test.xlsx"
file = "input/DeParaSofaDigital.xlsx"

df1 = pd.read_excel(filename_apple)
df = pd.read_excel(file,sheetname="Titles")[['Vendor Identifier','Region','Rights Holder','Start Date','End Date']]
df = df[:3]

#pivot the values into position using melt
df = pd.melt(df, id_vars=['Vendor Identifier', 'Region','Rights Holder'], value_name='Months')

df = df.set_index('Months')
f = lambda df: df.resample(rule='M', how='first')
df = df.groupby(['Vendor Identifier','Region','Rights Holder']).apply(f)

#print df.agg()
df =df.drop(['Vendor Identifier','Region','Rights Holder','variable'], axis=1)

print df
df.to_excel('out.xlsx', encoding='utf-8',merge_cells=False)
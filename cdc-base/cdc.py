#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
import numpy as np
import os.path

filename_apple="BASE-CDC.xlsm"


if os.path.isfile("temp") == False:
    print 'Loading files....'
    df_sales = pd.read_excel(filename_apple, header=1)
    #df_sales = pd.read_excel(filename_apple, header=1)[u"Ano/Mês","RECEBIMENTOS_MENOS_DEDUCOES", "RECEBIMENTOS_MENOS_CUSTOS","RECEBIMENTOS_MENOS_DESPESAS","TOTAL_INADIMPLENCIA","INVESTIMENTOS_CUSTOATUAL","TICKETMEDIO","TOTAL_FATURAMENTO","TOT_CLI","CLI_NOVOS","RECEBIMENTO_MES","RECEBIMENTO_PREVISTO_NO_PERIODO","CUSTOS","DESPESAS"]

    df_sales.to_pickle("temp")
else:
	print "Temp file found"
	
df_sales = pd.read_pickle("temp")
#print df_sales.dtypes
df_sales = df_sales.set_index(u"Ano/Mês") 
df_new = df_sales.loc[:,["LOJA","DATA_PRIM_FAT","GRUPOS_CONVENCAO","RECEBIMENTOS_MENOS_DEDUCOES", "RECEBIMENTOS_MENOS_CUSTOS","RECEBIMENTOS_MENOS_DESPESAS","TOTAL_INADIMPLENCIA","INVESTIMENTOS_CUSTOATUAL","TICKETMEDIO","TOTAL_FATURAMENTO","TOT_CLI","CLI_NOVOS","RECEBIMENTO_MES","RECEBIMENTO_PREVISTO_NO_PERIODO","CUSTOS","DESPESAS"]]
df_new.to_excel("final.xlsx")





#### IMPORT ####




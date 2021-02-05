# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 11:23:13 2020

@author: jason
"""


import json
from dateutil.relativedelta import *
import datetime
import pandas as pd
import os
import time
import urllib.request

import requests
path1=os.getcwd()
datapath = os.path.join(path1, 'data')
path_price = os.path.join(datapath, 'price')
if os.path.exists(datapath) == False:
    os.mkdir(datapath)
if os.path.exists(path_price) == False:
    os.mkdir(path_price)
#從政府資料開放平台中國民所得統計-國內生產毛額貢獻度-依支出分-年 下載資料
r = requests.get("https://quality.data.gov.tw/dq_download_json.php?nid=6799&md5_url=f7e51c4cf417aaf3ecaff622f30025bf")
list_of_dicts = r.json()
tlist = []
nlist = []

#把1961的資料去除掉 因為1961的檔案不齊全
for i in range(0,len(list_of_dicts)):
    if list_of_dicts[i]['Item'] == '國內生產毛額GDP(名目值，百萬元)' and list_of_dicts[i]['TYPE'] == '年增率(%)' and '1961' not in list_of_dicts[i]['TIME_PERIOD']:
        nlist.append(list_of_dicts[i]['Item_VALUE'])
        tlist.append(list_of_dicts[i]['TIME_PERIOD'])


#獲得交易價格 如果沒有當日價格 用後一個交易日的數據
def getprice(y,m,bullish_target):  
    y = str(y)
    if len(m) < 2:
        m = '0' + m
    #這季結束的資料要在下一個月初才會知道
    open_day = datetime.datetime.strptime(y + '-' + m + '-01', '%Y-%m-%d') + relativedelta(months=+1)
    close_day = datetime.datetime.strptime(y + '-' + m + '-01', '%Y-%m-%d') + relativedelta(months=+2)

    price_data = pd.read_csv( bullish_target + '.csv')
    price_data = price_data.dropna()  #去掉缺失的樣本
    date_list = price_data['Date'].tolist()
    start_month = datetime.datetime.strftime(open_day,'%Y-%m')
    end_month = datetime.datetime.strftime(close_day,'%Y-%m')

    check_start = 0
    check_end = 0
    end_idx = -10 #為了處理找不到資料的情況
    for i in range(0,len(date_list)):
        if check_start == 0 and start_month in date_list[i]:
            start_idx = i
            check_start = 1 
        elif check_end == 0 and end_month in date_list[i]:
            check_end = 1
        elif check_end == 1 and end_month not in date_list[i]:
            end_idx = i
            break

    if check_start == 1 and check_end == 1:#確定都找到了資料再作處理
        trade_range = price_data.iloc[start_idx:end_idx]#以下為上課內容
        trade_date_list = trade_range['Date'].tolist()
        for i in range(0,len(trade_date_list)):
            trade_date_list[i] = datetime.datetime.strptime(trade_date_list[i],'%Y-%m-%d')   
        open_delta = []
 
        for i in range(0,len(trade_date_list)):
            open_delta.append(abs(trade_date_list[i] - open_day))   
        open_indices = [i for i, x in enumerate(open_delta) if x == min(open_delta)]
        open_idx = open_indices[-1]#如果有兩個一樣的相差日期 找後面的日期
        trade_range = trade_range.reset_index()
        open_price = trade_range['Adj Close'][open_idx]  
    else:  #資料不在檔案裡
        open_price = "NaN"
    return (open_price)


#雖然台灣大約是2 5 8 11 月公布gdp值 但目前先假設 季一結束就公布資料
def getdateprice(target):
    targetmonth=['3','6','9','12']
    targetprice = []
    for i in range(2000,2020):
        for j in targetmonth:
           targetprice.append(getprice(str(i),j,target))
        with open(target+'.json','w') as file_object:#找到後存在json檔
            json.dump(targetprice,file_object) 
            
#先轉換是其型式，再來用上課交的辦法來抓資料和存資料

def getTime(timeStamp):
    return (int(time.mktime(time.strptime(timeStamp,"%Y-%m-%d"))+28800))#和日期差了8個小時 所以家28800秒


def getPriceData(ticker,start,end):
    Start = getTime(start)#轉換成我們要的型式
    End = getTime(end)+86400
    
    url = 'https://query1.finance.yahoo.com/v7/finance/download/'+str(ticker)+'.TW?period1='+str(Start)+'&period2='+str(End)+'&interval=1d&events=history'
    urllib.request.urlretrieve(url,str(ticker)+'.csv')
###屬於觀光類別的股票編號
origin = os.getcwd() 
ftarget = ['2701','2702','2704','2705','2706','2722','2727','2731','2748','5706','8462','8940','9943']
start = '2000-01-01'
end = '2020-01-01'
path = "data/price" #進入到data/price處理 
os.chdir( path )
for i in ftarget:#找出要的那一檔股票
    getPriceData(i,start,end)
for i in ftarget:#找出所要日期的價格
    getdateprice(i)          
fprice = []
for i in range(0,79):
    p = 0
    n = 0
    for j in ftarget:
        with open(j + '.json', 'r') as f:#讀資料
            abc = json.load(f)
        if abc[i] == 'NaN':#如果沒有找到資料 直接略過 不列入計算
            continue
        p = p+ float(abc[i])
        n=n+1
    fprice.append(p/n)#這邊是找平均觀光事業價格
true_nlist = []
for i in range(152,len(nlist)):
    true_nlist.append(float(nlist[i]))
    
#############################33
#交易策略 如果兩期GDP都跌就買進 如果兩期GDP都漲就賣出 
#一張股票為1000股 stock為手上有的股票 因為要有股票才能賣股票
sold = 0
spend = 0
stock = 0
for i in range(0,len(fprice)-2):
    if true_nlist[i+2] < true_nlist[i+1] < true_nlist[i]:
        stock = stock + 1000
        spend = spend + fprice[i+2]*1000
      
    elif true_nlist[i+2] > true_nlist[i+1] > true_nlist[i] and stock>=1:
        stock = stock - 1000
        sold = sold + fprice[i+2]*1000
   
        
profit = sold - spend 
ROI = profit / spend
print('淨利 =' + str(profit))   
print('投資報酬率 =' + str(ROI))
os.chdir( path1 )

  

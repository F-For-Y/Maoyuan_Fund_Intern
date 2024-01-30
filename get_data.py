# encoding: UTF-8
import logging
import requests
import json
import pandas as pd
import math
import numpy as np
from datetime import datetime
from datetime import date
import psycopg2
from iFinDPy import *
import akshare as ak
import re


logger = logging.getLogger()


class SQI_DB(object):

    def __init__(self, url='http://182.254.241.204:5001', user='huangyangcheng@sqicapital.com', password='sq123456'):
        self.url = url
        self.user = user
        self.password = password
        self.token = self.generate_token()

    def generate_token(self):
        login_url = self.url + "/auth/login"
        headers = {'content-type': 'application/json'}
        login_info = {'email': self.user, 'password': self.password}
        login_response = requests.post(login_url, data=json.dumps(login_info), headers=headers)
        return json.loads(login_response.text)['auth_token']

    # CCM日频时间序列接口
    def get_ssd(self, index_id, startday='', endday='', source='ifind', ret_type='df'):
        data_header = {'Authorization': 'Basic ' + self.token, 'content-type': 'application/json'}
        data_url = self.url + "/ssd"
        data_info = {
            'indexes': [
                {
                    'id': index_id,
                    'startday': startday,
                    'endday': endday,
                }
            ],
            'source': source
        }
        data_rsp = requests.post(data_url, data=json.dumps(data_info), headers=data_header)
        data = json.loads(json.loads(data_rsp.text)['data'])
        if ret_type == 'df':
            df = pd.DataFrame(data)
        else:
            # raise warning !
            raise ValueError('Unsupported ret_type={}'.format(ret_type))
        return df

    # CCM K线接口数据
    def get_bar(self, symbol, bartype, ret_type='df'):
        data_header = {'Authorization': 'Basic ' + self.token, 'content-type': 'application/json'}
        data_url = self.url + "/bar"
        data_info = {
            'index':
                {
                    'symbol': symbol,
                    'bartype': bartype  # '1 Min'  '5 Min' '15 Min'  '1 Hour' 'Daily'
                }
        }
        data_rsp = requests.post(data_url, data=json.dumps(data_info), headers=data_header)
        data = json.loads(json.loads(data_rsp.text)['data'])
        if ret_type == 'df':
            df = pd.DataFrame(data)
        else:
            raise ValueError('Unsupported ret_type={}'.format(ret_type))
        return df


# target: SQI_DB 对象, list_id: a list of 指数ID, list_df: dataframe list
def append_df(target, list_id, list_df):
    for i in range(len(list_id)):
        df = target.get_ssd(list_id[i]).dropna()
        df = df.drop(index=df[df['index_value'] == 0].index)
        # df['tradingday'] = df['tradingday'].apply(lambda x: x[:4] + '-' + x[4:6] + '-' + x[6:8])
        list_df.append(df)
        print('Successfully collecting {} ({}/{})'.format(list_id[i], i+1, len(list_id)))


def price_quantile(ar):
    price = ar[len(ar) - 1]
    ar.sort()
    l = len(ar)
    for i in range(l):
        if ar[i] > price:
            return int((i / l) * 100)
        elif i == l - 1:
            return 100


# 波动率 -> list
# 取55天算std
def volatility(ar):
    vol_list = []
    vol_std_list = []
    for i in range(len(ar) - 1):
        vol_list.append(math.log((ar[i + 1] / ar[i]), math.e))
    for i in range(len(ar) - 54):
        vol_std_list.append(np.std(vol_list[i:i + 55]) * 15.5)
    return vol_std_list


# 相关性
def price_ratio(ar):
    ratio_list = []
    for i in range(len(ar) - 1):
        ratio_list.append(math.log((ar[i + 1] / ar[i]), math.e))
    return ratio_list


def cor(typo, category_list, df_list):
    cor_list = []
    for i in range(len(category_list)):
        if category_list[i] == '有色' and typo == 1:
            cor_list.append((df_list[i].tail(55)['index_value'].to_list()))
        elif category_list[i] == '贵金属' and typo == 2:
            cor_list.append((df_list[i].tail(55)['index_value'].to_list()))
        elif category_list[i] == '黑色' and typo == 3:
            cor_list.append((df_list[i].tail(55)['index_value'].to_list()))
        elif category_list[i] == '农产品' and typo == 4:
            cor_list.append((df_list[i].tail(55)['index_value'].to_list()))
        elif category_list[i] == '化工' and typo == 5:
            cor_list.append((df_list[i].tail(55)['index_value'].to_list()))
    cor_list = np.corrcoef(cor_list)
    return cor_list.round(2)


# 月度波动概率和均值
def ratio_to_peak(series):
    if len(series) <= 1:
        return 0
    else:
        return (series.iloc[1] / series.iloc[0]) - 1


def positive_probability(series):
    return (series.sum() / len(series)) * 100


def month_review(df1, if_select, year):
    df = df1
    temp = []
    df = df.drop(index=df[df['index_value'] == 0].index)
    df['tradingday'] = df['tradingday'].apply(lambda x: str(x)[:4] + '-' + str(x)[4:6] + '-' + str(x)[6:8])
    df['tradingday'] = pd.to_datetime(df['tradingday'], errors='coerce')
    df['month'] = df['tradingday'].apply(lambda x: x.month)
    df['Year'] = df['tradingday'].apply(lambda x: x.year)
    end_time = datetime.now()
    # print(end_time)
    if if_select == 1:
        df = df[(df['Year'] >= end_time.year-year) & (df['Year'] <= end_time.year)]
    df['first'] = df['tradingday'].where(df['month'] != df.shift(1)['month'], np.nan)
    df['last'] = df['tradingday'].where(df['month'] != df.shift(-1)['month'], np.nan)
    df = df[df['first'].notna() | df['last'].notna()]
    df = df.iloc[2:]
    df['tradingday'] = df['tradingday'].apply(lambda x: x.year)
    df = df.groupby(['tradingday', 'month'])["index_value"].agg(ratio_to_peak)
    df = df.reset_index()
    df['positive'] = df['index_value'].apply(lambda x: x > 0).replace(True, 1).replace(False, 0)
    df = df.groupby('month')[['index_value', 'positive']].agg(positive_probability)
    temp.append(np.round(df['index_value'].to_list(), 2).tolist())
    temp.append(np.round(df['positive'].to_list(), 2).tolist())
    return temp


# 获取合约信息
def get_contract(download, contract_abbreviation):
    timetable = []
    keys = []
    keys_value = []
    local_time_str = datetime.now().strftime('%Y-%m-%d')

    for i in range(10):
        year = int(local_time_str[0:4])
        month = int(local_time_str[5:7]) + i + 1
        day = int(local_time_str[8:10])
        while month > 12:
            month = month - 12
            year += 1
        time = datetime(year=year, month=month, day=day)
        timetable.append(contract_abbreviation + str(time)[2:4] + str(time)[5:7])

    for i in range(len(timetable)):
        temp = download.get_bar(timetable[i], 'Daily').dropna()
        if not temp.empty:
            temp = temp.drop(index=temp[temp['closeprice'] == 0].index)
            keys.append(timetable[i])
            keys_value.append(temp.tail(50))

    contract_json = {}.fromkeys(keys, 0)
    for i in range(len(keys)):
        contract_json[keys[i]] = keys_value[i]

    return contract_json


# 获取持仓信息
# 通过connect方法，创建连接对象 conn
# 这里连接的是本地的数据库
# def receipt_query(contract_id, tr_day):
#     conn = psycopg2.connect(database="future", user="postgres", password="ck1/ck1@123456", host="81.68.204.178", port="6001")
#
#     # 执行之后不报错，就表示连接成功了！
#     # print('postgreSQL数据库“db_test”连接成功!')
#     cursor=conn.cursor() ##通过cursor方法，对数据库进行操作
#     query = "select * from receipt_select('{}', '{}')".format(contract_id, tr_day)
#     cursor.execute(query)
#     rows = cursor.fetchall()
#     receipt_tb = pd.DataFrame(rows)
#     receipt_tb.rename(columns={0:'tradingday', 1:'productid', 2:'exchange', 3:'company_sell', 4:'sell', 5:'company_buy', 6:'buy'},inplace=True)
#     return receipt_tb
#
#
# # timeline
# def chi_c_r(contract_id, num, date):
#     # temp_df = download.get_ssd(contract_id).dropna()
#     # temp_df = temp_df.drop(index=temp_df[temp_df['index_value'] == 0].index)
#     overall = []
#     one_to_five = []
#     six_to_twe = []
#     other = []
#     # tr_d = temp_df['tradingday'].to_list()[-num:]
#     # date = datetime.date(2023, 5, 16)
#     tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
#     tr_d = tool_trade_date_hist_sina_df[tool_trade_date_hist_sina_df['trade_date'] < date]
#     tr_d = tr_d['trade_date'].apply(lambda x: x.strftime("%Y%m%d")).to_list()[-num:]
#     # print(tr_d)
#     # price = temp_df['index_value'].to_list()[-num:]
#     price = []
#     for i in range(num):
#         df = receipt_query(re.match(r"[a-zA-Z]+", contract_id)[0], tr_d[i])
#         # df = receipt_query(contract_id, tr_d[i])
#         sell = df['sell'].to_list()
#         buy = df['buy'].to_list()
#         one_to_five.append(-sum(sell[0:5])+sum(buy[0:5]))
#         six_to_twe.append(-sum(sell[5:])+sum(buy[5:]))
#         other.append(sum(sell[:])-sum(buy[:]))
#         print('{}/{}'.format(i+1, num))
#     overall.append(tr_d)
#     overall.append(one_to_five)
#     overall.append(six_to_twe)
#     overall.append(price)
#     overall.append(other)
#     return overall

def chi_c_get(contract_id):
    conn = psycopg2.connect(database="future", user="postgres", password="ck1/ck1@123456", host="81.68.204.178",
                            port="6001")

    # 执行之后不报错，就表示连接成功了！
    # print('postgreSQL数据库“db_test”连接成功!')
    cursor = conn.cursor()  ##通过cursor方法，对数据库进行操作
    query = "select * from public.{} where productid ilike {}".format('"Chi_cang"',"'" + contract_id + "'")
    cursor.execute(query)
    rows = cursor.fetchall()
    df = pd.DataFrame(rows)
    overall = []
    tr_d = df[0].to_list()[-150:]
    one_to_five = df[2].to_list()[-150:]
    six_to_twe = df[3].to_list()[-150:]
    other = df[4].to_list()[-150:]
    price = []
    overall.append(tr_d)
    overall.append(one_to_five)
    overall.append(six_to_twe)
    overall.append(price)
    overall.append(other)
    return overall


# ------------------------------股票------------------------
def thslogindemo():
    # 输入用户的帐号和密码
    # -> thsLogin = THS_iFinDLogin("数据接口_账号","数据接口_密码")
    thsLogin = THS_iFinDLogin("llsy017","1qaz2wsx")
    print(thsLogin)
    if thsLogin != 0:
        print('登录失败')
    else:
        print('登录成功')


def datepool_basicdata_demo():
    # 通过数据池的板块成分函数和基础数据函数，提取沪深300的全部股票在2020-11-16日的日不复权收盘价
    data_hs300 = THS_DP('block', '2020-11-16;001005290', 'date:Y,thscode:Y,security_name:Y')
    if data_hs300.errorcode != 0:
        print('error:{}'.format(data_hs300.errmsg))
    else:
        seccode_hs300_list = data_hs300.data['THSCODE'].tolist()
        data_result = THS_BD(seccode_hs300_list, 'ths_close_price_stock', '2020-11-16,100')
        if data_result.errorcode != 0:
            print('error:{}'.format(data_result.errmsg))
        else:
            data_df = data_result.data
            return data_df
            # print(data_df)
    return 0


def datapool_realtime_demo():
    # 通过数据池的板块成分函数和实时行情函数，提取上证50的全部股票的最新价数据,并将其导出为csv文件
    today_str = datetime.today().strftime('%Y-%m-%d')
    print('today:{}'.format(today_str))
    data_sz50 = THS_DP('block', '{};001005260'.format(today_str), 'date:Y,thscode:Y,security_name:Y')
    if data_sz50.errorcode != 0:
        print('error:{}'.format(data_sz50.errmsg))
    else:
        seccode_sz50_list = data_sz50.data['THSCODE'].tolist()
        data_result = THS_RQ(seccode_sz50_list,'latest')
        if data_result.errorcode != 0:
            print('error:{}'.format(data_result.errmsg))
        else:
            data_df = data_result.data
            print(data_df)
            data_df.to_csv('realtimedata_{}.csv'.format(today_str))


# 上证50 (001005260) ，沪深300 (001005290)，中证500和中证1000这四个宽基指数的各自申万一级行业占比情况
def stock(day, block ,ths_code):
    data_sz50 = THS_DP('{}'.format(block), '{};{}'.format(day,ths_code), 'thscode:Y')
    if data_sz50.errorcode != 0:
        print('error:{}'.format(data_sz50.errmsg))
    else:
        seccode_sz300_list = data_sz50.data['THSCODE'].tolist()
        data_result = THS_BD(seccode_sz300_list, 'ths_stock_short_name_stock;ths_current_mv_stock;ths_the_sw_industry_stock', ';{};100,{}'.format(day, day))
        if data_result.errorcode != 0:
            print('error:{}'.format(data_result.errmsg))
        else:
            data_df = data_result.data
            return data_df
            # print(data_df)
    return 0


def get_stock():
    thslogindemo()
    local_time = date.today()
    tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
    tool_trade_date_hist_sina_df = tool_trade_date_hist_sina_df[local_time > tool_trade_date_hist_sina_df['trade_date']]
    local_time = tool_trade_date_hist_sina_df['trade_date'].to_list()[-1].strftime('%Y-%m-%d')
    # 上证50
    df_sz50 = stock(local_time, 'block', '001005260').groupby('ths_the_sw_industry_stock')['ths_current_mv_stock'].sum().reset_index()
    sz50_list = []
    for i in range(df_sz50.shape[0]):
        temp = {}.fromkeys(['value', 'name'], 0)
        temp['value'] = df_sz50['ths_current_mv_stock'].to_list()[i]
        temp['name'] = df_sz50['ths_the_sw_industry_stock'].to_list()[i]
        sz50_list.append(temp)
    print('get 上证50 !')
    # 沪深300
    df_hs300 = stock(local_time, 'block', '001005290').groupby('ths_the_sw_industry_stock')['ths_current_mv_stock'].sum().reset_index()
    hs300_list = []
    for i in range(df_hs300.shape[0]):
        temp = {}.fromkeys(['value', 'name'], 0)
        temp['value'] = df_hs300['ths_current_mv_stock'].to_list()[i]
        temp['name'] = df_hs300['ths_the_sw_industry_stock'].to_list()[i]
        hs300_list.append(temp)
    print('get 沪深300 !')
    # 中证1000
    df_sz1000 = stock(local_time, 'index', '000852').groupby('ths_the_sw_industry_stock')['ths_current_mv_stock'].sum().reset_index()
    sz1000_list = []
    for i in range(df_sz1000.shape[0]):
        temp = {}.fromkeys(['value', 'name'], 0)
        temp['value'] = df_sz1000['ths_current_mv_stock'].to_list()[i]
        temp['name'] = df_sz1000['ths_the_sw_industry_stock'].to_list()[i]
        sz1000_list.append(temp)
    print('get 中证1000 !')
    # 中证500
    df_zz500 = stock(local_time, 'index', '000905').groupby('ths_the_sw_industry_stock')['ths_current_mv_stock'].sum().reset_index()
    zz500_list = []
    for i in range(df_zz500.shape[0]):
        temp = {}.fromkeys(['value', 'name'], 0)
        temp['value'] = df_zz500['ths_current_mv_stock'].to_list()[i]
        temp['name'] = df_zz500['ths_the_sw_industry_stock'].to_list()[i]
        zz500_list.append(temp)
    print('get 中证500 !')

    res = [sz50_list, hs300_list, sz1000_list, zz500_list]

    return res




























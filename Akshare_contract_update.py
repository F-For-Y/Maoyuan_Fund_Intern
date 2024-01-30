from sqlalchemy import Column, String, create_engine, Integer, DECIMAL, SMALLINT
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import psycopg2
from urllib import parse
import akshare as ak
import pandas as pd
import re
import datetime
import psycopg2

# 创建对象的基类:
Base = declarative_base()
engine = create_engine('postgresql://postgres:{}@{}/{}'
                           .format(parse.quote_plus("ck1/ck1@123456"), "81.68.204.178:6001", "future"))
DBSession = sessionmaker(bind=engine)


# 定义User对象:
class Contract(Base):
    # 表的名字:
    __tablename__ = 'contract'

    # 表的结构:
    # index = Column(Integer, autoincrement=True, primary_key=True, nullable=False)
    tradingday = Column(String(8), primary_key=True, unique=False, nullable=False)
    productid = Column(String(5), nullable=False)
    symbol = Column(String(8), primary_key=True, nullable=False)
    exchange = Column(String(6), nullable=False)
    rank = Column(SMALLINT, primary_key=True, nullable=False)
    company = Column(String(30), primary_key=True, nullable=False)
    quantity = Column(DECIMAL, nullable=False)
    change = Column(DECIMAL, nullable=False)
    ranktype = Column(String(8), primary_key=True, nullable=False)


def create_table():
    # 创建表
    Base.metadata.create_all(engine)


def drop_table():
    # 删除表
    session = DBSession()  # 创建会话
    session.execute('drop table if exists contract')
    session.commit()
    session.close()


def insert_table(df, exchange_name, time):
    session = DBSession()
    if type(df) == pd.DataFrame and df.shape[0] != 0:
        for i in range(df.shape[0]):
            row1 = Contract(tradingday=time,
                            productid=df['var'].to_list()[0],
                            symbol=df['symbol'].to_list()[0],
                            exchange=exchange_name,
                            rank=df['rank'].to_list()[i],
                            company=df['short_party_name'].to_list()[i],
                            quantity=df['short_open_interest'].to_list()[i],
                            change=df['short_open_interest_chg'].to_list()[i],
                            ranktype='short')
            row2 = Contract(tradingday=time,
                            productid=df['var'].to_list()[0],
                            symbol=df['symbol'].to_list()[0],
                            exchange=exchange_name,
                            rank=df['rank'].to_list()[i],
                            company=df['long_party_name'].to_list()[i],
                            quantity=df['long_open_interest'].to_list()[i],
                            change=df['long_open_interest_chg'].to_list()[i],
                            ranktype='long')
            row3 = Contract(tradingday=time,
                            productid=df['var'].to_list()[0],
                            symbol=df['symbol'].to_list()[0],
                            exchange=exchange_name,
                            rank=df['rank'].to_list()[i],
                            company=df['vol_party_name'].to_list()[i],
                            quantity=df['vol'].to_list()[i],
                            change=df['vol_chg'].to_list()[i],
                            ranktype='volume')
            session.add_all([row1, row2, row3])
            session.commit()
        session.close()
    else:
        session.close()


# 1. 创建 table 对象
def update_contract():
    # 2. variable: date, start, tr_date
    date = datetime.date.today()
    with open('d_store/update/update_receipt', 'r+', encoding='utf-8') as f:
        start = f.read()
        start = datetime.date(int(start[0:4]), int(start[5:7]), int(start[8:]))

    if start == date:
        print('数据库已更新')
    else:
        tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
        tool_trade_date_hist_sina_df = tool_trade_date_hist_sina_df[start <= tool_trade_date_hist_sina_df['trade_date']]
        tool_trade_date_hist_sina_df = tool_trade_date_hist_sina_df[date > tool_trade_date_hist_sina_df['trade_date']]
        if tool_trade_date_hist_sina_df.shape[0] == 0:
            print('数据库已更新')
        else:
            tr_date = tool_trade_date_hist_sina_df['trade_date'].apply(lambda x: x.strftime("%Y%m%d")).to_list()

            tr_date2 = tr_date[:]

            for i in range(len(tr_date2)):
                print("-----------------------Loading data on {}({}/{})---------------------------".format(tr_date2[i], i+1, len(tr_date2)))

                print("--------------------1.dce--------------------")
                ak_dl = ak.get_dce_rank_table(date=tr_date2[i])
                ak_dl_keys = list(ak_dl.keys())
                for j in range(len(ak_dl.keys())):
                    temp = ak_dl[ak_dl_keys[j]]
                    tmep = temp.fillna({'vol_party_name': '-', 'long_party_name': '-', 'short_party_name': '-', 'vol': 0.0, 'vol_chg': 0.0, 'long_open_interest': 0.0,
                                   'long_open_interest_chg': 0.0, 'short_open_interest': 0.0, 'short_open_interest_chg': 0.0})
                    insert_table(temp, 'dce', tr_date2[i])
                    print('Successfully insert {} ({}/{}) from dce on day {} ({}/{})'
                          .format(ak_dl_keys[j], j + 1, len(ak_dl_keys), tr_date2[i], i + 1, len(tr_date2)))

                print("--------------------2.cf--------------------")
                ak_cf = ak.get_cffex_rank_table(date=tr_date2[i])
                ak_cf_keys = list(ak_cf.keys())
                for j in range(len(ak_cf.keys())):
                    ak_cf[ak_cf_keys[j]].rename(columns={'variety': 'var'}, inplace=True)
                    temp = ak_cf[ak_cf_keys[j]].drop(index=ak_cf[ak_cf_keys[j]].index[ak_cf[ak_cf_keys[j]].shape[0]-1])
                    temp = temp.fillna({'vol_party_name': '-', 'long_party_name': '-', 'short_party_name': '-', 'vol': 0.0, 'vol_chg': 0.0, 'long_open_interest': 0.0,
                                   'long_open_interest_chg': 0.0, 'short_open_interest': 0.0, 'short_open_interest_chg': 0.0})
                    insert_table(temp, 'cffex', tr_date2[i])
                    print('Successfully insert {} ({}/{}) from cffex on day {} ({}/{})'
                          .format(ak_cf_keys[j], j + 1, len(ak_cf_keys), tr_date2[i], i + 1, len(tr_date2)))

                print("--------------------3.cz--------------------")
                ak_cz = ak.get_czce_rank_table(date=tr_date2[i])
                ak_cz_keys = list(ak_cz.keys())
                for j in range(len(ak_cz.keys())):
                    temp = ak_cz[ak_cz_keys[j]]
                    temp['var'] = ''.join(re.findall(r'[A-Za-z]', list(ak_cz.keys())[j]))
                    temp['symbol'] = ak_cz_keys[j]
                    temp['long_open_interest'] = temp['long_open_interest'].apply(lambda x: float('0'+re.sub('\D', '', x)))
                    temp['long_open_interest_chg'] = temp['long_open_interest_chg'].apply(lambda x: float('0'+re.sub('\D', '', x)))
                    temp['short_open_interest'] = temp['short_open_interest'].apply(lambda x: float('0'+re.sub('\D', '', x)))
                    temp['short_open_interest_chg'] = temp['short_open_interest_chg'].apply(lambda x: float('0'+re.sub('\D', '', x)))
                    temp['vol'] = temp['vol'].apply(lambda x: float('0'+re.sub('\D', '', x)))
                    temp['vol_chg'] = temp['vol_chg'].apply(lambda x: float('0'+re.sub('\D', '', x)))
                    temp = temp.fillna({'vol_party_name': '-', 'long_party_name': '-', 'short_party_name': '-', 'vol': 0.0, 'vol_chg': 0.0, 'long_open_interest': 0.0,
                                   'long_open_interest_chg': 0.0, 'short_open_interest': 0.0, 'short_open_interest_chg': 0.0})
                    insert_table(temp, 'czce', tr_date2[i])
                    print('Successfully insert {} ({}/{}) from czce on day {} ({}/{})'
                          .format(ak_cz_keys[j], j + 1, len(ak_cz_keys), tr_date2[i], i + 1, len(tr_date2)))

                print("--------------------4.sh--------------------")
                ak_sh = ak.get_shfe_rank_table(date=tr_date2[i])
                ak_sh_keys = list(ak_sh.keys())
                for j in range(len(ak_sh.keys())):
                    ak_sh[ak_sh_keys[j]].rename(columns={'variety': 'var'}, inplace=True)
                    temp = ak_sh[ak_sh_keys[j]].drop(index=ak_sh[ak_sh_keys[j]].index[ak_sh[ak_sh_keys[j]].shape[0]-1])
                    temp = temp.fillna({'vol_party_name': '-', 'long_party_name': '-', 'short_party_name': '-', 'vol': 0.0, 'vol_chg': 0.0, 'long_open_interest': 0.0,
                                   'long_open_interest_chg': 0.0, 'short_open_interest': 0.0, 'short_open_interest_chg': 0.0})
                    insert_table(temp, 'shfe', tr_date2[i])
                    print('Successfully insert {} ({}/{}) from shfe on day {} ({}/{})'
                          .format(ak_sh_keys[j], j + 1, len(ak_sh_keys), tr_date2[i], i + 1, len(tr_date2)))
            print('数据库更新完毕')
# insert_table(ak_d['c2305'],'dce')

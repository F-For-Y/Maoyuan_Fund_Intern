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
class Chi_cang(Base):
    # 表的名字:
    __tablename__ = 'Chi_cang'

    # 表的结构:
    # index = Column(Integer, autoincrement=True, primary_key=True, nullable=False)
    tradingday = Column(String(8), primary_key=True, unique=False, nullable=False)
    productid = Column(String(5), primary_key=True, unique=False, nullable=False)
    one_t_five = Column(DECIMAL, nullable=False)
    six_t_twt = Column(DECIMAL, nullable=False)
    other = Column(DECIMAL, nullable=False)
    index_value=Column(DECIMAL, nullable=False)


def create_table():
    # 创建表
    Base.metadata.create_all(engine)


def drop_table():
    # 删除表
    session = DBSession()  # 创建会话
    session.execute('drop table if exists contract')
    session.commit()
    session.close()


def insert_table(tradingday, productid, one_t_five, six_t_twt, other):
    session = DBSession()
    row1 = Chi_cang(tradingday=tradingday,
                    productid=productid,
                    one_t_five=one_t_five,
                    six_t_twt=six_t_twt,
                    other=other,
                    index_value=0
                    )
    session.add(row1)
    session.commit()
    session.close()

def receipt_query(contract_id, tr_day):
    conn = psycopg2.connect(database="future", user="postgres", password="ck1/ck1@123456", host="81.68.204.178", port="6001")

    # 执行之后不报错，就表示连接成功了！
    # print('postgreSQL数据库“db_test”连接成功!')
    cursor=conn.cursor() ##通过cursor方法，对数据库进行操作
    query = "select * from receipt_select('{}', '{}')".format(contract_id, tr_day)
    cursor.execute(query)
    rows = cursor.fetchall()
    receipt_tb = pd.DataFrame(rows)
    receipt_tb.rename(columns={0:'tradingday', 1:'productid', 2:'exchange', 3:'company_sell', 4:'sell', 5:'company_buy', 6:'buy'},inplace=True)
    return receipt_tb


# timeline
def chi_c_r(contract_id, date):
    overall     = []
    one_to_five = []
    six_to_twe  = []
    other = []
    price = []

    df = receipt_query(re.match(r"[a-zA-Z]+", contract_id)[0], date)
    sell = df['sell'].to_list()
    buy = df['buy'].to_list()
    one_to_five.append(-sum(sell[0:5])+sum(buy[0:5]))
    six_to_twe.append(-sum(sell[5:])+sum(buy[5:]))
    other.append(sum(sell[:])-sum(buy[:]))
    overall.append(date)
    overall.append(one_to_five)
    overall.append(six_to_twe)
    overall.append(other)
    overall.append(price)
    return overall


id_list = ['ZN8888.SHF', 'CU8888.SHF', 'AG8888.SHF', 'AU8888.SHF', 'AL8888.SHF', 'I8888.DCE', 'RB8888.SHF',
           'M8888.DCE', 'Y8888.DCE', 'P8888.DCE', 'CF8888.CZC',
           'RU8888.SHF', 'FU8888.SHF', 'SP8888.SHF',
           'HC8888.SHF', 'NI8888.SHF', 'BU8888.SHF', 'SN8888.SHF',
           'SA8888.CZC', 'MA8888.CZC', 'OI8888.CZC',
           'FG8888.CZC', 'V8888.DCE', 'EG8888.DCE', 'PP8888.DCE',
           'PG8888.DCE', 'EB8888.DCE', 'L8888.DCE', 'JD8888.DCE',
           'RM8888.CZC', 'SR8888.CZC', 'AP8888.CZC', 'J8888.DCE',
           'JM8888.DCE', 'SM8888.CZC', 'SF8888.CZC']


def update_receipt():
    # 1. 创建 table 对象
    date = datetime.date.today()
    with open('d_store/update/update_receipt', 'r+', encoding='utf-8') as f:
        start = f.read()
        start = datetime.date(int(start[0:4]), int(start[5:7]), int(start[8:]))

    if start == date:
        print('数据库已更新')
    else:
        with open('d_store/update/update_receipt', 'r+', encoding='utf-8') as f:
            f.truncate()
            f.write(str(date))
        tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
        tool_trade_date_hist_sina_df = tool_trade_date_hist_sina_df[start <= tool_trade_date_hist_sina_df['trade_date']]
        tool_trade_date_hist_sina_df = tool_trade_date_hist_sina_df[date > tool_trade_date_hist_sina_df['trade_date']]
        if tool_trade_date_hist_sina_df.shape[0] == 0:
            print('数据库已更新')
        else:
            tr_date = tool_trade_date_hist_sina_df['trade_date'].apply(lambda x: x.strftime("%Y%m%d")).to_list()
            # with open('../d_store/update/update_receipt', 'r+', encoding='utf-8') as f:
            #     f.truncate()
            #     f.write(str(date))
            for i in id_list:
                for j in tr_date:
                    temp = chi_c_r(i, j)
                    insert_table(temp[0], re.match(r"[a-zA-Z]+", i)[0], temp[1][0], temp[2][0], temp[3][0])
                    print('successfully insert {} on {}'.format(i, j))
            print('数据库更新完毕')
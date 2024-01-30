import pandas as pd
from flask import Flask, request, render_template
import get_data
import Akshare_contract_update
import THS_chi_cang_rank_update
import akshare as ak
import get_data as gd
import datetime
import re

app = Flask(__name__, static_url_path='/', static_folder='templates')
app.config['JSON_AS_ASCII'] = False

# Variable:
# ---------------------- 这部分需要自己定义 -----------------------
base = './d_store/'

id_list = ['ZN8888.SHF', 'CU8888.SHF', 'AG8888.SHF', 'AU8888.SHF', 'AL8888.SHF', 'I8888.DCE', 'RB8888.SHF',
           'M8888.DCE', 'Y8888.DCE', 'P8888.DCE', 'CF8888.CZC',
           'RU8888.SHF', 'SC8888.SHF', 'FU8888.SHF', 'SP8888.SHF',
           'HC8888.SHF', 'NI8888.SHF', 'BU8888.SHF', 'SN8888.SHF',
           'SA8888.CZC', 'TA8888.CZC', 'MA8888.CZC', 'OI8888.CZC',
           'FG8888.CZC', 'V8888.DCE', 'EG8888.DCE', 'PP8888.DCE',
           'PG8888.DCE', 'EB8888.DCE', 'L8888.DCE', 'JD8888.DCE',
           'RM8888.CZC', 'SR8888.CZC', 'AP8888.CZC', 'J8888.DCE',
           'JM8888.DCE', 'SM8888.CZC', 'SF8888.CZC']
label_list = ['沪锌ZN', '铜CU', '沪银AG', '黄金AU', '沪铝AL', '铁矿I', '螺纹钢RB',
              '豆粕M', '豆油Y', '棕榈油P', '棉花CF',
              '橡胶RU', '原油SC', '燃油FU', '纸浆SP',
              '热卷HC', '沪镍NI', '沥青BU', '沪锡SN',
              '纯碱SA', 'PTA', '甲醇MA', '菜油OC',
              '玻璃FG', 'PVC', '乙二醇', '聚丙烯',
              'LPG', '苯乙烯', '塑料', '鸡蛋',
              '菜粕', '白糖', '苹果', '焦炭',
              '焦煤', '锰硅', '硅铁']
category_list = ['有色', '有色', '贵金属', '贵金属', '有色', '黑色', '黑色',
                 '农产品', '农产品', '农产品', '农产品',
                 '化工', '化工', '化工', '化工',
                 '黑色', '有色', '化工', '有色',
                 '化工', '化工', '化工', '农产品',
                 '化工', '化工', '化工', '化工',
                 '化工', '化工', '化工', '农产品',
                 '农产品', '农产品', '农产品', '黑色',
                 '黑色',  '黑色',  '黑色']
# -------------------------------------------------------------


# 1. get data:
df_list = []
download = gd.SQI_DB()
get_data.append_df(download, id_list, df_list)
stock_list = get_data.get_stock()
Akshare_contract_update.update_contract()
THS_chi_cang_rank_update.update_receipt()
# for i in range(len(df_list)):
#     df_list[i].to_csv('./d_store/'+id_list[i], index=False)

# for i in range(len(id_list)):
#     temp = pd.read_csv('./d_store/'+id_list[i])
#     df_list.append(temp)


# -------------------------------------------------------------
# 2. data percolator
def df_dump(df_l, id_l):
    # bubble_json = {}.fromkeys(['有色', '贵金属', '黑色', '农产品', '化工'])
    lis = []
    for i in range(len(id_l)):
        arr1 = df_l[i]['index_value'].to_list()
        arr2 = df_l[i]['index_value'].to_list()
        lis.append([get_data.price_quantile(arr1), get_data.price_quantile(get_data.volatility(arr2)), label_list[i],
                    category_list[i]])

    return lis


# 3. month dump
def month_dump(df, idl, cate, if_select, year):
    temp_df = []
    for j in range(len(idl)):
        imm = get_data.month_review(df[j], if_select, year)
        imm.append(idl[j])
        imm.append(cate[j])
        temp_df.append(imm)
    return temp_df


# 4. get_contract
contract_id_list = []
for i in range(len(id_list)):
    contract_id_list.append(id_list[i][:-8].lower())
contract_store = {}.fromkeys(contract_id_list, 0)


# print(df_list)
# print(df_dump(df_list, id_list))
@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('sidebar.html')


@app.route("/bubble", methods=['GET', 'POST'])
def bubble_input():
    return df_dump(df_list, id_list)


@app.route("/cor", methods=['GET', 'POST'])
def cor_input():
    cor_list = []
    typo = request.form.get('type')
    if typo is None:
        typo = 1
    return_list = get_data.cor(int(typo), category_list, df_list)
    for i in range(len(return_list)):
        cor_list.append(return_list[i].tolist())
    return cor_list


@app.route("/month", methods=['GET', 'POST'])
def month_reviewer():
    if request.method == 'POST':
        year = request.form.get('Year')
        print(year)
        mon_reviewer = month_dump(df_list, label_list, category_list, 1, int(year))
    else:
        mon_reviewer = month_dump(df_list, label_list, category_list, 0, 0)
    return mon_reviewer


@app.route("/contract", methods=['GET', 'POST'])
def contract():
    contract_id = request.form.get('id')

    contract_date = request.form.get('time')
    if contract_date == 'initial':
        today = datetime.date.today()
        hist = ak.tool_trade_date_hist_sina()
        contract_date = hist[today > hist['trade_date']]['trade_date'].apply(lambda x: x.strftime("%Y-%m-%d")).to_list()[-1]
        # print(contract_date)
    else:
        contract_date = datetime.datetime.strptime(contract_date, '%Y-%m-%d')
        contract_date = contract_date.strftime('%Y-%m-%d')

    if contract_store[contract_id] == 0:
        contract_data = get_data.get_contract(download, contract_id)
        valid = 0
    else:
        contract_data = contract_store[contract_id]
        valid = 1

    legend_list = []
    contract_closeprice = []
    contract_volume = []
    for my_id in contract_data.keys():
        if valid == 0:
            contract_data[my_id]['tradingday'] = contract_data[my_id]['tradingday'].apply(lambda x: str(x)[:4] + '-' + str(x)[4:6] + '-' + str(x)[6:8])
        if contract_data[my_id][contract_data[my_id]['tradingday'] == contract_date].shape[0] != 0:
            legend_list.append(my_id)
            contract_closeprice.\
                append(contract_data[my_id][contract_data[my_id]['tradingday'] == contract_date]['closeprice'].to_list()[0])
            contract_volume. \
                append(contract_data[my_id][contract_data[my_id]['tradingday'] == contract_date]['volume'].to_list()[0])

    return [legend_list, contract_closeprice, contract_volume]


@app.route("/receipt", methods=['GET', 'POST'])
def receipt():
    res = []
    if request.method == 'POST':
        receipt_id = request.form.get('id')
        # for i in id_list:
        #     if re.match(r"[a-zA-Z]+", i)[0].lower() == receipt_id:
        #         receipt_id = i
        # print(receipt_id)
        res = get_data.chi_c_get(receipt_id)
    return res


@app.route("/stock", methods=['GET', 'POST'])
def stock():
    return stock_list

if __name__ == '__main__':
    app.run(debug=False, port=3389)


























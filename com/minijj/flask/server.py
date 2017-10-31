# -*- coding: utf-8 -*-
import datetime
import time
import json
import hashlib

from flask import render_template
from flask import Flask
from flask import request
from flask import session
from form.settingForm import settingForm
from form.fastHigherForm import fastHigherForm
from form.fastLowerForm import fastLowerForm
import flask
import requests

from flask_login import (LoginManager, login_required, login_user,
                             logout_user, UserMixin)

import sys
import os
#parentpath = os.path.dirname(sys.path[0])

#print "#########parentpath=",parentpath
#sys.path.append(parentpath)

import core.constants as constants
from core.db import db
from core.db import rediscon

import core.api.okcoin_com_api as okcom
from core.api import bitmex_api
okcoin = okcom.OkCoinComApi(constants.coin_key, constants.coin_skey)
mex = bitmex_api.Bitmex(constants.mex_skey,constants.mex_key)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
redis = rediscon.Conn_db()
#okcoin = okcom.OkCoinComApi(constants.coin_key, constants.coin_skey)
#dif = diff.Diff(50,3600)

# user models
class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def is_authenticated(self):
        return True

    def is_actice(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


# flask-login
app.secret_key = 's3cr3t'
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    user = User(user_id)
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        m = hashlib.md5()
        str = request.form['password']
        m.update(str)
        if(m.hexdigest() == constants.password):
            user = User("minijj")
            login_user(user)
            return flask.redirect(flask.url_for('admin'))
        return render_template("login.html" ,name="密码错误!")
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return 'Logged out'

@app.route('/')
@login_required
def hello_world():
    return flask.redirect(flask.url_for('admin'))

@app.route('/chart')
@login_required
def chart():
    return render_template('chart.html')

@app.route('/admin')
@login_required
def admin():
    tradeserver = redis.get(constants.trade_server)

    #lstatus = requests.get(constants.http_server + "/lstatus/")
    #print lstatus

    main = redis.get(constants.lower_main_run_key)
    buy = redis.get(constants.lower_buy_run_key)
    sell = redis.get(constants.lower_sell_run_key)
    server = redis.get(constants.lower_server)

    main2 = redis.get(constants.higher_main_run_key)
    buy2 = redis.get(constants.higher_sell_run_key)
    sell2 = redis.get(constants.higher_buy_run_key)
    server2 = redis.get(constants.higher_server)

    ok_holding = okcoin.get_position(constants.higher_contract_type)
    if ok_holding and ok_holding.has_key('holding'):
        ok_holding = ok_holding['holding'][0]
    else:
        ok_holding = []
    # if ok_holding:
    #     ok_holding = ok_holding
    #ok_holding = []
    #print mex
    mex_holding = mex.get_position(constants.higher_mex_contract_type)
    #print mex_holding

    lowercreate = redis.get(constants.lower_basic_create_key)
    highercreate = redis.get(constants.higher_basic_create_key)
    orders = redis.get(constants.trade_his_key)
    orders.reverse()
    today = datetime.date.today()
    today = datetime.datetime.strptime(str(today), '%Y-%m-%d')
    todaycount = 0
    now = datetime.datetime.now() -datetime.timedelta(hours=24)
    count = 0
    for od in orders:
        if now < datetime.datetime.strptime(od[0],'%Y-%m-%d %H:%M:%S'):
            if od[4] < 0:
                count -= od[4]
        else:
            break
    for od in orders:
        if today < datetime.datetime.strptime(od[0],'%Y-%m-%d %H:%M:%S'):
            if od[4] < 0:
                todaycount -= od[4]
        else:
            break
    orders = orders[0:100]
    holdl = redis.get(constants.lower_split_position)
    holdh = redis.get(constants.higher_split_position)
    all = 0
    for ho in holdl:
        all += ho[0]
    for ho in holdh:
        all += ho[0]

    forml = fastLowerForm()
    forml.lower_max_size.data = redis.get(constants.lower_max_size_key)
    forml.lower_deal_amount.data = redis.get(constants.lower_deal_amount_key)
    forml.lower_expected_profit.data = redis.get(constants.lower_expected_profit_key)
    forml.lower_back_distant.data = redis.get(constants.lower_back_distant_key)
    forml.lower_basis_create.data = redis.get(constants.lower_basic_create_key)
    forml.lower_step_price.data = redis.get(constants.lower_step_price_key)

    formh = fastHigherForm()
    formh.higher_max_size.data = redis.get(constants.higher_max_size_key)
    formh.higher_deal_amount.data = redis.get(constants.higher_deal_amount_key)
    formh.higher_expected_profit.data = redis.get(constants.higher_expected_profit_key)
    formh.higher_back_distant.data = redis.get(constants.higher_back_distant_key)
    formh.higher_basis_create.data = redis.get(constants.higher_basic_create_key)
    formh.higher_step_price.data = redis.get(constants.higher_step_price_key)


    return render_template('admin2.html',forml=forml,formh=formh,ok_holding=ok_holding,mex_holding=mex_holding,tradeserver=str(tradeserver),main=str(main),buy=str(buy),sell=str(sell),server=str(server),main2=str(main2),buy2=str(buy2),sell2=str(sell2),server2=str(server2),all=all,holdh=holdh,holdl=holdl,orders=orders,lowercreate = lowercreate,highercreate=highercreate,sum=count,todaysum=todaycount)

@app.route('/mex')
@login_required
def mexdo():
    ac = request.args.get("action")
    count = request.args.get("count")
    prices = redis.get(constants.ok_mex_price)
    print "######count=",count
    print int(count)*100
    if "buy" == ac:
        print mex.buy(constants.higher_mex_contract_type,round((prices[1]+5),1),int(count) * 100)
    if "sell" == ac:
        print mex.sell(constants.higher_mex_contract_type,round((prices[2]-5),1),int(count) * 100)
    return "True"

@app.route('/liquid')
@login_required
def liquid():
    ac = request.args.get("action")
    count = request.args.get("count")
    #print count
    if "liquidh" == ac:
        okcoin.tradeRival(constants.higher_contract_type, int(count), 4)
        return "True"
    if "liquidl" == ac:
        okcoin.tradeRival(constants.lower_contract_type, int(count), 3)
        return "True"
    if "liquidhall" == ac:
        sp = redis.get(constants.higher_split_position)
        if sp:
            amount = 0
            for x in sp:
                amount += x[0]
            okcoin.tradeRival(constants.higher_contract_type, amount, 4)
        return "True"
    if "liquidlall" == ac:
        sp = redis.get(constants.higher_split_position)
        if sp:
            amount = 0
            for x in sp:
                amount += x[0]
            okcoin.tradeRival(constants.higher_contract_type, amount, 3)
        return "True"
    return "WTF"


@app.route('/fastlsetting' , methods=['POST'])
@login_required
def fastlsetting():
    form = fastLowerForm()
    constants.updatel(form)
    fm = {"lower_max_size": form.lower_max_size.data, "lower_deal_amount": form.lower_deal_amount.data,
          "lower_expected_profit": form.lower_expected_profit.data,
          "lower_back_distant": form.lower_back_distant.data, "lower_basis_create": form.lower_basis_create.data,
          "lower_step_price": form.lower_step_price.data}
    redis.set("fastforml",fm)
    requests.get(constants.http_server + "/lsetting/")
    return flask.redirect(flask.url_for('admin'))

@app.route('/fasthsetting' , methods=['POST'])
@login_required
def fasthsetting():
    form = fastHigherForm()
    constants.updateh(form)
    fm = {"higher_max_size":form.higher_max_size.data,"higher_deal_amount":form.higher_deal_amount.data,"higher_expected_profit":form.higher_expected_profit.data,"higher_back_distant":form.higher_back_distant.data,"higher_basis_create":form.higher_basis_create.data,"higher_step_price":form.higher_step_price.data}
    redis.set("fastformh", fm)
    requests.get(constants.http_server + "/hsetting/")
    return flask.redirect(flask.url_for('admin'))

@app.route('/setting' , methods=['GET', 'POST'])
@login_required
def setting():
    #execfile
    #import os
    #os.system("python filename")
    #--注：filename最好是全路径 + 文件名，python在环境变量中（linux就没这个问题了）
    #http://www.cnblogs.com/bergus/p/4811291.html
    form = settingForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            position = form.lower_split_position.data
            if(position.strip() !=""):
                lsplit_position = eval(position)
                lsplit_position.sort(key=lambda x: x[1])
                lsplit_position.reverse()
                redis.set(constants.lower_split_position,lsplit_position)
            else:
                redis.set(constants.lower_split_position, [])
            position = form.higher_split_position.data
            if (position.strip() != ""):
                hsplit_position = eval(position)
                hsplit_position.sort(key=lambda x: x[1])
                redis.set(constants.higher_split_position, hsplit_position)
            else:
                redis.set(constants.lower_split_position, [])
            redis.set(constants.higher_basic_create_key, form.higher_basis_create.data)
            redis.set(constants.lower_basic_create_key, form.lower_basis_create.data)
            constants.update(form)
            #os.system('ls -l *')
        else:
            print "##########wtf"
        return render_template('setting.html',form=form)
    else:
        config = constants.getCfg()
        form.lower_max_size.data = config.get("all","lower_max_size")
        form.lower_deal_amount.data = config.get("all","lower_deal_amount")
        form.lower_expected_profit.data = config.get("all","lower_expected_profit")
        form.lower_back_distant.data = config.get("all", "lower_back_distant")
        form.lower_basis_create.data = redis.get(constants.lower_basic_create_key)
        form.lower_split_position.data = redis.get(constants.lower_split_position)
        form.lower_step_price.data = config.get("all","lower_step_price")
        form.lower_contract_type.data = config.get("all","lower_contract_type")
        form.lower_mex_contract_type.data = config.get("all","lower_mex_contract_type")
        form.higher_max_size.data = config.get("all","higher_max_size")
        form.higher_deal_amount.data = config.get("all","higher_deal_amount")
        form.higher_expected_profit.data = config.get("all","higher_expected_profit")
        form.higher_back_distant.data = config.get("all", "higher_back_distant")
        form.higher_basis_create.data = redis.get(constants.higher_basic_create_key)
        form.higher_split_position.data = redis.get(constants.higher_split_position)
        form.higher_step_price.data = config.get("all","higher_step_price")#redis.get(higher_basic_create_key)
        form.higher_contract_type.data = config.get("all","higher_contract_type")
        form.higher_mex_contract_type.data = config.get("all","higher_mex_contract_type")
        return render_template('setting.html',form=form)
    return render_template('setting.html',)
@app.route('/threadctl/<thread>')
@login_required
def threadctl(thread):
    key = True
    if "trade" == thread:
        key = redis.get(constants.trade_server)
        if key:
            redis.set(constants.trade_server,False)
        else:
            os.system('nohup python core/ok_mex.py &')

    if "buy" == thread:
        key = redis.get(constants.lower_buy_run_key)
        requests.get(constants.http_server + "/lopen/")
    if "sell" == thread:
        key = redis.get(constants.lower_sell_run_key)
        requests.get(constants.http_server + "/lliquid/")

    if "buy2" == thread:
        key = redis.get(constants.higher_sell_run_key)
        requests.get(constants.http_server + "/hliquid/")
    if "sell2" == thread:
        key = redis.get(constants.higher_buy_run_key)
        requests.get(constants.http_server + "/hopen/")

    if "server" == thread:
        key = redis.get(constants.lower_server)
        # if not key:
        #     redis.set(constants.command_h_server, key)#开lserver 一定要关 hserver
        # redis.set(constants.command_l_server, not key)
        requests.get(constants.http_server+"/lserver/")


    if "server2" == thread:
        key = redis.get(constants.higher_server)
        # if not key:
        #     redis.set(constants.command_l_server, key) #开hserver 一定要关 lserver
        # redis.set(constants.command_h_server, not key)
        requests.get(constants.http_server + "/hserver/")

    if "strategy" == thread:
        key = redis.get(constants.strategy_on_key)
        redis.set(constants.strategy_on_key,not key)

    return str(not key)

@app.route('/strategy' , methods=['GET', 'POST'])
@login_required
def strategy():
    if request.method == 'POST':
        strategyh = float(request.values.get("edgeup"))
        strategyl = float(request.values.get("edgedown"))

        redis.set(constants.strategy_higher_key,strategyh)
        redis.set(constants.strategy_lower_key, strategyl)
    else:
        pass
    strategyon = redis.get(constants.strategy_on_key)
    strategyh = redis.get(constants.strategy_higher_key)
    strategyl = redis.get(constants.strategy_lower_key)
    return render_template('strategy.html', strategyon = str(strategyon),strategyh = strategyh,strategyl = strategyl)

@app.route('/recentall/')
def recentall():
    oklist = redis.get('recent')
    size = len(oklist) - 1
    rs = []
    for i in range(0, size, 1):
        el = (oklist[i][0]+datetime.timedelta(hours=8), oklist[i][1],oklist[i][2])
        rs.append(el)
    return json.dumps(rs, cls=CJsonEncoder)

@app.route('/recent10m/')
def recent10min():
    oklist = redis.get('recent')
    size = len(oklist) - 1
    rs = []
    start = size - 600 if size - 600 > 0 else 0
    for i in range(start, size, 1):
        el = (oklist[i][0]+datetime.timedelta(hours=8), round(oklist[i][2] - oklist[i][1], 2))
        rs.append(el)
    return json.dumps(rs, cls=CJsonEncoder)

@app.route('/recent210m/')
def recent210min():
    oklist = redis.get('recent2')
    size = len(oklist) - 1
    rs = []
    start = size - 600 if size - 600 > 0 else 0
    for i in range(start, size, 1):
        el = (oklist[i][0]+datetime.timedelta(hours=8), round(oklist[i][3] - oklist[i][2], 2))
        rs.append(el)
    return json.dumps(rs, cls=CJsonEncoder)

@app.route('/recent30m/')
def recent5m():
    oklist = redis.get('list')
    size = len(oklist)-1
    rs = []
    start = size-360 if size-360 > 0 else 0
    for i in range(start,size,1):
        el = (oklist[i][0]+ datetime.timedelta(hours=8),round(oklist[i][2]-oklist[i][1],2))
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)

@app.route('/recent1h/')
def recent1h():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("select margin,update_time from bit_1min_margin order by trading_time desc limit 60")
    list = cursor.fetchall()
    cursor.close()
    conn.close()
    rs = []
    for i in range(len(list)-1,-1,-1):
        el = (list[i][1],list[i][0])
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)


@app.route('/recent4h/')
def recent4h():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("select margin,update_time from bit_1min_margin order by trading_time desc limit 240")
    list = cursor.fetchall()
    cursor.close()
    conn.close()
    rs = []
    for i in range(len(list) - 1, -1, -1):
        el = (list[i][1],list[i][0])
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)

@app.route('/recent1d/')
def recent1d():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("select margin,update_time from bit_5min_margin order by trading_time desc limit 288")
    list = cursor.fetchall()
    cursor.close()
    conn.close()
    rs = []
    for i in range(len(list) - 1, -1, -1):
        el = (list[i][1],list[i][0])
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)

@app.route('/recent3d/')
def recent3d():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("select margin,update_time from bit_15min_margin order by trading_time desc limit 288")
    list = cursor.fetchall()
    cursor.close()
    conn.close()
    rs = []
    for i in range(len(list) - 1, -1, -1):
        el = (list[i][1],list[i][0])
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)

@app.route('/recent7d/')
def recent7d():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("select margin,update_time from bit_30min_margin order by trading_time desc limit 336")
    list = cursor.fetchall()
    cursor.close()
    conn.close()
    rs = []
    for i in range(len(list) - 1, -1, -1):
        el = (list[i][1],list[i][0])
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)

@app.route('/recent30d/')
def recent30d():
    conn = db.getconn()
    cursor = conn.cursor()
    cursor.execute("select margin,update_time from bit_30min_margin order by trading_time desc limit 1000")
    list = cursor.fetchall()
    cursor.close()
    conn.close()
    rs = []
    for i in range(len(list) - 1, -1, -1):
        el = (list[i][1],list[i][0])
        rs.append(el)
    return json.dumps(rs,cls=CJsonEncoder)

class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return json.JSONEncoder.default(self, obj)

@app.template_filter('sub')
def sub(l, start, end):
    return l[start:end]
if __name__ == '__main__':
    #dif.run()
    from werkzeug.contrib.fixers import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run(host='172.31.91.40', port=80)

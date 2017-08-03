# -*- coding: utf-8 -*-
import datetime
import time
import json

from flask import render_template
from flask import Flask
from flask import request
from flask import session
from form.settingForm import settingForm
import flask

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
        if(request.form['password'] == "minijj"):
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
    main = redis.get(constants.lower_main_run_key)
    buy = redis.get(constants.lower_buy_run_key)
    sell = redis.get(constants.lower_sell_run_key)
    server = redis.get(constants.lower_server)

    main2 = redis.get(constants.higher_main_run_key)
    buy2 = redis.get(constants.higher_buy_run_key)
    sell2 = redis.get(constants.higher_sell_run_key)
    server2 = redis.get(constants.higher_server)


    lowercreate = redis.get(constants.lower_basic_create_key)
    highercreate = redis.get(constants.higher_basic_create_key)
    orders = redis.get(constants.trade_his_key)
    orders.reverse()
    now = datetime.datetime.now() -datetime.timedelta(hours=24)
    count = 0
    for od in orders:
        if now < datetime.datetime.strptime(od[0],'%Y-%m-%d %H:%M:%S'):
            if od[4] < 0:
                count -= od[4]
        else:
            break
    orders = orders[0:30]
    return render_template('admin.html',main=str(main),buy=str(buy),sell=str(sell),server=str(server),main2=str(main2),buy2=str(buy2),sell2=str(sell2),server2=str(server2),holdh=redis.get(constants.coin_skey + 'higher'),holdl=redis.get(constants.coin_skey + 'lower'),orders=orders,lowercreate = lowercreate,highercreate=highercreate,sum=count)

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
            constants.update(form)
            print "############aaa"
            print constants.lower_basis_create
            #os.system('ls -l *')
        else:
            print "##########wtf"
        return render_template('setting.html',form=form)
    else:
        config = constants.getCfg()
        form.lower_max_size.data = config.get("all","lower_max_size")
        form.lower_deal_amount.data = config.get("all","lower_deal_amount")
        form.lower_expected_profit.data = config.get("all","lower_expected_profit")
        form.lower_basis_create.data = redis.get(constants.lower_basic_create_key)
        form.lower_step_price.data = config.get("all","lower_step_price")
        form.lower_contract_type.data = config.get("all","lower_contract_type")
        form.lower_mex_contract_type.data = config.get("all","lower_mex_contract_type")
        form.higher_max_size.data = config.get("all","higher_max_size")
        form.higher_deal_amount.data = config.get("all","higher_deal_amount")
        form.higher_expected_profit.data = config.get("all","higher_expected_profit")
        form.higher_basis_create.data = config.get("all","higher_basis_create")
        form.higher_step_price.data = config.get("all","higher_step_price")#redis.get(higher_basic_create_key)
        form.higher_contract_type.data = config.get("all","higher_contract_type")
        form.higher_mex_contract_type.data = config.get("all","higher_mex_contract_type")
        return render_template('setting.html',form=form)
    return render_template('setting.html',)
@app.route('/threadctl/<thread>')
@login_required
def threadctl(thread):
    if "main" == thread:
        key = redis.get(constants.lower_main_run_key)
        redis.set(constants.lower_main_run_key,not key)
        return str(not key)
    if "buy" == thread:
        key = redis.get(constants.lower_buy_run_key)
        redis.set(constants.lower_buy_run_key,not key)
        return str(not key)
    if "sell" == thread:
        key = redis.get(constants.lower_sell_run_key)
        redis.set(constants.lower_sell_run_key,not key)
        return str(not key)
    if "main2" == thread:
        key = redis.get(constants.higher_main_run_key)
        redis.set(constants.higher_main_run_key,not key)
        return str(not key)
    if "buy2" == thread:
        key = redis.get(constants.higher_buy_run_key)
        redis.set(constants.higher_buy_run_key,not key)
        return str(not key)
    if "sell2" == thread:
        key = redis.get(constants.higher_sell_run_key)
        redis.set(constants.higher_sell_run_key,not key)
        return str(not key)

    if "server" == thread:
        key = redis.get(constants.lower_server)
        if key:
            redis.set(constants.lowerer_server, False)
            return str(False)
        else:
            os.system('nohup python core/ok_lower.py &')
            return str(True)
    if "server2" == thread:
        key = redis.get(constants.higher_server)
        if key:
            redis.set(constants.higher_server, False)
            return str(False)
        else:
            os.system('nohup python core/ok_higher.py &')
            return str(True)


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

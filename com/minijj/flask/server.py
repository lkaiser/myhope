# -*- coding: utf-8 -*-
import datetime
import time
import json

from flask import render_template
from flask import Flask
from flask import request
from flask import session
import flask

from flask_login import (LoginManager, login_required, login_user,
                             logout_user, UserMixin)

import sys
import os
parentpath = os.path.dirname(sys.path[0])

print "#########parentpath=",parentpath
sys.path.append(parentpath)

import bit.constants as constants
from bit.db import db
from bit.db import rediscon



app = Flask(__name__)
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
    return render_template('index.html')

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
    lowercreate = redis.get(constants.lower_basic_create_key)
    orders = redis.get(constants.trade_his_key)
    orders.reverse()
    now = datetime.datetime.now() -datetime.timedelta(hours=24)
    count = 0
    for od in orders:
        if now < datetime.datetime.strptime(od[0],'%Y-%m-%d %H:%M:%S'):
            if od[4] < 0:
                count +=1
        else:
            break
    orders = orders[0:30]
    print constants.trade_his_key
    print orders
    return render_template('admin.html',main=str(main),buy=str(buy),sell=str(sell),holdh=redis.get(constants.coin_skey + 'higher'),holdl=redis.get(constants.coin_skey + 'lower'),orders=orders,lowercreate = lowercreate,sum=count)

@app.route('/setting')
@login_required
def setting():
    #execfile
    #import os
    #os.system("python filename")
    #--注：filename最好是全路径 + 文件名，python在环境变量中（linux就没这个问题了）
    #http://www.cnblogs.com/bergus/p/4811291.html
    return render_template('setting.html')

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

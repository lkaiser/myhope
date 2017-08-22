# -*- coding: utf-8 -*-
import sys
import os
import datetime
import threading
import time
#print sys.path

parentpath = os.path.dirname(sys.path[0])
print sys.path[0]
print parentpath
#sys.path.append(parentpath)

import logging.handlers
LOG_FILE = 'test.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 1024*1024*4, backupCount = 10) # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('tst')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)

import core.constants as constants
from core.db import db
from core.db import rediscon
redis = rediscon.Conn_db()
print type(constants.coin_key)

a = []
a.append("a")
a.append("b")
a.append("c")

b = redis.get(constants.trade_his_key)
b.reverse()
logger.info("##############python 调用 test##########")
c = datetime.date.today()
d = datetime.datetime.strptime(str(c),'%Y-%m-%d')
print d
now = datetime.datetime.now() -datetime.timedelta(hours=24)
print now
if now< datetime.datetime.now():
    print True
print b[0:30]

a = 8.5
b = None

redis.set(constants.lower_server,False)
redis.set(constants.lower_server,0)
redis.delete(constants.lower_server)
rs = redis.get(constants.lower_server)
print isinstance(rs,bool)

def tes(pa=None):
    if pa:
        print pa
    else:
        print "no pa"


tes("ha")
tes()

def event1(event):
    event.clear()
    print "event1 要卡住咯"
    event.wait()
    print "event1 活过来了"

def event2(event):
    event.clear()
    print "event2 要卡住咯"
    event.wait()
    print "event2 活过来了"

event = threading.Event()

pm = threading.Thread(target=event1,args=(event,))
pm.setDaemon(True)
pm.start()

time.sleep(2)

pm2 = threading.Thread(target=event2,args=(event,))
pm2.setDaemon(True)
pm2.start()

while 1:
    print "我是主进程"
    time.sleep(5)
    print "你们谁卡住了，我来释放你们"
    event.set()
    print "孩儿们，玩去吧"
    time.sleep(10)
    break


#print a + b
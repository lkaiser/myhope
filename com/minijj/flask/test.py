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
from core.api import bitmex_api
mex = bitmex_api.Bitmex("vXainyeMrILyP0v3yiDHolLseGDr5XyqWLAiGhDn00pQytWY","iJ0GlU97wuife_k3uAV2zxy_")

#print mex.buy('XBTU17',round(3760.233,1),int(2) * 100)
print mex.sell('XBTU17',round(3730.155,1),int(2) * 100)

#print round(3780,2)

#print a + b
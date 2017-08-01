import sys
import os
import datetime
#print sys.path

parentpath = os.path.dirname(sys.path[0])
sys.path.append(parentpath)

import core.constants as constants
from core.db import db
from core.db import rediscon
redis = rediscon.Conn_db()
print type(constants.coin_key)
print type("xxqqq")

a = []
a.append("a")
a.append("b")
a.append("c")

b = redis.get(constants.trade_his_key)
b.reverse()

now = datetime.datetime.now() -datetime.timedelta(hours=24)
print now
if now< datetime.datetime.now():
    print True
print b[0:30]
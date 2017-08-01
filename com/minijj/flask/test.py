import sys
import os

#print sys.path

parentpath = os.path.dirname(sys.path[0])
sys.path.append(parentpath)

import bit.constants as constants
from bit.db import db
from bit.db import rediscon
redis = rediscon.Conn_db()
print type(constants.coin_key)
print type("xxqqq")

a = []
a.append("a")
a.append("b")
a.append("c")

b = redis.get(constants.trade_his_key)
b.reverse()
print b[0:30]
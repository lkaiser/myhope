# coding=utf-8
import datetime
import logging.handlers

import Queue
import threading
from db import rediscon
import time
import constants as constants
import api.okcoin_com_api as okcom
from api import bitmex_api

import sys

import ConfigParser
import hashlib

LOG_FILE = 'test.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 1024*1024, backupCount = 5) # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('tst')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)

config = ConfigParser.ConfigParser()

class mexliquidation(object):
    def __init__(self):
        self.buyqueue = Queue.Queue(10)
        config.readfp(open('constants.ini'))
        a = config.get("all", "lower_sell_run_key")
        print a

    def liquidBuy(self):
        while(1):
            try:
                #print "what the fuck"
                #self.buyqueue.put("fuck")
                order = self.buyqueue.get()
                while(1):
                    #print self.price+slipp
                    try:
                       print "############queue 里拿的啥啊",order
                       time.sleep(3)
                       break
                    except Exception, e:
                        logger.info(e)
                    finally:
                        pass
            except Exception, e:
                logger.info("########what the fuck error############")
                logger.info(e)
                pass

    def changeQueue(self):
        while(1):
            input_s = raw_input("Input Mode\n")
            self.buyqueue.put(input_s)


    def start(self):
        # self.server.test()
        buy = threading.Thread(target=self.liquidBuy)
        buy.setDaemon(True)
        buy.start()

        sell = threading.Thread(target=self.changeQueue)
        sell.setDaemon(True)
        sell.start()


if __name__ == '__main__':
   #m = mexliquidation()
   # m.start()
   # while 1:
   #    pass
   starttime = datetime.datetime.now()
   # long running
   time.sleep(0.3)
   endtime = datetime.datetime.now()
   print round(300000/1000000.0,2)



   # print True
   # print datetime.datetime.utcnow()
   # timenow = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))
   # print timenow
   #
   # redis = rediscon.Conn_db()
   # #skey = constants.coin_skey
   # ps = redis.get(constants.lower_split_position)
   # amount = 0
   # for x in ps:
   #     amount += x[0]
   # print "############amount=",amount
   #okcoin = okcom.OkCoinComApi(constants.coin_key, constants.coin_skey)
   # print "########here"
   #print okcoin.get_userinfo()

   #mex = bitmex_api.Bitmex(constants.mex_skey,constants.mex_key)
   #mexall = mex.get_userCommission()
   #print "#########mex info"
   #print mexall

   # print 4091.849-4099.22 <= -100
   #
   # tradehis = []
   # tradehis.append((datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S'),15,"20",2+5-3))
   # tradehis.append((datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S'), 25, "50",1+7-2))
   #redis.set("tradehis",tradehis)
   #print redis.get("tradehis")

   # config = ConfigParser.ConfigParser()
   # config.readfp(open('constants.ini'))
   # a = config.get("all", "lower_sell_run_key")
   #
   # config.read('constants.ini')
   # config.set("all", "author", "fredrik aaaaa")
   # config.write(open('constants.ini', "r+"))
   #print a
   #test3.printcfg()

   # print "@@@@@@@@@2"
   # print bytes(constants.higher_back_distant)
   #
   # print sys.path

   str = "[(2, -27), (2, -26.652), (2, -26), (2, -24.558), (2, -22.749), (2, -21.996), (2, -20.78), (2, -20.73), (1, -18.486), (2, -17.708), (2, -15.421)]"
   b = eval(str)
   b.reverse()
   print b
   print type(b[0])

   # print redis.get("fastforml")
   # redis.delete("fastforml")
   # print "###########wft",redis.get("fastforml")


   m = hashlib.md5()
   str = "lulu"
   m.update(str)
   print m.hexdigest()

   #print constants.const.PI

   a = '{"op": "subscribe", "args": ["orderBook10:'+'haha'+'"]}'
   print a

   #logger.info("################ammout 增加了 " + bytes(0) + "，持仓变化如下 #######################")

    #print "################",mex2.position("XBTM17")


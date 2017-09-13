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



   print True
   print datetime.datetime.utcnow()
   timenow = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))
   print timenow

   redis = rediscon.Conn_db()
   #skey = constants.coin_skey
   ps = redis.get(constants.lower_split_position)
   amount = 0
   for x in ps:
       amount += x[0]
   print "############amount=",amount
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

   # str = "[(2, -27), (2, -26.652), (2, -26), (2, -24.558), (2, -22.749), (2, -21.996), (2, -20.78), (2, -20.73), (1, -18.486), (2, -17.708), (2, -15.421)]"
   # b = eval(str)
   # b.reverse()
   # print b
   # print type(b[0])

   # print redis.get("fastforml")
   # redis.delete("fastforml")
   # print "###########wft",redis.get("fastforml")


   m = hashlib.md5()
   strs = "lulu"
   m.update(strs)
   print m.hexdigest()

   t = [0,0,0]
   t[0] = 5
   t[2] = 1
   print t
   print sum(t)

   ls = ["1", "2", "3"]
   print ','.join(ls)

   openorders = {9428634258: [{u'status': -1, u'contract_name': u'BTC0929', u'fee': 0, u'create_date': 1504501912000, u'order_id': 9428634258, u'price': 4501.57, u'amount': 20, u'unit_amount': 100, u'price_avg': 0, u'lever_rate': 10, u'type': 2, u'symbol': u'btc_usd', u'deal_amount': 0}, 4.5, 1], 9428634275: [{u'status': -1, u'contract_name': u'BTC0929', u'fee': 0, u'create_date': 1504501912000, u'order_id': 9428634275, u'price': 4514.07, u'amount': 10, u'unit_amount': 100, u'price_avg': 0, u'lever_rate': 10, u'type': 2, u'symbol': u'btc_usd', u'deal_amount': 0}, 7.5, 2], 9428634246: [{u'status': -1, u'contract_name': u'BTC0929', u'fee': 0, u'create_date': 1504501912000, u'order_id': 9428634246, u'price': 4489.07, u'amount': 10, u'unit_amount': 100, u'price_avg': 0, u'lever_rate': 10, u'type': 2, u'symbol': u'btc_usd', u'deal_amount': 0}, 1.5, 0]}
   open_his = {}
   for order in openorders.values():
       if order[0]['status'] == 2 or order[0]['status'] == -1:
           remove = False
           if not open_his.has_key(order[0]['order_id']) and order[0]['deal_amount'] == 0:  # ,没有，且deal_amount=0 可删
               remove = True
           if remove or openorders[order[0]['order_id']]['deal_amount'] == open_his[order[0]['order_id']]:  # 一致，说明已经记录，可以删除了
               del openorders[order[0]['order_id']]
               if not remove:
                    del open_his[order[0]['order_id']]



   #print constants.const.PI

   #logger.info("################ammout 增加了 " + bytes(0) + "，持仓变化如下 #######################")

    #print "################",mex2.position("XBTM17")


# -*- coding: utf-8 -*-
import Queue
import json
import logging.handlers
import sys
import threading
import time
import datetime
import inspect
import ctypes

import websocket
from retrying import retry
import constants as constants
import api.okcoin_com_api as okcom
from mexliquidation2 import mexliquidation
import marketPrice
from ok_higher2 import OkHigher
from ok_lower2 import OkLower
from holdposition import HoldPostion
from api import bitmex_api
from db.rediscon import Conn_db
from market_maker import bitmex
from httpserver import TradeHTTPServer,MyHandler

import sys
import os

# parentpath = os.path.dirname(sys.path[0])

LOG_FILE = sys.path[0] + '/trade.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024 * 8, backupCount=20)  # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('root')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)


class TradeMexAndOk(object):
    def __init__(self):
        key = constants.coin_key
        skey = constants.coin_skey

        mex_key = constants.mex_key
        mex_skey = constants.mex_skey

        self.redis = Conn_db()
        self.redis.set(constants.trade_server, True)
        self.status = True

        self.mex = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',symbol=constants.higher_mex_contract_type, apiKey=mex_key, apiSecret=mex_skey)
        self.contract_type = constants.higher_contract_type
        self.okcoin = okcom.OkCoinComApi(key, skey)
        self.okcoin.cancel_all(self.contract_type)
        self._mex = bitmex_api.Bitmex(mex_skey, mex_key)
        self.marketPrice = marketPrice.MarketPrice(self.okcoin)
        self.mexliquidation = mexliquidation(self.mex)
        self.OkHigher = OkHigher(
            self.okcoin, self.mex, self._mex, self.marketPrice, constants.higher_contract_type,
            constants.higher_max_size, constants.higher_deal_amount, constants.higher_expected_profit,
            constants.higher_basis_create, constants.higher_back_distant, constants.higher_step_price)

        self.OkLower = OkLower(
            self.okcoin, self.mex, self._mex, self.marketPrice, constants.lower_contract_type,
            constants.lower_max_size, constants.lower_deal_amount, constants.lower_expected_profit,
            constants.lower_basis_create, constants.lower_back_distant, constants.lower_step_price)

        self.mexliquidation.setServers(self.OkHigher,self.OkLower)
        self.position = HoldPostion(self.okcoin,self.marketPrice,self.mexliquidation,self.OkHigher,self.OkLower)
        self.httpd = None
        # sys.exit(0)

    def setting_check(self):
        while 1:
            try:
                time.sleep(1)
                hserver = self.redis.get(constants.command_h_server)
                lserver = self.redis.get(constants.command_l_server)

                if isinstance(hserver, bool):
                    logger.info("#########higher command "+str(hserver))
                    if hserver:
                        self.startHserver()
                    else:
                        self.stopHserver()
                    self.redis.delete(constants.command_h_server)

                if isinstance(lserver, bool):
                    logger.info("#########lower command " + str(lserver))
                    if lserver:
                        self.startLserver()
                    else:
                        self.stopLserver()
                    self.redis.delete(constants.command_l_server)

                if self.redis.get(constants.strategy_on_key):
                    prices = self.redis.get(constants.ok_mex_price)
                    high = self.redis.get(constants.strategy_higher_key)
                    low = self.redis.get(constants.strategy_lower_key)

                    if prices[4] - prices[1] - low < 15:
                        t.stopOpenH()
                    else:
                        t.remainOpenH()

                    if high - (prices[3]-prices[2]) <15:
                        t.stopOpenL()
                    else:
                        t.remainOpenL()

                    if (prices[4] - prices[1]) >= high:
                        logger.info("#########high strategy acitve prices[4] = "+bytes(prices[4])+" prices[1] = "+bytes(prices[1]) +" high = "+bytes(high))
                        #t.liquidL()
                        t.startHserver()
                    if (prices[3] - prices[2]) <= low:
                        logger.info("#########low strategy acitve prices[3] = " + bytes(prices[3]) + " prices[2] = " + bytes(prices[2]) + " low = " + bytes(low))
                        #t.liquidH()
                        t.startLserver()
            except:
                pass

    def initcfg(self):
        self.redis.set(constants.strategy_on_key,False)
        self.redis.set(constants.strategy_higher_key, 0)
        self.redis.set(constants.strategy_lower_key, 0)

        self.redis.set(constants.higher_server,False)
        self.redis.set(constants.lower_server, False)

    def upStatu(self):
        self.status = self.redis.get(constants.trade_server)
        return self.status

    def startHttp(self):
        serveaddr = ('127.0.0.1', 8000)
        self.httpd = TradeHTTPServer(serveaddr, MyHandler)
        self.httpd.setTrade(self)
        print "Base serve is start add is %s port is %d" % (serveaddr[0], serveaddr[1])
        self.httpd.serve_forever()

    def start(self):
        self.initcfg()
        self.marketPrice.start()
        self.mexliquidation.start()

        self.position.start()

        check = threading.Thread(target=self.setting_check)
        check.setDaemon(True)
        check.start()

        print "I'm starting postion now"
        http = threading.Thread(target=self.startHttp)
        http.setDaemon(True)
        http.start()

    def stop(self):
        self.OkHigher.stop()
        self.OkLower.stop()
        self.httpd.shutdown()

    def switchHserver(self):
        rs = self.redis.get(constants.higher_server)
        if rs:
            self.stopHserver()
        else:
            self.startHserver()

    def stopOpenH(self):
        self.OkHigher.stopOpen()

    def remainOpenH(self):
        self.OkHigher.remainOpen()

    def stopOpenL(self):
        self.OkLower.stopOpen()

    def remainOpenL(self):
        self.OkLower.remainOpen()

    def switchLserver(self):
        rs = self.redis.get(constants.lower_server)
        if rs:
            self.stopLserver()
        else:
            self.startLserver()

    def startHserver(self,basis=None):
        self.OkLower.stop()
        self.OkHigher.start(basis)
        self.redis.set(constants.higher_server, True)
        self.redis.set(constants.lower_server, False)

    def stopHserver(self):
        self.OkHigher.stop()
        self.redis.set(constants.higher_server, False)

    def startLserver(self,basis=None):
        self.OkHigher.stop()
        self.OkLower.start(basis)
        self.redis.set(constants.lower_server, True)
        self.redis.set(constants.higher_server, False)

    def stopLserver(self):
        self.OkLower.stop()
        self.redis.set(constants.lower_server, False)

    def switchHOpen(self):
        if self.redis.get(constants.higher_buy_run_key):
            self.OkHigher.stopOpen()
        else:
            self.OkHigher.remainOpen()

    def switchHLiquid(self):
        if self.redis.get(constants.higher_sell_run_key):
            self.OkHigher.stopLiquid()
        else:
            self.OkHigher.remainLiquid()

    def switchLOpen(self):
        if self.redis.get(constants.lower_buy_run_key):
            self.OkLower.stopOpen()
        else:
            self.OkLower.remainOpen()

    def switchLLiquid(self):
        if self.redis.get(constants.lower_sell_run_key):
            self.OkLower.stopLiquid()
        else:
            self.OkLower.remainLiquid()

    def hsetting(self):
        self.OkHigher.setting_check()

    def lsetting(self):
        self.OkLower.setting_check()

    def liquidH(self):
        self.OkHigher.liquidAll()

    def liquidL(self):
        self.OkLower.liquidAll()

    def cancel_all(self):
        self.okcoin.cancel_all(self.contract_type)

    def hstatu(self):
        return [self.OkHigher.event.isSet(),self.OkHigher.openevent.isSet(),self.OkHigher.liquidevent.isSet(),self.OkHigher.waitevent.isSet()]

    def lstatu(self):
        return [self.OkLower.event.isSet(),self.OkLower.openevent.isSet(),self.OkLower.liquidevent.isSet(),self.OkLower.waitevent.isSet()]


t = TradeMexAndOk()
t.start()


while t.upStatu():
    time.sleep(2)
    pass
t.stop()
logger.info("###I'm quit###########")
t.cancel_all()
sys.exit(0)

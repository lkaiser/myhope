# -*- coding: utf-8 -*-
import Queue
import json
import logging.handlers
import sys
import threading
import time
import datetime

import websocket
from retrying import retry
import constants as constants
import api.okcoin_com_api as okcom
from mexliquidation2 import mexliquidation
import marketPrice
from ok_higher2 import OkHigher
from ok_lower2 import OkLower
from api import bitmex_api
from db.rediscon import Conn_db
from market_maker import bitmex

import sys
import os

# parentpath = os.path.dirname(sys.path[0])

LOG_FILE = sys.path[0] + '/trade.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024 * 4, backupCount=10)  # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('tst')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)


class TradeMexAndOk(object):
    def __init__(self):
        key = constants.coin_key
        skey = constants.coin_skey

        mex_key = constants.mex_key
        mex_skey = constants.mex_skey
        self.mex = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',symbol=constants.higher_mex_contract_type, apiKey=mex_key, apiSecret=mex_skey)
        self.contract_type = constants.higher_contract_type
        self.okcoin = okcom.OkCoinComApi(key, skey)
        self.okcoin.cancel_all(self.contract_type)
        self._mex = bitmex_api.Bitmex(mex_skey, mex_key)
        self.marketPrice = marketPrice.MarketPrice(self.okcoin)
        self.mexliquidation = mexliquidation(self.mex)
        self.OkHigher = OkHigher(
            self.okcoin, self.mex, self._mex, self.marketPrice,self.mexliquidation, constants.higher_contract_type,
            constants.higher_max_size, constants.higher_deal_amount, constants.higher_expected_profit,
            constants.higher_basis_create, constants.higher_back_distant, constants.higher_step_price)

        self.OkLower = OkLower(
            self.okcoin, self.mex, self._mex, self.marketPrice, self.mexliquidation, constants.lower_contract_type,
            constants.lower_max_size, constants.lower_deal_amount, constants.lower_expected_profit,
            constants.lower_basis_create, constants.lower_back_distant, constants.lower_step_price)

        self.mexliquidation.setServers(self.OkHigher,self.OkLower)
        # sys.exit(0)

    def setting_check(self):
        while 1:
            try:
                time.sleep(1)
                hserver = redis.get(constants.higher_server)
                lserver = redis.get(constants.lower_server)
                if hserver:
                    if "start" == hserver:
                        self.startHserver()
                    else:
                        self.stopHserver()
                if lserver:
                    if "start" == lserver:
                        self.startLserver()
                    else:
                        self.stopLserver()
            except:
                pass

    def start(self):
        self.marketPrice.start()
        #self.OkHigher.start()
        #self.OkLower.start()
        self.mexliquidation.start()

        check = threading.Thread(target=self.setting_check)
        check.setDaemon(True)
        check.start()

    def startHserver(self):
        self.OkLower.stop()
        self.OkHigher.start()

    def stopHserver(self):
        self.OkHigher.stop()

    def startLserver(self):
        self.OkHigher.stop()
        self.OkLower.start()

    def stopLserver(self):
        self.OkLower.stop()


    def cancel_all(self):
        self.okcoin.cancel_all(self.contract_type)

    def cal_order(self, okposition, mexposition):
        sposition = self.conn.get(self.slipkey)
        if not sposition:
            sposition = []
        if not okposition or not okposition['sell_amount']:
            self.conn.set(self.slipkey, [])
        else:
            if (mexposition[1] != okposition['sell_amount'] * 100):
                logger.info("两端仓位不平，对冲个屁啊，赶紧改！")
                sys.exit(1)
            self.split_position = sposition
            cnt = 0
            allbais = 0
            for pos in sposition:
                cnt += pos[0]
                allbais += pos[0] * pos[1]
            if cnt < okposition['sell_amount']:
                a = (okposition['sell_price_avg'] - mexposition[0]) * okposition['sell_amount'] - allbais
                b = okposition['sell_amount'] - cnt
                bais = round(a / b, 3)
                self.split_position.append(((okposition['sell_amount'] - cnt), bais))
                self.conn.set(self.slipkey, self.split_position)
            if (cnt > okposition['sell_amount']):
                left_amount = cnt - okposition['sell_amount']
                while (self.split_position and left_amount > 0):
                    last_pos = self.split_position.pop()
                    left_amount = left_amount - last_pos[0]
                    if (left_amount < 0):
                        self.split_position.append((-left_amount, last_pos[1]))
                        break
                self.conn.set(self.slipkey, self.split_position)

    def cancel_all(self):
        self.okcoin.cancel_all(self.contract_type)


redis = Conn_db()
#redis.conn.set(constants.higher_main_run_key,False)
#redis.conn.set(constants.lower_main_run_key,False)
redis.set(constants.trade_server, True)
status = True

t = TradeMexAndOk()
t.start()


while status:
    status = redis.get(constants.trade_server)

    lower = redis.get(constants.lower_server)
    if lower:
        t.startLserver()
    else:
        t.stopLserver()

    higher = redis.get(constants.higher_server)
    if higher:
        t.startHserver()
    else:
        t.stopHserver()

    if constants.strategy_on:
        prices = redis.get(constants.ok_mex_price)
        if prices[4]-prices[1] >= constants.strategy_higher:
            t.startHserver()
        if prices[3]-prices[2] <= constants.strategy_lower:
            t.startLserver()

    time.sleep(1)
    pass
logger.info("###I'm quit###########")
t.cancel_all()

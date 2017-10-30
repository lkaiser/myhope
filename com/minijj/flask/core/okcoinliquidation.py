# coding=utf-8
import sys
import Queue
import datetime
import logging.handlers
import threading
import time
from db.rediscon import Conn_db
import constants as constants
from market_maker import bitmex
import api.okcoin_com_api as okcom
logger = logging.getLogger('root')

class okcoinLiquidation(object):
    def __init__(self, mex,mexpush,okcoin):
        self.mex = mex
        self.mexpush = mexpush

        self.okcoin = okcoin
        self.startime = datetime.datetime.now()
        self.conn = Conn_db()

    def highopenOrlowliquid(self):
        trade_back = None
        slipp = 0
        while 1:
            if slipp<3:
                trade_back = self.okcoin.tradeRival(constants.higher_contract_type, abs(self.mexpush.on_set["okqty"]), 2)
            else:
                recent = self.conn.get("recent2")
                recent.reverse()
                logger.info("okcoin high open at"+str(round(recent[0][4]-10,2)))
                trade_back = self.okcoin.trade(constants.higher_contract_type,round(recent[0][4]-10,2), abs(self.mexpush.on_set["okqty"]), 2)
            if not trade_back['result']:
                logger.info(trade_back)
                slipp += 2
                time.sleep(2)
                if slipp > 60:
                    break;
            else:
                break
        if slipp>60:
            logger.error("########bad thing happen,cant liquid on okcoin,error_code = " + str(trade_back['error_code']))
            return
        time.sleep(0.5)
        order = self.okcoin.get_order_info(constants.higher_contract_type,[str(trade_back['order_id'])])
        logger.info(order)
        logger.info(self.mexpush.on_set)
        exceedtime = 0
        while not order['result']:
            logger.info(order)
            time.sleep(1)
            exceedtime += 1
            order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
            if exceedtime > 120:
                logger.error("########bad thing happen,cant get liquid order info")
                break

        if order['result']:
            exceedtime = 0
            while order['orders'][0]['status'] !=1 and order['orders'][0]['status'] !=2:
                time.sleep(1)
                exceedtime += 1
                order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
                if exceedtime > 120:
                    logger.error("########bad thing happen,liquid order status not right " + str(trade_back['order_id']) + " to update statu")
                    break

        self.mexpush.recordSet(order['orders'][0])
        self.mexpush.on_set = None

    def highliquidOrlowopen(self):
        trade_back = None
        slipp = 0
        while 1:
            if slipp < 3:
                trade_back = self.okcoin.tradeRival(constants.higher_contract_type, abs(self.mexpush.on_liquid["okqty"]), 4)
            else:
                recent = self.conn.get("recent2")
                recent.reverse()
                logger.info("okcoin high open at" + str(round(recent[0][3]+10,2)))
                trade_back = self.okcoin.trade(constants.higher_contract_type,round(recent[0][3]+10,2), abs(self.mexpush.on_set["okqty"]), 4)
            if not trade_back['result']:
                logger.info(trade_back)
                slipp += 2
                time.sleep(2)
                if slipp > 60:
                    break;
            else:
                break;
        if slipp>60:
            logger.error("########bad thing happen,cant liquid on okcoin,error_code = " + str(trade_back['error_code']))
            return
        time.sleep(0.5)

        order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
        logger.info(order)
        logger.info(self.mexpush.on_liquid)
        exceedtime = 0
        while not order['result']:
            logger.info(order)
            time.sleep(1)
            exceedtime += 1
            order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
            if exceedtime > 120:
                logger.error("########bad thing happen,cant get liquid order info")
                break

        if order['result']:
            exceedtime = 0
            while (not order['result']) or (order['orders'][0]['status'] !=1 and order['orders'][0]['status'] !=2):
                time.sleep(1)
                exceedtime += 1
                order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
                if exceedtime > 120:
                    logger.debug("########bad thing happen,watting so long for order " + str(trade_back['order_id']) + " to update statu")
            self.mexpush.removeSet(order['orders'][0])
            self.mexpush.on_liquid = None




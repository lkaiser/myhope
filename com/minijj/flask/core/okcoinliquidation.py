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

    def highopen(self):
        trade_back = None
        slipp = 0
        while 1:
            trade_back = self.okcoin.tradeRival(constants.higher_contract_type, abs(self.mexpush.on_set["okqty"]), 2)
            logger.info(trade_back)
            if not trade_back['result']:
                trade_back = self.okcoin.cancel_orders(constants.higher_contract_type,[str(trade_back['order_id'])])
                logger.info(trade_back)
                if not trade_back['result']:
                    break;
                else:
                    slipp += 2
                    time.sleep(2)
                    if slipp > 60:
                        trade_back = None
                        break;
            else:
                break
        if slipp>60:
            logger.error("########bad thing happen,order "+str(trade_back['order_id'])+" cannot open")
            return
        time.sleep(0.5)
        order = self.okcoin.get_order_info(constants.higher_contract_type,[str(trade_back['order_id'])])
        exceedtime = 0
        while order['orders'][0]['status'] !=1 and order['orders'][0]['status'] !=2:
            time.sleep(1)
            exceedtime += 1
            order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
            if exceedtime > 60:
                logging.error("########bad thing happen,watting so long for order " + str(trade_back['order_id']) + " to update statu")
        logger.info(order)
        self.mexpush.recordSet(order['orders'][0])
        self.mexpush.on_set = None


    def highliquid(self):
        trade_back = None
        slipp = 0
        while 1:
            trade_back = self.okcoin.tradeRival(constants.higher_contract_type, abs(self.mexpush.on_liquid["okqty"]), 4)
            logger.info(trade_back)
            if not trade_back['result']:
                trade_back = self.okcoin.cancel_orders(constants.higher_contract_type,[str(trade_back['order_id'])])
                logger.info(trade_back)
                if not trade_back['result']:
                    break;
                else:
                    slipp += 2
                    time.sleep(2)
                    if slipp > 60:
                        trade_back = None
                        break;
            else:
                break;
        if slipp>60:
            logging.error("########bad thing happen,order "+str(trade_back['order_id'])+" cannot liquid")
            return
        time.sleep(0.5)
        order = self.okcoin.get_order_info(constants.higher_contract_type,[str(trade_back['order_id'])])
        exceedtime = 0
        while order['orders'][0]['status'] !=1 and order['orders'][0]['status'] !=2:
            time.sleep(1)
            exceedtime += 1
            order = self.okcoin.get_order_info(constants.higher_contract_type, [str(trade_back['order_id'])])
            if exceedtime > 60:
                logging.error("########bad thing happen,watting so long for order " + str(trade_back['order_id']) + " to update statu")
        logger.info(order)
        self.mexpush.removeSet(order['orders'][0])
        self.mexpush.on_liquid = None




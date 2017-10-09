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

logger = logging.getLogger('root')  # 获取名为tst的logger
class mexpush(object):
    def __init__(self, mex,market,max_size):
        self.conn = Conn_db()
        self.mex = mex
        self.status = False
        self.market = market
        self.max_size = max_size
        self.openevent = threading.Event()  # 开仓暂停
        self.openhigh = True
        self.openlow = True
        self.openedhigh = self.conn.get(constants.opened_high)
        self.openedlow = self.conn.get(constants.opened_low)
        self.high_order = None
        self.low_order = None

    def is_openhigh(self):
        #TODO 策略判断
        return self.openedhigh

    def is_openlow(self):
        # TODO 策略判断 1有low挂单，挂单是否需要重新挂 2 均线趋势
        return self.openlow

    def high_price(self,depth):


    def openPosition(self):
        while 1:
            if not self.status:
                logger.info("###############################Higher 开仓 thread shutdown");
                break
            if not self.openevent.isSet():#开仓暂停
                logger.info("###############################Higher 开仓 suspend");
                self.openevent.wait()
            depth = self.market.get_depth_5_price()
            if self.openhigh:
                if self.high_order:
                    nowstatus = self.mex.get(self.high_order['clOrdID'])
                rst = self.mex.buy((abs(order[2]) * 100 - partdel), (order[1] + slipp))



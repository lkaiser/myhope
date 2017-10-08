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
    def __init__(self, mex):
        self.mex = mex
        self.status = False
        self.openevent = threading.Event()  # 开仓暂停

    def openPosition(self):
        while 1:
            if not self.status:
                logger.info("###############################Higher 开仓 thread shutdown");
                break
            if not self.openevent.isSet():#开仓暂停
                logger.info("###############################Higher 开仓 suspend");
                self.openevent.wait()

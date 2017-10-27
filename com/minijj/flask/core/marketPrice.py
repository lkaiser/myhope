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


import sys


logger = logging.getLogger('root')  # 获取名为tst的logger


class MarketPrice(object):
    def __init__(self):
        self.ws = websocket.WebSocket()
        self.q_asks_price = Queue.Queue(1)
        self.q_bids_price = Queue.Queue(1)
        self.mex_bids_price = None
        self.mex_asks_price = None
        self.depth_5_price = None


        # sys.exit(0)

    @staticmethod
    def calc_price(order_list):
        l = []
        k = 0
        for i in order_list:
            k += i[0] * i[1]
            l.append(i[1])
        return k / sum(l)

    # 统计mex 3档行情买卖平均价
    def calc_mex_order_price(self, recv_data):
        asks_price = self.calc_price(json.loads(recv_data)['data'][0]['asks'][0:5])
        bids_price = self.calc_price(json.loads(recv_data)['data'][0]['bids'][0:5])
        return asks_price, bids_price

    def mex_order_price(self, recv_data):
        asks_price = json.loads(recv_data)['data'][0]['asks'][0:5]
        bids_price = json.loads(recv_data)['data'][0]['bids'][0:5]
        self.depth_5_price = [asks_price, bids_price]

    def get_depth_5_price(self):
        return self.depth_5_price


    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def init_ws(self):
        init_asks_price, init_bids_price = None, None
        while not init_asks_price and not init_bids_price:
            try:
                self.ws.close()
                logger.info("connecting to MEX... ")
                self.ws.connect("wss://www.bitmex.com/realtime")
                logger.info("Done")
                print '{"op": "subscribe", "args": ["orderBook10:' + constants.higher_mex_contract_type + '"]}'
                self.ws.send('{"op": "subscribe", "args": ["orderBook10:' + constants.higher_mex_contract_type + '"]}')
                self.ws.timeout = 8
                recv_data = ""
                logger.info(self.ws.recv())
                logger.info(self.ws.recv())  # welcome info.
                while '"table":"orderBook10"' not in recv_data:
                    recv_data = self.ws.recv()
                init_asks_price, init_bids_price = self.calc_mex_order_price(recv_data)
                logger.info("mex_order_price updated")
                self.mex_order_price(recv_data)
                self.q_asks_price.put(init_asks_price)
                self.q_bids_price.put(init_bids_price)
                return init_asks_price, init_bids_price
            except Exception, e:
                logger.info("############cannot connect to mex################")
                logger.info(e)
                time.sleep(5)
                pass


    def ws_thread(self):
        init_asks_price, init_bids_price = self.init_ws()
        while 1:
            try:
                recv_data = self.ws.recv()
                if 'pong' in recv_data:
                    continue
                else:
                    new_init_asks_price, new_init_bids_price = \
                        self.calc_mex_order_price(
                            recv_data)
                    self.mex_asks_price = new_init_asks_price
                    self.mex_bids_price = new_init_bids_price
                    self.mex_order_price(recv_data)

                    diff_asks = new_init_asks_price - init_asks_price

                    # 卖价波动超过0.3，最新价放到卖队列
                    if not -0.3 < diff_asks < 0.3:
                        init_asks_price = new_init_asks_price
                        # print "asks changed", self.mex_asks_price
                        try:
                            self.q_asks_price.put(self.mex_asks_price, timeout=0.01)
                        except:
                            pass
                            # print "too many"

                    diff_bids = new_init_bids_price - init_bids_price

                    # 买价波动超过0.3，最新价放到买队列
                    if not -0.3 < diff_bids < 0.3:
                        init_bids_price = new_init_bids_price
                        # print "bids changed", self.mex_bids_price
                        try:
                            self.q_bids_price.put(self.mex_bids_price, timeout=0.01)
                        except:
                            pass
                            # print "too many"

            except Exception, e:
                logger.info(e)
                self.init_ws()

    def ping_thread(self):
        while 1:
            try:
                time.sleep(3)
                self.ws.send("ping")
            except:
                pass

    def start(self):
        ws = threading.Thread(target=self.ws_thread)
        ws.setDaemon(True)
        ws.start()
        time.sleep(5)

        ping_thread = threading.Thread(target=self.ping_thread)
        ping_thread.setDaemon(True)
        ping_thread.start()

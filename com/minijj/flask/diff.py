# coding=utf-8
import datetime
import json
import threading
import time
from threading import Timer

import websocket

import dataStore

import core.constants as constants

from core.db import rediscon


class CycleList(object):
    def __init__(self, maxsize):
        self.list = []
        self.maxsize = maxsize
        self.size = 0
        self.ind = 0
        self.lock = threading.Lock()

    def put(self,obj):
        if self.lock.acquire():
            if self.size < self.maxsize:
                self.list.append(obj)
                self.size += 1
                self.ind = self.size - 1
            else:
                self.ind = (self.ind + 1) % self.maxsize
                self.list[self.ind] = obj
            self.lock.release()


    def peek(self):
        if self.size == 0:
            return None
        else:
            return self.list[self.ind]

    def orderesult(self):
        if self.lock.acquire():
            rs = None
            if(self.size==self.maxsize):
                rs = self.list[self.ind+1:self.maxsize]+self.list[0:self.ind+1]
            else:
                rs = self.list[0:(self.ind+1)]
            self.lock.release()
            return rs

class Diff(object):
    def __init__(self, deal_amount,maxsize):
        self.ws_ok = websocket.WebSocket()
        self.ws_mex = websocket.WebSocket()
        self.ok_price = None
        self.ok_askprice = None
        self.mex_price = None
        self.mex_bidprice = None

        self.deal_amount = deal_amount
        self.renew = False
        self.list = CycleList(maxsize)
        self.recent = CycleList(1200)
        self.recent2 = CycleList(1200)
        self.store = dataStore.DataStore()
        self.conn = rediscon.Conn_db()

    def init_mex_ws(self):
        try:
            self.ws_mex.close()
            self.ws_mex.connect("wss://www.bitmex.com/realtime")
            self.ws_mex.send('{"op": "subscribe", "args": ["orderBook10:XBTU17"]}')
            self.ws_mex.settimeout = 6
        except Exception, e:
            self.init_mex_ws()

    def init_ok_ws(self):
        try:
            self.ws_ok.close()
            self.ws_ok.connect("wss://real.okex.com:10440/websocket/okcoinapi")
            # this_week = {'event': 'addChannel',
            #              'channel': 'ok_sub_futureusd_btc_depth_this_week_60'}
            # next_week = {'event': 'addChannel',
            #              'channel': 'ok_sub_futureusd_btc_depth_next_week_60'}
            quarter = {'event': 'addChannel',
                       'channel': 'ok_sub_futureusd_btc_depth_quarter_60'}
            # contract = [this_week, next_week, quarter]
            contract = [quarter]
            self.ws_ok.settimeout = 6

            for c in contract:
                self.ws_ok.send(json.dumps(c))
        except Exception, e:
            print e
            self.init_ok_ws()

    def mex_ping(self):
        while 1:
            try:
                time.sleep(4)
                self.ws_mex.send("ping")
            except:
                print "error mex ping"
                pass

    @staticmethod
    def depth(amount, order_list):
        sum_list = []
        amount_1 = amount
        sum_am = []
        for am in order_list:
            sum_am.append(am[1])
        sum_amount = sum(sum_am)
        if amount > sum_amount:
            return "NULL"
        if amount <= float(order_list[0][1]):
            return order_list[0][0], order_list[0][0]
        else:
            for bp in order_list:
                amount -= float(bp[1])
                if amount > 0:
                    sum_list.append(float(bp[1]) * float(bp[0]))
                    last_am = amount
                else:
                    sum_list.append(last_am * float(bp[0]))
                    break
            return sum(sum_list) / amount_1, float(bp[0])

    def ok_ping(self):
        while 1:
            try:
                time.sleep(4)
                self.ws_ok.send("ping")
            except:
                print "error ok ping"
                pass

    def get_mex_price(self):
        while 1:
            try:
                mex_data = self.ws_mex.recv()
                if mex_data != 'pong':
                    ws_data = json.loads(mex_data)
                    if 'action' in ws_data and 'types' not in ws_data:
                        ws_data = ws_data['data'][0]

                        #print "mex asks",ws_data['asks']
                        #print "mex bids",ws_data['bids']
                        self.mex_price = \
                        self.depth(self.deal_amount * 100, ws_data['asks'])[0]

                        self.mex_bidprice = \
                            self.depth(self.deal_amount * 100, ws_data['bids'])[0]
                        #print ws_data
                        #print 'seconds = ',ws_data['timestamp'][18:19]
                        #print 'date = ', ws_data['timestamp'][0:19]
                        # if not int(ws_data['timestamp'][18:19])%5:
                        #     latest = self.mexlist.peek()
                        #     print "mex time ", ws_data['timestamp'][0:19]
                        #     if (not latest or latest[2] != ws_data['timestamp'][0:19]):
                        #         lastestime = datetime.datetime.strptime(ws_data['timestamp'][0:19], '%Y-%m-%dT%H:%M:%S')
                        #         self.mexlist.put((lastestime, round(self.mex_price,3),ws_data['timestamp'][0:19]))
                        #print ws_data
            except Exception, e:
                print e
                self.init_mex_ws()


    def get_ok_price(self):
        while 1:
            try:
                recv_data = self.ws_ok.recv()
                if recv_data != 'pong':
                    ws_data = json.loads(recv_data)
                    if 'result' not in ws_data[0]['data']:
                        ws_data = ws_data[0]
                        #print ws_data
                        if ws_data['channel'] == 'ok_sub_futureusd_btc_depth_quarter_60':
                            l = ws_data['data']['bids']
                            #print "bids",l[0]
                            k = []
                            for i in l:
                                k.append([float(i[0]),float(i[1])])
                            # l.reverse()
                            self.ok_price = self.depth(self.deal_amount,k)[0]

                            l = ws_data['data']['asks']
                            l.reverse()
                            #print "asks",l[0]
                            k = []
                            for i in l:
                                k.append([float(i[0]), float(i[1])])
                            # l.reverse()
                            self.ok_askprice = self.depth(self.deal_amount, k)[0]
                            # print "OK",self.ok_price
                            # tst = ws_data['data']['timestamp']
                            # if not (tst / 1000) % 5:
                            #     latest = self.oklist.peek()
                            #     if(not latest or latest[2] != int(tst/1000)):
                            #         lastestime = datetime.datetime.utcfromtimestamp(int(tst / 1000))
                            #         self.oklist.put((lastestime,round(self.ok_price),int(tst/1000)))
            except Exception, e:
                print e
                self.init_ok_ws()

    def caculate_diff(self):
        count = 9
        while 1:
            try:
                time.sleep(1)
                count += 1
                count = count % 10
                if self.mex_price and self.ok_price:
                    self.recent.put((datetime.datetime.utcnow(), round(self.mex_price, 3), round(self.ok_price, 3)))
                    self.conn.set('recent', self.recent.orderesult())




                if not count:
                    if self.mex_price and self.ok_price:
                        print 'systerm utc time=',datetime.datetime.utcnow()
                        self.list.put((datetime.datetime.utcnow(), round(self.mex_price, 3), round(self.ok_price, 3)))
                        self.conn.set('list', self.list.orderesult())
            except Exception as e:
                print "fuck",e
                pass

    def diff1sca(self):
        if self.mex_price and self.ok_price:
            p1 = self.mex_price  #mex 卖
            p2 = self.ok_price   # ok 买
            p3 = self.ok_askprice # ok 卖
            p4 = self.mex_bidprice #mex 买  p3 - p4
            if (type(p1) == float and type(p2) == float  and type(p3) == float  and type(p4) == float):
                self.conn.set(constants.ok_mex_price, (datetime.datetime.utcnow(), round(p1, 3), round(p4, 3),round(p3, 3), round(p2, 3)))
                #print self.conn.get(constants.ok_mex_price)
                self.recent.put((datetime.datetime.utcnow(), round(p1, 3), round(p2, 3)))
                self.conn.set('recent', self.recent.orderesult())

                self.recent2.put((datetime.datetime.utcnow(), round(p1, 3), round(p4, 3),
                                  round(p3, 3), round(p2, 3)))
                #print (datetime.datetime.utcnow(), round(p1, 3), round(self.mex_bidprice, 3),
                #       round(self.ok_askprice, 3), round(self.ok_price, 3))
                self.conn.set('recent2', self.recent2.orderesult())

                #print "recent2 ==",self.recent2.orderesult()[1:5]
        t = Timer(1, self.diff1sca).start()

    def diff10sca(self):
        if self.mex_price and self.ok_price:
            if(type(self.mex_price) == float and type(self.ok_price) == float):
                self.list.put((datetime.datetime.utcnow(), round(self.mex_price, 3), round(self.ok_price, 3)))
                self.conn.set('list', self.list.orderesult())
        t = Timer(10, self.diff10sca).start()

    def schedStore(self):
        self.store.extra(self.list.orderesult())
        self.store.commit()
        t = Timer(10, self.schedStore).start()

    def run(self):
        self.init_mex_ws()
        self.init_ok_ws()
        time.sleep(3)

        ok = threading.Thread(target=self.get_ok_price)
        ok.setDaemon(True)
        ok.start()

        mex = threading.Thread(target=self.get_mex_price)
        mex.setDaemon(True)
        mex.start()

        ping_mex = threading.Thread(target=self.mex_ping)
        ping_mex.setDaemon(True)
        ping_mex.start()

        ping_ok = threading.Thread(target=self.ok_ping)
        ping_ok.setDaemon(True)
        ping_ok.start()

        #ca = threading.Thread(target=self.caculate_diff)
        #ca.setDaemon(True)
        #ca.start()
        ca1 = threading.Thread(target=self.diff1sca)
        ca1.setDaemon(True)
        ca1.start()

        ca10 = threading.Thread(target=self.diff10sca)
        ca10.setDaemon(True)
        ca10.start()

        st = threading.Thread(target=self.schedStore)
        st.setDaemon(True)
        st.start()

if __name__ == '__main__':
    dif = Diff(50, 3000)

    dif.run()

    while 1:
        try:
            time.sleep(1)
        except Exception as e:
            print "fuck", e
            pass





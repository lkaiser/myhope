# -*- coding: utf-8 -*-
import Queue
import json
import logging.handlers
import sys
import threading
import time

import websocket
from retrying import retry

import api.okcoin_com_api as okcom
import mexliquidation
from api import bitmex_api
from db.rediscon import Conn_db
from market_maker import bitmex

LOG_FILE = 'test.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 1024*1024, backupCount = 5) # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('tst')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)


class TradeMexAndOk(object):
    def __init__(self, contract_type='quarter', max_size=24, deal_amount=6,
                 expected_profit=5, basis_create=40, step_price=1.5):
        key = "3c9833c6-60b1-4b6b-a995-1981db34eedf"
        skey = "07408F4678E5A6A99A4153B1A686A6B7"

        mex_key = 'h80qBYmz4GpyJv2VkCeBqyVf'
        mex_skey = '1kt1T3uyEEuK_T1aYGmXZq9sG2JM8bq-RFt-X5ih6XzIYeMI'
        bmext = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',
                              symbol='XBTUSD', apiKey=mex_key, apiSecret=mex_skey)
        self.mex = bmext

        self.contract_type = contract_type
        self.okcoin = okcom.OkCoinComApi(key, skey)
        self.okcoin.cancel_all(self.contract_type)
        self._mex = bitmex_api.Bitmex()
        self.ws = websocket.WebSocket()
        self.q_asks_price = Queue.Queue(1)
        self.q_bids_price = Queue.Queue(1)
        self.mex_bids_price = None
        self.mex_asks_price = None
        self.MAX_Size = max_size
        self.deal_amount = deal_amount
        self.expected_profit = expected_profit
        self.basis_create = basis_create
        self.basis_cover = -500
        self.step_price = step_price
        self.init_basis_create = basis_create
        self.init_MAX_Size = max_size
        #self.already_basis = None
        self.normal = True
        self.mexliquidation = mexliquidation.mexliquidation(self.mex,self)
        self.mexliquidation.start()
        #self.mexliquidation.suborder(3300,3000,-1,10,300,'sell')

        #input_s = raw_input("Input Mode\n")
        #assert input_s == 'higher', "Error"
        okposition = self.okcoin.get_position(self.contract_type)['holding'][0]
        mexposition = self._mex.get_position("XBTUSD")
        self.ok_sell_balance = 0
        self.mex_buy_balance = 0
        if okposition:
            self.ok_sell_balance = okposition['sell_amount']
            self.mex_buy_balance = self.ok_sell_balance
        self.balancelock = threading.Lock()
        self.conn = Conn_db()

        self.slipkey = skey

        #self.cal_order(okposition,mexposition)
        logger.info("##############初始化 后分段持仓##########")
        self.split_position = self.conn.get(self.slipkey)
        if(not self.split_position):
            self.split_position = []
        logger.info(self.split_position)
        #sys.exit(0)

    #
    def cal_order(self,okposition,mexposition):
        sposition = self.conn.get(self.slipkey)
        if not sposition:
            sposition = []
        if not okposition or not okposition['sell_amount']:
              self.conn.set(self.slipkey,[])
        else:
            if (mexposition[1] != okposition['sell_amount'] * 100):
                logger.info("两端仓位不平，对冲个屁啊，赶紧改！")
                sys.exit(1)
            self.split_position = sposition
            cnt = 0
            allbais = 0
            for pos in sposition:
                cnt += pos[0]
                allbais += pos[0]*pos[1]
            if cnt < okposition['sell_amount']:
                a = (okposition['sell_price_avg']-mexposition[0]) *okposition['sell_amount']-allbais
                b = okposition['sell_amount'] - cnt
                bais = round(a/b,3)
                self.split_position.append(((okposition['sell_amount'] - cnt), bais))
                self.conn.set(self.slipkey, self.split_position)
            if (cnt > okposition['sell_amount']):
                left_amount = cnt-okposition['sell_amount']
                while (self.split_position and left_amount > 0):
                    last_pos = self.split_position.pop()
                    left_amount = left_amount - last_pos[0]
                    if (left_amount < 0):
                        self.split_position.append((-left_amount, last_pos[1]))
                        break
                self.conn.set(self.slipkey, self.split_position)



    @staticmethod
    def calc_price(order_list):
        l = []
        k = 0
        for i in order_list:
            k += i[0] * i[1]
            l.append(i[1])
        return k / sum(l)

    def redefine_basic_create(self):
        print "redefine_basic_create"
        self.basis_create = self.init_basis_create

    def get_ok_sell_contract_amount(self):  # OK空单持仓amount
        return self.okcoin.get_position(self.contract_type)['holding'][0]['sell_amount']

    #统计mex 3档行情买卖平均价
    def calc_mex_order_price(self, recv_data):
        asks_price = self.calc_price(json.loads(recv_data)['data'][0]['asks'][0:3])
        bids_price = self.calc_price(json.loads(recv_data)['data'][0]['bids'][0:3])
        return asks_price, bids_price

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def init_ws(self):
        init_asks_price, init_bids_price = None, None
        while not init_asks_price and not init_bids_price:
            try:
                self.ws.close()
                logger.info("connecting to MEX... ")
                self.ws.connect("wss://www.bitmex.com/realtime")
                logger.info("Done")
                self.ws.send('{"op": "subscribe", "args": ["orderBook10:XBTUSD"]}')
                self.ws.timeout = 8
                recv_data = ""
                logger.info(self.ws.recv())
                logger.info(self.ws.recv())  # welcome info.
                while '"table":"orderBook10"' not in recv_data:
                    recv_data = self.ws.recv()
                    init_asks_price, init_bids_price = self.calc_mex_order_price(recv_data)
                    self.q_asks_price.put(init_asks_price)
                    self.q_bids_price.put(init_bids_price)
                return init_asks_price, init_bids_price
            except:
                time.sleep(3)
                pass

    def ping_thread(self):
        while 1:
            try:
                time.sleep(3)
                self.ws.send("ping")
            except:
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

                    diff_asks = new_init_asks_price - init_asks_price

                    #卖价波动超过0.3，最新价放到卖队列
                    if not -0.3 < diff_asks < 0.3:
                        init_asks_price = new_init_asks_price
                        #print "asks changed", self.mex_asks_price
                        try:
                            self.q_asks_price.put(self.mex_asks_price, timeout=0.01)
                        except:
                            pass
                            #print "too many"

                    diff_bids = new_init_bids_price - init_bids_price

                    # 买价波动超过0.3，最新价放到买队列
                    if not -0.3 < diff_bids < 0.3:
                        init_bids_price = new_init_bids_price
                        #print "bids changed", self.mex_bids_price
                        try:
                            self.q_bids_price.put(self.mex_bids_price, timeout=0.01)
                        except:
                            pass
                            #print "too many"

            except Exception, e:
                logger.info(e)
                self.okcoin.cancel_all(self.contract_type)
                self.init_ws()

    #现有问题，一开始就查持仓，执行到后面的重新提交平仓或者开仓动作时，并非以最新实际持仓下的操作，导致重复提交平仓（分步平仓下会影响盈利）、开仓（超过最大限额开仓）
    #一开始就要取消所有平仓、开仓动作,线程sleep 0.5s,执行接下来在查持仓,这样保证在一个循环周期内持仓不变
    def position_mon(self):
        init_holding = None
        okposition = self.okcoin.get_position(self.contract_type)['holding']
        if okposition:
            init_holding = okposition[0]
        buyorder_id = []
        sellorder_id = []
        while 1:
            try:
                if sellorder_id:
                    cancel_result = self.okcoin.cancel_orders(self.contract_type, sellorder_id)
                    if 'error_code' in cancel_result:
                        logger.info(cancel_result)
                        if cancel_result['error_code'] != 20015:
                            time.sleep(2)
                            logger.info("##########注意，新的错误来了#############")
                            logger.info(self.okcoin.cancel_orders(self.contract_type, sellorder_id))
                sellorder_id[:] = []
                if buyorder_id:
                    cancel_result = self.okcoin.cancel_orders(self.contract_type, buyorder_id)
                    if 'error_code' in cancel_result:
                        logger.info(cancel_result)
                        if cancel_result['error_code'] != 20015:
                            time.sleep(2)
                            logger.info("##########注意，新的错误来了#############")
                            logger.info(self.okcoin.cancel_orders(self.contract_type, buyorder_id))
                    buyorder_id[:] = []
                if sellorder_id or buyorder_id: #有买单或卖单需要平,平了之后等待0.5s
                    time.sleep(0.5)

                new_holding = self.okcoin.get_position(self.contract_type)['holding'][0]
                amount_change = new_holding['sell_amount'] - init_holding['sell_amount']

                logger.info("ok_sell_balance="+bytes(self.ok_sell_balance)+"amount_change = "+bytes(amount_change))

                self.ok_sell_balance += amount_change

                #OKcoin挂单成交后，mex立刻以市价做出反向操作
                if amount_change > 0:
                    okprice = (new_holding['sell_price_avg'] * new_holding['sell_amount'] - init_holding[
                        'sell_price_avg'] * init_holding['sell_amount']) / amount_change
                    sell_price = round(self.mex_bids_price + 15, 1)#以成交为第一目的
                    logger.info(init_holding)
                    logger.info(new_holding)
                    logger.info("avarage ok deal price"+bytes(okprice))
                    logger.info("mex_bids_price = "+bytes(self.mex_bids_price)+" allow exced area= "+bytes(2))

                    self.mexliquidation.suborder(okprice,sell_price,amount_change,self.expected_profit,self.basis_create,'buy')

                if amount_change < 0:#有仓位被平
                    okprice = (new_holding['sell_price_avg'] * new_holding['sell_amount'] - init_holding[
                        'sell_price_avg'] * init_holding['sell_amount']) / amount_change
                    buy_price = round(self.mex_asks_price - 15, 1)
                    logger.info("mex_asks_price = "+bytes(self.mex_asks_price) + " allow exced area= "+ bytes(2))
                    # 按bais价格从高到低减,排序

                    last_pos = None
                    if self.balancelock.acquire():
                        self.split_position.sort(key=lambda x: x[1])
                        left_amount = -amount_change

                        while(self.split_position and left_amount>0):
                            last_pos = self.split_position.pop()
                            left_amount = left_amount-last_pos[0]
                            if(left_amount<0):
                                self.split_position.append((-left_amount,last_pos[1]))
                                break
                        if left_amount>0:
                            print "操你大爷，都卖光了还要卖？"

                        self.conn.set(self.slipkey, self.split_position)
                        logger.info("################ammout 减少了，持仓变化如下 #######################")
                        logger.info(self.conn.get(self.slipkey))
                    self.balancelock.release()

                    self.mexliquidation.suborder(okprice, buy_price, amount_change, self.expected_profit,last_pos[1], 'sell')

                init_holding = new_holding
                self.basis_create += float(amount_change) / float(self.deal_amount) * float(
                    self.step_price)  # okcoin每开成一空单,create 就上升 1.5/deal_amount,可以理解为价差在继续拉大,扩大下一次开单价差获取更大利差空间

                #重新提交平仓单
                buyorder_id = self.submit_buy_order()
                #重新挂空单

                sellorder_id = self.submit_sell_order()
                if buyorder_id or sellorder_id:
                    time.sleep(0.5)

            except Exception, e:
                time.sleep(1.25)
                logger.info(e)
                self.okcoin.cancel_all(self.contract_type)

    def plusUpdate(self,okprice,mexprice,amount):
        if self.balancelock.acquire():  # 更新balance、split_position
            self.mex_buy_balance += amount
            bais = okprice - mexprice
            self.split_position.append((amount, round(bais, 3)))
            self.split_position.sort(key=lambda x: x[1])
            self.conn.set(self.slipkey, self.split_position)
            logger.info("################ammout 增加了，持仓变化如下 #######################")
            logger.info(self.conn.get(self.slipkey))
        self.balancelock.release()

    def test(self):
        logger.info("就是个测试，看回调咋样");


    def minusUpdate(self,okprice,mexprice,amount):
        if self.balancelock.acquire():  # 更新balance、split_position
            self.mex_buy_balance += amount
        self.balancelock.release()


    def submit_buy_order(self):
        order_id = []
        price = self.q_bids_price.get()
        logger.info("q_bids_price= "+bytes(price))
        if self.split_position:
            highest = self.split_position[len(self.split_position)-1]
            baiss = highest[1]
            price = round(price, 2) + baiss - self.expected_profit
            trade_back = {}
            try:
                if highest[0] > 0:
                    amount = highest[0]
                    logger.info("下单，下单，平平平 amount= "+bytes(amount)+ "mex price = "+bytes(price+self.expected_profit-baiss)+" coin price = "+bytes(price) +" baiss= "+bytes(baiss))
                    trade_back = self.okcoin.trade(self.contract_type, price, amount, 4)
                    #time.sleep(0.5)
                    oid = trade_back['order_id']
                    order_id.append(str(oid))
            except Exception:
                logger.info(trade_back)
                logger.info("平平平oid error")
                self.okcoin.cancel_all(self.contract_type)
            finally:
                return order_id

    def submit_sell_order(self):
        order_id = []
        price = self.q_asks_price.get()
        logger.info("q_asks_price= " + bytes(price))
        price = round(price, 2) + self.basis_create  # mex 卖最新价 + 初始设定差价 放空单,失败就取消循环放,假设价格倒挂，create为负
        trade_back = {}
        try:
            if self.ok_sell_balance < self.MAX_Size:
                if self.MAX_Size - self.ok_sell_balance >= self.deal_amount:
                    amount = self.deal_amount
                else:
                    amount = abs(self.MAX_Size - self.ok_sell_balance)
                logger.info("下单，下单，买买买 amount= "+bytes(amount)+  "mex price = "+bytes(price-self.basis_create)+" coin price= "+bytes(price) +" basis_create= "+bytes(self.basis_create))
                trade_back = self.okcoin.trade(self.contract_type, price, amount, 2)
                #time.sleep(0.5)
                oid = trade_back['order_id']
                order_id.append(str(oid))
        except Exception:
            logger.info(trade_back)
            logger.info("买买买oid error")
            self.okcoin.cancel_all(self.contract_type)
        finally:
            return order_id


    def splitposcheck(self):
        while 1:
            try:
                if self.balancelock.acquire():
                    #holding = self.conn.get('holding')
                    sposition = self.conn.get(self.slipkey)
                    if sposition:
                        cnt = 0
                        for pos in sposition:
                            cnt += pos[0]
                        #if cnt != holding[1]:
                         #   logger.info("持仓检查错误，分布持仓汇总="+bytes(cnt)+" 总持仓= "+bytes(holding[1]))
                self.balancelock.release()

                time.sleep(3)
            except Exception:
                pass



t = TradeMexAndOk(contract_type='quarter', max_size=120, deal_amount=4,
                  expected_profit=15, basis_create=304, step_price=4)

ws = threading.Thread(target=t.ws_thread)
pm = threading.Thread(target=t.position_mon)
#splitposcheck = threading.Thread(target=t.splitposcheck)
ping_thread = threading.Thread(target=t.ping_thread)

pm.setDaemon(True)
ws.setDaemon(True)

ping_thread.setDaemon(True)
#splitposcheck.setDaemon(True)

ws.start()
time.sleep(7)
pm.start()
#splitposcheck.start()
ping_thread.start()

while 1:
    pass

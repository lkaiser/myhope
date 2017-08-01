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
        key = "f2e919df-378e-4c75-8c09-0ffa910649fe"
        skey = "2D2E421A1ECC4FE5481629ED824C388D"

        mex_key = 'J3LTq4n69Cpwzzwo_RNo7rXM'
        mex_skey = 'FirA0TKwY_I14byDi9ohKYX9FV4uz7qzBeTphrcNvN5w31Vm'
        self.mex = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',
                                 symbol='XBTM17', apiKey=mex_key, apiSecret=mex_skey)

        self.contract_type = contract_type
        self.okcoin = okcom.OkCoinComApi(key, skey)
        self.okcoin.cancel_all(self.contract_type)
        self._mex = bitmex_api.Bitmex()
        self.ws = websocket.WebSocket()
        self.split_position = []
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

        #input_s = raw_input("Input Mode\n")
        #assert input_s == 'higher', "Error"
        okposition = self.okcoin.get_position(self.contract_type)['holding'][0]
        mexposition = self._mex.get_position("XBTM17")
        self.ok_sell_balance = 0
        self.mex_buy_balance = 0
        if okposition:
            self.ok_sell_balance = okposition['sell_amount']
            self.mex_buy_balance = self.ok_sell_balance
        self.balancelock = threading.Lock()
        self.conn = Conn_db()

        self.cal_order(okposition,mexposition)
        logger.info("##############初始化 后分段持仓##########")
        logger.info(self.split_position)

    #
    def cal_order(self,okposition,mexposition):
        holding = self.conn.get('holding')
        sposition = self.conn.get('split_position')
        if not holding:
            holding = (0,0,0,0)
        if not sposition:
            sposition = []

        ammount = 0
        if(holding or sposition):
            for pos in sposition:
                ammount += pos[0]
            if ammount != holding[1]:
                logger.info("redis 记录的分仓汇总数据与持仓数据不对，咋整"+bytes(ammount)+ " while hoding="+bytes(holding[1]))
                sys.exit(1)
        if not okposition or not okposition['sell_amount']:
            self.conn.set('holding',(0,0,0,0))
            self.conn.set('split_position',[])
        else:
            if (mexposition[1] != okposition['sell_amount'] * 100):
                logger.info("两端仓位不平，对冲个屁啊，赶紧改！")
                sys.exit(1)
            self.split_position = sposition
            if(holding[1] < okposition['sell_amount']):
                a = (okposition['sell_amount'] * okposition['sell_price_avg'] - holding[1] * holding[0] / 100) / (okposition['sell_amount'] - holding[1])
                mexholding = mexposition[0] * mexposition[1] / 100
                mexp = holding[2]
                if mexp is None:
                    mexp = 0
                b = (mexholding - mexp * holding[3] / 100) / (okposition['sell_amount'] - holding[1])
                bais = round(a -b,3)
                self.split_position.append(((okposition['sell_amount'] - holding[1]), bais))
                self.conn.set('holding',(okposition['sell_price_avg'], okposition['sell_amount'], mexposition[0], mexposition[1]))
                self.conn.set('split_position', self.split_position)
            if (holding[1] > okposition['sell_amount']):
                left_amount = holding[1]-okposition['sell_amount']
                while (self.split_position and left_amount > 0):
                    last_pos = self.split_position.pop()
                    left_amount = left_amount - last_pos[0]
                    if (left_amount < 0):
                        self.split_position.append((-left_amount, last_pos[1]))
                        break
                self.conn.set('holding',(okposition['sell_price_avg'], okposition['sell_amount'], mexposition[0], mexposition[1]))
                self.conn.set('split_position', self.split_position)






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
                self.ws.send('{"op": "subscribe", "args": ["orderBook10:XBTM17"]}')
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
        init_amount = 0
        okposition = self.okcoin.get_position(self.contract_type)['holding']
        if okposition:
            init_amount = okposition[0]['sell_amount']
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

                okposition = self.okcoin.get_position(self.contract_type)['holding']
                okholding = 0
                new_init_amount = 0
                amount_change = 0
                logger.info("new holding amount = "+bytes(okposition[0]['sell_amount']))
                if okposition:
                    okholding = okposition[0]['sell_price_avg'] * okposition[0]['sell_amount']
                    new_init_amount = okposition[0]['sell_amount']#获取最新持仓情况
                    amount_change = new_init_amount - init_amount

                logger.info("amount_change = "+bytes(amount_change))

                init_amount = new_init_amount
                #OKcoin挂单成交后，mex立刻以市价做出反向操作
                if amount_change > 0:
                    #print "amount_change", amount_change
                    sell_price = round(self.mex_bids_price + 0.5, 1)#以成交为第一目的
                    logger.info("mex_bids_price = "+bytes(self.mex_bids_price)+" allow exced area= "+bytes(0.5))
                    rst = self._mex.buy("XBTM17", sell_price, amount_change * 100)
                    if rst['ordStatus'] and 'filled' == rst['ordStatus']:
                        print "这尼玛才是真的成交了啊"
                    threading._sleep(0.5) #考虑提交一定时间后mex position holding才更新到最新状态

                    mexposition = self._mex.get_position("XBTM17")

                    mexholding = mexposition[0] * mexposition[1]/100

                    if self.balancelock.acquire():  #更新balance、split_position
                        self.mex_buy_balance += amount_change
                        self.ok_sell_balance += amount_change
                        lastholding = self.conn.get('holding')
                        mexp = lastholding[2]
                        if mexp is None:
                            mexp = 0
                        bais = (okholding - lastholding[0]*lastholding[1]) / amount_change - (mexholding - mexp*lastholding[3]/100) / amount_change
                        self.split_position.append((amount_change, round(bais,3)))
                        self.split_position.sort(key=lambda x: x[1])
                        self.conn.set('holding', (okposition[0]['sell_price_avg'],okposition[0]['sell_amount'],mexposition[0],mexposition[1]))
                        self.conn.set('split_position', self.split_position)
                        logger.info("################ammout 增加了，持仓变化如下 #######################")
                        logger.info(self.conn.get("holding"))
                        logger.info(self.conn.get("split_position"))
                    self.balancelock.release()
                    #self.renew_ok_order()

                if amount_change < 0:#有仓位被平
                    buy_price = round(self.mex_asks_price - 0.5, 1)
                    logger.info("mex_asks_price = "+bytes(self.mex_asks_price) + " allow exced area= "+ bytes(0.5))
                    logger.info(self._mex.sell("XBTM17", buy_price, -amount_change * 100, ))
                    threading._sleep(0.5)

                    mexposition = self._mex.get_position("XBTM17")
                    #mexholding = mexposition[0] * mexposition[1]
                    # 按bais价格从高到低减,排序
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
                        self.mex_buy_balance += amount_change
                        self.ok_sell_balance += amount_change
                        if not okposition[0]['sell_amount']:
                            self.conn.set('holding', (0,0,0,0))
                        else:
                            self.conn.set('holding', (okposition[0]['sell_price_avg'], okposition[0]['sell_amount'], mexposition[0], mexposition[1]))
                        self.conn.set('split_position', self.split_position)
                        logger.info("################ammout 减少了，持仓变化如下 #######################")
                        logger.info(self.conn.get("holding"))
                        logger.info(self.conn.get("split_position"))
                    self.balancelock.release()
                    #self.renew_ok_order()
                    #if self.ok_sell_balance == 0:
                    #    self.already_basis = None

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
            self.conn.set('split_position', self.split_position)
            logger.info("################ammout 增加了，持仓变化如下 #######################")
            logger.info(self.conn.get("split_position"))
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
                    holding = self.conn.get('holding')
                    sposition = self.conn.get('split_position')
                    if sposition:
                        cnt = 0
                        for pos in sposition:
                            cnt += pos[0]
                        if cnt != holding[1]:
                            logger.info("持仓检查错误，分布持仓汇总="+bytes(cnt)+" 总持仓= "+bytes(holding[1]))
                self.balancelock.release()

                time.sleep(3)
            except Exception:
                pass



t = TradeMexAndOk(contract_type='quarter', max_size=10, deal_amount=1,
                  expected_profit=25, basis_create=245, step_price=10)

ws = threading.Thread(target=t.ws_thread)
pm = threading.Thread(target=t.position_mon)
splitposcheck = threading.Thread(target=t.splitposcheck)
ping_thread = threading.Thread(target=t.ping_thread)

pm.setDaemon(True)
ws.setDaemon(True)

ping_thread.setDaemon(True)
splitposcheck.setDaemon(True)

ws.start()
time.sleep(7)
pm.start()
splitposcheck.start()
ping_thread.start()

while 1:
    pass

# -*- coding: utf-8 -*-
import logging.handlers
import threading
import time
import datetime
import Queue

import constants as constants
from db.rediscon import Conn_db


logger = logging.getLogger('root')  # 获取名为tst的logger

class OkLower(object):
    def __init__(self,okcoin,mex,_mex,market, contract_type='quarter', max_size=24, deal_amount=6,
                 expected_profit=15, basis_create=40,lower_back_distant=15, step_price=1.5):
        self.mex = mex
        self.contract_type = contract_type
        self.okcoin = okcoin
        self.okcoin.cancel_all(self.contract_type)
        self._mex = _mex
        self.market = market
        self.MAX_Size = max_size
        self.deal_amount = deal_amount
        self.expected_profit = expected_profit
        self.basis_create = basis_create
        self.lower_back_distant = lower_back_distant
        self.step_price = step_price
        self.init_basis_create = basis_create
        self.status = False
        self.event = threading.Event()
        self.openevent = threading.Event()
        self.liquidevent = threading.Event()
        self.waitevent = threading.Event()

        self.conn = Conn_db()
        self.conn.set(constants.lower_max_size_key, self.MAX_Size)
        self.conn.set(constants.lower_deal_amount_key, self.deal_amount)
        self.conn.set(constants.lower_expected_profit_key, self.expected_profit)
        self.conn.set(constants.lower_back_distant_key, self.lower_back_distant)
        self.conn.set(constants.lower_basic_create_key, self.basis_create)
        self.conn.set(constants.lower_step_price_key, self.step_price)

        okposition = self.okcoin.get_position(self.contract_type)['holding'][0]
        self.ok_sell_balance = 0
        self.mex_buy_balance = 0
        if okposition:
            self.ok_sell_balance = okposition['buy_amount']
            self.mex_buy_balance = self.ok_sell_balance
        self.balancelock = threading.Lock()

        self.conn.set(constants.lower_buy_run_key, True)
        self.conn.set(constants.lower_sell_run_key, True)

        self.slipkey = constants.lower_split_position
        self.lastevenuprice = 0
        self.lastsub = datetime.datetime.now()
        self.sublock = threading.Lock()


        logger.info("##############lower 初始化 后分段持仓##########")
        self.split_position = self.conn.get(self.slipkey)
        if(not self.split_position):
            self.split_position = []
        logger.info(self.split_position)

    def cancel_all(self):
        self.okcoin.cancel_all(self.contract_type)

    def flush_status(self,amount_change):
        if amount_change != 0:
            self.ok_sell_balance += amount_change
            self.basis_create -= round(float(amount_change) / float(self.deal_amount) * float(self.step_price), 3)
            self.conn.set(constants.lower_basic_create_key, self.basis_create)
        if not self.waitevent.isSet():
            logger.info("###########set lower free##########")
            self.waitevent.set()

    def update_split_position(self,amount_change):
        if self.balancelock.acquire():
            last_pos = 0
            logger.info("###balancelock acqurie")
            self.split_position.sort(key=lambda x: x[1])
            self.split_position.reverse()
            left_amount = -amount_change
            prices = self.conn.get(constants.ok_mex_price)
            now_create = prices[3] - prices[2]  # 两种算法，1用当前差价  2 用split_position最新平仓差价
            last_create = now_create
            while (self.split_position and left_amount > 0):
                last_pos = self.split_position.pop()
                left_amount = left_amount - last_pos[0]
                last_create = last_pos[1]
                if (left_amount < 0):
                    self.split_position.append((-left_amount, last_pos[1]))
                    break
            if left_amount > 0:
                print "操你大爷，都卖光了还要卖？"
            self.conn.set(self.slipkey, self.split_position)
            logger.info("################ammout 减少了 " + bytes(amount_change) + "，持仓变化如下 #######################")
            if (last_create + self.expected_profit - self.lower_back_distant) < now_create:
                self.basis_create = round(last_create - self.lower_back_distant + self.expected_profit, 3)
                self.conn.set(constants.lower_basic_create_key, self.basis_create)
            self.balancelock.release()
            logger.info("#####balancelock release")
            return last_pos

    def plusUpdate(self,okprice,mexprice,amount):
        if self.balancelock.acquire():  # 更新balance、split_position
            logger.info("###balancelock acqurie")
            self.mex_buy_balance += amount
            if(amount >0):
                bais = okprice - mexprice
                self.split_position.append((amount, round(bais, 3)))
                self.split_position.sort(key=lambda x: x[1])
                self.split_position.reverse()
                self.conn.set(self.slipkey, self.split_position)
                logger.info("################mex ammout 增加了"+bytes(amount)+"，持仓变化如下 #######################")
            else:
                logger.info("################mex ammout 减少了" + bytes(amount) + "，持仓变化如下 #######################")
            self.balancelock.release()
            logger.info("#####balancelock rlease")

    def submit_buy_order(self):
        order_id = []
        cycletimes = 0
        while 1:
            if not self.status:
                logger.info("###############################Lower 平仓 thread shutdown");
                break
            if not self.event.isSet(): #停止信号
                logger.info("###############################Lower 平仓 thread stopped");
                self.event.wait()
            if not self.liquidevent.isSet():#平仓暂停
                logger.info("###############################Lower 平仓 suspend");
                self.liquidevent.wait()
            start = datetime.datetime.now()
            price = self.market.q_asks_price.get()
            end = datetime.datetime.now()
            logger.info("############buy order1 spend"+bytes(((end - start).microseconds)/1000.0)+"milli seconds ")
            if order_id:
                if self.sublock.acquire():
                    logger.info("###sublock acqurie")
                    escape = (datetime.datetime.now() - self.lastsub).microseconds
                    if escape < 430000:
                        time.sleep(round((430000 - escape) / 1000000.0, 2))
                        self.lastsub = datetime.datetime.now()
                    self.sublock.release()
                    logger.info("#####sublock release")
                    logger.info("下单，撤单，平仓撤单")
                    cancel_result = self.okcoin.cancel_orders(self.contract_type, [order_id[0][1]])
                    if 'error_code' in cancel_result:
                        logger.info(cancel_result)
                        if cancel_result['error_code'] != 20015 and cancel_result['error_code'] != 20016:
                            logger.info("##########注意，新的错误来了#############")
                            time.sleep(2)
                            cycletimes += 1
                            if cycletimes>20:
                                logger.info("##############terrible sycle on cancel buy order##########")
                            continue #取消状态只有2种，取消成功或者20015交易成功无法取消,其它状态都跳回重新取消
                        else:
                            cycletimes = 0
                            if cancel_result['error_code'] == 20015:
                                self.waitevent.clear()  # 发现有成交，强行等待 holdposition更新，否则会有holdpostion长时间不运行概率
                                self.waitevent.wait()
                    else:
                        cycletimes = 0

            order_id[:] = []
            end = datetime.datetime.now()
            logger.info("############buy order2 spend"+bytes(((end - start).microseconds)/1000.0)+" milli seconds,q_asks_price= "+bytes(price))
            if self.balancelock.acquire():
                logger.info("#############balancelock acuire")
                if self.split_position:
                    highest = self.split_position[len(self.split_position)-1]
                    self.balancelock.release()
                    logger.info("##################balancelock release")
                    baiss = highest[1]
                    price = round(price, 2) + baiss + self.expected_profit
                    self.lastevenuprice = price
                    trade_back = {}

                    okprice = self.conn.get(constants.ok_mex_price)
                    logger.info(
                        "#######current ok bid price =" + bytes(okprice[4]) + " while wanna 平仓 price=" + bytes(price))
                    if (price - okprice[4] > 5):
                        continue

                    try:
                        if highest[0] > 0:
                            amount = highest[0]
                            if self.sublock.acquire():
                                logger.info("###sublock acuire")
                                #if (datetime.datetime.now() - self.lastsub).microseconds < 300000:
                                #    time.sleep(0.3)
                                self.lastsub = datetime.datetime.now()
                                self.sublock.release()
                                logger.info("#####sublock release")
                                logger.info("下单，下单，平平平 amount= "+bytes(amount)+ "mex price = "+bytes(price-self.expected_profit-baiss)+" coin price = "+bytes(price) +" baiss= "+bytes(baiss))
                                trade_back = self.okcoin.trade(self.contract_type, price, amount, 3)
                                oid = trade_back['order_id']
                                order_id.append([amount, str(oid), datetime.datetime.now()])
                    except Exception:
                        logger.info(trade_back)
                        logger.info("平平平oid error")
                        self.okcoin.cancel_all(self.contract_type)
                    finally:
                        pass
                else:
                    self.balancelock.release()
                    logger.info("################balancelock release")
            end = datetime.datetime.now()
            logger.info("############buy order3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")

    def submit_sell_order(self):
        order_id = []
        cycletimes = 0
        while 1:
            if not self.status:
                logger.info("###############################Lower 开仓 thread shutdown");
                break
            if not self.event.isSet(): #停止信号
                logger.info("###############################Lower 开仓 thread stopped");
                self.event.wait()
            if not self.openevent.isSet():#开仓暂停
                logger.info("###############################Lower 开仓 suspend");
                self.openevent.wait()
            start = datetime.datetime.now()
            price = self.market.q_bids_price.get()
            end = datetime.datetime.now()
            logger.info("############sell order1 spend " + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")
            if order_id:
                if self.sublock.acquire():
                    logger.info("###sublock acuire")
                    escape = (datetime.datetime.now() - self.lastsub).microseconds
                    if escape < 430000:
                        time.sleep(round((430000-escape)/1000000.0,2))
                        self.lastsub = datetime.datetime.now()
                    self.sublock.release()
                    logger.info("#####sublock release")
                    logger.info("下单，撤单，买单撤单")
                    cancel_result = self.okcoin.cancel_orders(self.contract_type, [order_id[0][1]])

                    if 'error_code' in cancel_result:
                        logger.info(cancel_result)
                        if cancel_result['error_code'] != 20015:
                            logger.info("##########注意，新的错误来了#############")
                            time.sleep(2)
                            cycletimes += 1
                            if cycletimes>20:
                                logger.info("##############terrible sycle on cancel sell order##########")
                            continue #取消状态只有2种，取消成功或者20015交易成功无法取消,其它状态都跳回重新取消
                        else:
                            self.waitevent.clear()  #发现有成交，强行等待 holdposition更新，否则会有holdpostion长时间不运行概率
                            self.waitevent.wait()
                    else:
                        cycletimes = 0
            order_id[:] = []
            end = datetime.datetime.now()

            logger.info("############sell order2 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds  ,q_bids_price= " + bytes(price))
            price = round(price, 2) + self.basis_create  # mex 卖最新价 + 初始设定差价 放空单,失败就取消循环放,假设价格倒挂，create为负

            okprice = self.conn.get(constants.ok_mex_price)
            logger.info("#######current ok ask price =" + bytes(okprice[3]) + " while wanna 开仓 price=" + bytes(price))
            if (okprice[3] - price > 5):
                continue

            trade_back = {}
            try:
                if self.ok_sell_balance < self.MAX_Size:
                    if self.MAX_Size - self.ok_sell_balance >= self.deal_amount:
                        amount = self.deal_amount
                    else:
                        amount = abs(self.MAX_Size - self.ok_sell_balance)
                    if self.sublock.acquire():
                        #if (datetime.datetime.now() - self.lastsub).microseconds < 300000:
                        #    time.sleep(0.3)
                        self.lastsub = datetime.datetime.now()
                        logger.info("###sublock acuire")
                        self.sublock.release()
                        logger.info("#####sublock release")
                        self.lastsellprice = price
                        logger.info("下单，下单，买买买 amount= "+bytes(amount)+  "mex price = "+bytes(price-self.basis_create)+" coin price= "+bytes(price) +" basis_create= "+bytes(self.basis_create))
                        trade_back = self.okcoin.trade(self.contract_type, price, amount, 1)
                        oid = trade_back['order_id']
                        order_id.append([amount,str(oid),datetime.datetime.now()])

            except Exception ,e:
                logger.info(trade_back)
                logger.info("买买买oid error")
            finally:
                pass
            end = datetime.datetime.now()
            logger.info("############sell order3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")

    def setting_check(self):
        while 1:
            if not self.status:
                break
            try:
                time.sleep(1)
                fastformh = self.conn.get("fastforml")
                if fastformh:
                    logger.info("############fast forml setting################")
                    beforestatus = self.event.isSet() #
                    if beforestatus:
                        self.event.clear() #没停的话，先暂停
                    self.MAX_Size = fastformh['lower_max_size']
                    self.deal_amount = fastformh['lower_deal_amount']
                    self.expected_profit = fastformh['lower_expected_profit']
                    self.basis_create = fastformh['lower_basis_create']
                    self.lower_back_distant = fastformh['lower_back_distant']
                    self.step_price = fastformh['lower_step_price']

                    self.conn.set(constants.lower_max_size_key, self.MAX_Size)
                    self.conn.set(constants.lower_deal_amount_key, self.deal_amount)
                    self.conn.set(constants.lower_expected_profit_key, self.expected_profit)
                    self.conn.set(constants.lower_back_distant_key, self.lower_back_distant)
                    self.conn.set(constants.lower_basic_create_key, self.basis_create)
                    self.conn.set(constants.lower_step_price_key, self.step_price)
                    self.conn.delete("fastforml")
                    if beforestatus:
                        self.event.set()

            except:
                pass

    def start(self,basis=None):
        #self.server.test()
        if not self.status:
            logger.info("###############################Lower 跑起来了，哈哈哈");
            self.status = True
            self.openevent.set()
            self.liquidevent.set()
            self.conn.set(constants.lower_buy_run_key, True)
            self.conn.set(constants.lower_sell_run_key, True)

            if basis:
                self.conn.set(constants.lower_basic_create_key, basis)
                self.basis_create = basis

            sell = threading.Thread(target=self.submit_sell_order)
            sell.setDaemon(True)
            sell.start()

            buy = threading.Thread(target=self.submit_buy_order)
            buy.setDaemon(True)
            buy.start()

            check = threading.Thread(target=self.setting_check)
            check.setDaemon(True)
            check.start()
        self.event.set() #开启

    def stop(self):
        self.event.clear()
        logger.info("###############################Lower stopped");

    def stopOpen(self):
        self.openevent.clear()
        run = self.conn.get(constants.lower_buy_run_key)
        if run:
            self.conn.set(constants.lower_buy_run_key,False)

    def remainOpen(self):
        self.openevent.set()
        run = self.conn.get(constants.lower_buy_run_key)
        if not run:
            self.conn.set(constants.lower_buy_run_key,True)

    def stopLiquid(self):
        self.liquidevent.clear()
        run = self.conn.get(constants.lower_sell_run_key)
        if run:
            self.conn.set(constants.lower_sell_run_key,False)

    def remainLiquid(self):
        self.liquidevent.set()
        run = self.conn.get(constants.lower_sell_run_key)
        if not run:
            self.conn.set(constants.lower_sell_run_key,True)

    def liquidAll(self):
        if self.split_position:
            amount = 0
            for x in self.split_position:
                amount += x[0]
            self.okcoin.tradeRival(constants.lower_contract_type, amount, 3)



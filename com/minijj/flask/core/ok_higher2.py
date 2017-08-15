# -*- coding: utf-8 -*-

import logging.handlers
import threading
import time
import datetime

import constants as constants

from db.rediscon import Conn_db

logger = logging.getLogger('tst')  # 获取名为tst的logger

class OkHigher(object):
    def __init__(self,okcoin,mex,_mex,market,mexliquidation, contract_type='quarter', max_size=24, deal_amount=6,
                 expected_profit=15, basis_create=40,higher_back_distant=15, step_price=1.5):
        self.mex = mex
        self.contract_type = contract_type
        self.okcoin = okcoin
        self.okcoin.cancel_all(self.contract_type)
        self._mex = _mex
        self.market = market
        self.mexliquidation = mexliquidation
        self.MAX_Size = max_size
        self.deal_amount = deal_amount
        self.expected_profit = expected_profit
        self.basis_create = basis_create
        self.higher_back_distant = higher_back_distant
        self.step_price = step_price
        self.init_basis_create = basis_create
        self.status = False

        self.conn = Conn_db()
        self.conn.set(constants.higher_max_size_key, self.MAX_Size)
        self.conn.set(constants.higher_deal_amount_key, self.deal_amount)
        self.conn.set(constants.higher_expected_profit_key, self.expected_profit)
        self.conn.set(constants.higher_back_distant_key, self.higher_back_distant)
        self.conn.set(constants.higher_basic_create_key, self.basis_create)
        self.conn.set(constants.higher_step_price_key, self.step_price)

        okposition = self.okcoin.get_position(self.contract_type)['holding'][0]
        self.ok_sell_balance = 0
        self.mex_buy_balance = 0
        if okposition:
            self.ok_sell_balance = okposition['sell_amount']
            self.mex_buy_balance = self.ok_sell_balance
        self.balancelock = threading.Lock()

        #self.conn.set(constants.higher_buy_run_key, True)
        #self.conn.set(constants.higher_sell_run_key, True)
        #self.conn.set(constants.higher_main_run_key, True)
        self.slipkey = constants.higher_split_position
        self.lastevenuprice = 0
        self.lastsub = datetime.datetime.now()
        self.sublock = threading.Lock()
        self.amountsigal = 0

        logger.info("##############Hihger 分段持仓##########")
        self.split_position = self.conn.get(self.slipkey)
        if (not self.split_position):
            self.split_position = []
        logger.info(self.split_position)

        # sys.exit(0)

    def cancel_all(self):
        self.okcoin.cancel_all(self.contract_type)


    # 现有问题，一开始就查持仓，执行到后面的重新提交平仓或者开仓动作时，并非以最新实际持仓下的操作，导致重复提交平仓（分步平仓下会影响盈利）、开仓（超过最大限额开仓）
    # 一开始就要取消所有平仓、开仓动作,线程sleep 0.5s,执行接下来在查持仓,这样保证在一个循环周期内持仓不变
    def position_mon(self):
        init_holding = None
        okposition = self.okcoin.get_position(self.contract_type)['holding']
        if okposition:
            init_holding = okposition[0]
        while 1:
            if not self.status:
                break
            runmain = self.conn.get(constants.higher_main_run_key)
            if not runmain:
                logger.info("###############higher position suspend##################")
                time.sleep(2)
                continue
            try:
                new_holding = self.okcoin.get_position(self.contract_type)['holding'][0]
                amount_change = new_holding['sell_amount'] - init_holding['sell_amount']
                logger.info(
                    "ok_sell_balance=" + bytes(self.ok_sell_balance) + "amount_change = " + bytes(amount_change))

                self.ok_sell_balance += amount_change

                # OKcoin挂单成交后，mex立刻以市价做出反向操作
                if amount_change > 0:
                    okprice = (new_holding['sell_price_avg'] * new_holding['sell_amount'] - init_holding[
                        'sell_price_avg'] * init_holding['sell_amount']) / amount_change
                    sell_price = round(self.market.mex_bids_price + 8, 1)  # 以成交为第一目的
                    logger.info(init_holding)
                    logger.info(new_holding)
                    logger.info("avarage ok deal price" + bytes(okprice) + " while mex bid price =" + bytes(
                        self.market.mex_bids_price))
                    # logger.info("mex_bids_price = "+bytes(self.mex_bids_price)+" allow exced area= "+bytes(2))
                    logger.info(
                        "################ammout 增加了 " + bytes(amount_change) + "，持仓变化如下 #######################")
                    self.mexliquidation.suborder(okprice, sell_price, amount_change, self.expected_profit,
                                                 self.basis_create, 'buy')
                    self.basis_create += round(float(amount_change) / float(self.deal_amount) * float(self.step_price),
                                               3)
                    self.conn.set(constants.higher_basic_create_key, self.basis_create)

                if amount_change < 0:  # 有仓位被平
                    okprice = 0
                    buy_price = round(self.market.mex_asks_price - 8, 1)
                    # logger.info("avarage ok deal price" + bytes(okprice) + " while mex ask price =" + bytes(self.mex_asks_price))
                    # logger.info("mex_asks_price = "+bytes(self.mex_asks_price) + " allow exced area= "+ bytes(2))
                    # 按bais价格从高到低减,排序

                    last_pos = None
                    if self.balancelock.acquire():
                        logger.info("###balancelock acqurie")
                        self.split_position.sort(key=lambda x: x[1])
                        left_amount = -amount_change

                        while (self.split_position and left_amount > 0):
                            last_pos = self.split_position.pop()
                            left_amount = left_amount - last_pos[0]
                            if (left_amount < 0):
                                self.split_position.append((-left_amount, last_pos[1]))
                                break
                        if left_amount > 0:
                            print "操你大爷，都卖光了还要卖？"

                        self.conn.set(self.slipkey, self.split_position)
                        logger.info(
                            "################ammout 减少了 " + bytes(amount_change) + "，持仓变化如下 #######################")
                        # logger.info(self.conn.get(self.slipkey))
                        # logger.info("@@@@@@@@@okprice=="+bytes(self.lastevenuprice))
                        okprice = self.lastevenuprice
                        now_create = okprice - self.market.mex_asks_price
                        self.basis_create = round(now_create + self.higher_back_distant, 3)
                        self.conn.set(constants.higher_basic_create_key, self.basis_create)
                        # self.basis_create = now_create +8
                        self.balancelock.release()
                        logger.info("#####balancelock release")

                    self.mexliquidation.suborder(okprice, buy_price, amount_change, self.expected_profit, last_pos[1],
                                                 'sell')
                if (self.amountsigal > 10000):
                    self.amountsigal = 1
                else:
                    self.amountsigal += 1
                init_holding = new_holding
                # if amount_change>0:
                #     #logger.info("################basic_create=" + bytes(self.basis_create) + " ammount_change="+bytes(amount_change)+" deal_amount="+bytes(self.deal_amount)+" step_price="+bytes(self.step_price)+" ##############")
                #     self.basis_create += float(amount_change) / float(self.deal_amount) * float(self.step_price)
                #     self.conn.set(constants.higher_basic_create_key, self.basis_create)
                # if amount_change<0:
                #     #logger.info("################basic_create=" + bytes(self.basis_create) + " ammount_change=" + bytes(amount_change) + " deal_amount=" + bytes(self.deal_amount) + " step_price=" + bytes(self.step_price) + " ##############")
                #     self.basis_create += float(amount_change) / float(self.deal_amount) * float(self.step_price)*1.1  # okcoin每开成一多单,create 就上升 1.5/deal_amount,可以理解为价差在继续拉大,扩大下一次开单价差获取更大利差空间
                #     self.conn.set(constants.higher_basic_create_key, self.basis_create)
            except Exception, e:
                time.sleep(1.25)
                logger.info(e)
                self.okcoin.cancel_all(self.contract_type)
            time.sleep(0.5)
            # end = datetime.datetime.now()
            # logger.info("############position3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")

    def plusUpdate(self, okprice, mexprice, amount):
        if self.balancelock.acquire():  # 更新balance、split_position
            logger.info("###balancelock acqurie")
            self.mex_buy_balance += amount
            if (amount > 0):
                bais = okprice - mexprice
                self.split_position.append((amount, round(bais, 3)))
                self.split_position.sort(key=lambda x: x[1])
                self.conn.set(self.slipkey, self.split_position)
                logger.info("################mex ammout 增加了" + bytes(amount) + "，持仓变化如下 #######################")
                # logger.info(self.conn.get(self.slipkey))
            else:
                logger.info("################mex ammout 减少了" + bytes(amount) + "，持仓变化如下 #######################")
            self.balancelock.release()
            logger.info("#####balancelock rlease")

    def test(self):
        logger.info("就是个测试，看回调咋样");

    def minusUpdate(self, okprice, mexprice, amount):
        if self.balancelock.acquire():  # 更新balance、split_position
            logger.info("###balancelock acqurie")
            self.mex_buy_balance += amount
            self.balancelock.release()
            logger.info("#####balancelock release")

    def submit_buy_order(self):
        order_id = []
        cycletimes = 0
        laststatus = False
        while 1:
            if not self.status:
                break
            run = self.conn.get(constants.higher_buy_run_key)
            runmain = self.conn.get(constants.higher_main_run_key)
            if not run or not runmain:
                if laststatus:
                    self.okcoin.cancel_all(self.contract_type)
                    laststatus = False
                logger.info("###############buy supend##################")
                time.sleep(2)
                continue
            laststatus = True
            start = datetime.datetime.now()
            price = self.market.q_bids_price.get()
            end = datetime.datetime.now()
            logger.info("############buy order1 spend" + bytes(
                ((end - start).microseconds) / 1000.0) + "milli seconds ,q_asks_price= " + bytes(price))
            if order_id:
                if self.sublock.acquire():
                    logger.info("###sublock acqurie")
                    escape = (datetime.datetime.now() - self.lastsub).microseconds
                    if escape < 550000:
                        time.sleep(round((550000 - escape) / 1000000.0, 2))
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
                        if cycletimes > 20:
                            logger.info("##############terrible sycle on cancel buy order##########")
                        continue  # 取消状态只有2种，取消成功或者20015交易成功无法取消,其它状态都跳回重新取消
                    else:
                        cycletimes = 0
                else:
                    cycletimes = 0
            order_id[:] = []
            end = datetime.datetime.now()
            logger.info(
                "############buy order2 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")
            if self.balancelock.acquire():
                logger.info("#############balancelock acuire")
                if self.split_position:
                    highest = self.split_position[len(self.split_position) - 1]
                    self.balancelock.release()
                    logger.info("##################balancelock release")
                    baiss = highest[1]
                    price = round(price, 2) + baiss - self.expected_profit
                    self.lastevenuprice = price
                    trade_back = {}
                    try:
                        if highest[0] > 0:
                            amount = highest[0]
                            if self.sublock.acquire():
                                logger.info("###sublock acuire")
                                # if (datetime.datetime.now() - self.lastsub).microseconds < 300000:
                                #    time.sleep(0.3)
                                self.lastsub = datetime.datetime.now()
                                self.sublock.release()
                                logger.info("#####sublock release")
                                logger.info("下单，下单，平平平 amount= " + bytes(amount) + "mex price = " + bytes(
                                    price + self.expected_profit - baiss) + " coin price = " + bytes(
                                    price) + " baiss= " + bytes(baiss))
                                trade_back = self.okcoin.trade(self.contract_type, price, amount, 4)
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
            logger.info(
                "############buy order3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")

    def submit_sell_order(self):
        order_id = []
        cycletimes = 0
        laststatus = True
        while 1:
            if not self.status:
                break
            run = self.conn.get(constants.higher_sell_run_key)
            runmain = self.conn.get(constants.higher_main_run_key)
            if not run or not runmain:
                if laststatus:
                    self.okcoin.cancel_all(self.contract_type)
                    laststatus = False
                logger.info("###############sell supend##################")
                time.sleep(2)
                continue
            laststatus = True
            start = datetime.datetime.now()
            price = self.market.q_asks_price.get()
            end = datetime.datetime.now()
            logger.info("############sell order1 spend " + bytes(
                ((end - start).microseconds) / 1000.0) + " milli seconds ,q_bids_price= " + bytes(price))
            if order_id:
                if self.sublock.acquire():
                    logger.info("###sublock acuire")
                    escape = (datetime.datetime.now() - self.lastsub).microseconds
                    if escape < 550000:
                        time.sleep(round((550000 - escape) / 1000000.0, 2))
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
                        if cycletimes > 20:
                            logger.info("##############terrible sycle on cancel sell order##########")
                        continue  # 取消状态只有2种，取消成功或者20015交易成功无法取消,其它状态都跳回重新取消
                    else:
                        self.amountsigal = 0  # 设置amount更新信号，从0开始计数，更新2次以上后确认basis_create已经更新
                        while self.amountsigal < 2:
                            time.sleep(3)
                        cycletimes = 0
                else:
                    cycletimes = 0
            order_id[:] = []
            end = datetime.datetime.now()
            logger.info(
                "############sell order2 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")
            price = round(price, 2) + self.basis_create  # mex 卖最新价 + 初始设定差价 放空单,失败就取消循环放,假设价格倒挂，create为负
            trade_back = {}
            try:
                if self.ok_sell_balance < self.MAX_Size:
                    if self.MAX_Size - self.ok_sell_balance >= self.deal_amount:
                        amount = self.deal_amount
                    else:
                        amount = abs(self.MAX_Size - self.ok_sell_balance)
                    if self.sublock.acquire():
                        self.lastsub = datetime.datetime.now()
                        logger.info("###sublock acuire")
                        self.sublock.release()
                        logger.info("#####sublock release")
                        logger.info("下单，下单，买买买 amount= " + bytes(amount) + "mex price = " + bytes(
                            price - self.basis_create) + " coin price= " + bytes(price) + " basis_create= " + bytes(
                            self.basis_create))
                        trade_back = self.okcoin.trade(self.contract_type, price, amount, 2)
                        oid = trade_back['order_id']
                        order_id.append([amount, str(oid), datetime.datetime.now()])

            except Exception, e:
                logger.info(trade_back)
                logger.info("买买买oid error")

                # self.okcoin.cancel_all(self.contract_type)
            finally:
                pass
            end = datetime.datetime.now()
            logger.info(
                "############sell order3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")

    def setting_check(self):
        while 1:
            if not self.status:
                break
            try:
                time.sleep(1)
                fastformh = self.conn.get("fastformh")
                if fastformh:
                    logger.info("############fast formh setting################")
                    beforestatus = self.conn.get(constants.higher_main_run_key)
                    self.conn.set(constants.higher_main_run_key, False)
                    time.sleep(3)
                    self.MAX_Size = fastformh['higher_max_size']
                    self.deal_amount = fastformh['higher_deal_amount']
                    self.expected_profit = fastformh['higher_expected_profit']
                    self.basis_create = fastformh['higher_basis_create']
                    self.higher_back_distant = fastformh['higher_back_distant']
                    self.step_price = fastformh['higher_step_price']

                    self.conn.set(constants.higher_max_size_key, self.MAX_Size)
                    self.conn.set(constants.higher_deal_amount_key, self.deal_amount)
                    self.conn.set(constants.higher_expected_profit_key, self.expected_profit)
                    self.conn.set(constants.higher_back_distant_key, self.higher_back_distant)
                    self.conn.set(constants.higher_basic_create_key, self.basis_create)
                    self.conn.set(constants.higher_step_price_key, self.step_price)

                    if beforestatus:
                        self.conn.set(constants.higher_main_run_key, True)
                    self.conn.delete("fastformh")
            except:
                pass

    def start(self):
        logger.info("###############################Higher跑起来了，哈哈哈");
        #self.server.test()
        if not self.status:
            self.status = True
            pm = threading.Thread(target=self.position_mon)
            pm.setDaemon(True)
            pm.start()

            sell = threading.Thread(target=self.submit_sell_order)
            sell.setDaemon(True)
            sell.start()

            buy = threading.Thread(target=self.submit_buy_order)
            buy.setDaemon(True)
            buy.start()

            check = threading.Thread(target=self.setting_check)
            check.setDaemon(True)
            check.start()

    def stop(self):
        if self.status:
            self.status = False
            time.sleep(3)
            self.okcoin.cancel_all(self.contract_type)


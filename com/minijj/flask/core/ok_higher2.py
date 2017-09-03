# -*- coding: utf-8 -*-

import logging.handlers
import threading
import time
import datetime


import constants as constants

from db.rediscon import Conn_db

logger = logging.getLogger('root')  # 获取名为tst的logger

class OkHigher(object):
    def __init__(self,okcoin,mex,_mex,market, contract_type='quarter', max_size=24, deal_amount=6,
                 expected_profit=15, basis_create=40,higher_back_distant=15, step_price=1.5):
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
        self.higher_back_distant = higher_back_distant
        self.step_price = step_price
        self.init_basis_create = basis_create
        self.status = False
        self.event = threading.Event()  #启停控制
        self.openevent = threading.Event() #开仓暂停
        self.liquidevent = threading.Event() #平仓暂停
        self.waitevent = threading.Event() #等待 position
        self.lastUpdate = datetime.datetime.now()

        self.openorders = {}
        self.openstatus = False
        self.open_his = {}
        self.open_dealhis = []
        self.open_changehis = []
        self.openlock = threading.Lock()

        self.liquidorders = {}
        self.liquidstatus = False
        self.liquid_his = {}
        self.liquid_dealhis = []
        self.liquid_changehis = []
        self.liquidlock = threading.Lock()

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

        self.conn.set(constants.higher_buy_run_key, True)
        self.conn.set(constants.higher_sell_run_key, True)

        self.slipkey = constants.higher_split_position
        self.lastevenuprice = 0
        self.lastsellprice = 0
        self.lastsub = datetime.datetime.now()
        self.sublock = threading.Lock()


        logger.info("##############Higher 分段持仓##########")
        self.split_position = self.conn.get(self.slipkey)
        if (not self.split_position):
            self.split_position = []
        logger.info(self.split_position)

        # sys.exit(0)

    def cancel_all(self):
        self.okcoin.cancel_all(self.contract_type)


    def record_deal_status(self,amount_change):
        if amount_change >0 :
            for order in self.openorders.values():
                if not self.open_his.has_key(order[0]['order_id']):
                    self.open_his[order[0]['order_id']] = order[0]['deal_amount']
                    if order[0]['deal_amount'] != 0:
                        self.open_dealhis.append(([order[0]['deal_amount'], order[0]['price_avg']]))
                else:
                    if self.open_his[order[0]['order_id']] != order[0]['deal_amount']:
                        self.open_dealhis.append(([order[0]['deal_amount']-self.open_his[order[0]['order_id']],order[0]['price_avg']]))
                        self.open_his[order[0]['order_id']] = order[0]['deal_amount']
            self.open_changehis.append(abs(amount_change))
        else:
            for order in self.liquidorders.values():
                if not self.liquid_his.has_key(order[0]['order_id']):
                    self.liquid_his[order[0]['order_id']] = order[0]['deal_amount']
                    if order[0]['deal_amount'] != 0:
                        self.liquid_dealhis.append(([order[0]['deal_amount'], order[0]['price_avg']]))
                else:
                    if self.liquid_his[order[0]['order_id']] != order[0]['deal_amount']:
                        self.liquid_dealhis.append(([order[0]['deal_amount'] - self.liquid_his[order[0]['order_id']], order[0]['price_avg']]))
                        self.liquid_his[order[0]['order_id']] = order[0]['deal_amount']
            self.liquid_changehis.append(abs(amount_change))

    def get_deal_price(self,amount_change):
        dealhis = []
        allamount = 0
        if amount_change >0 :
            dealhis = self.open_dealhis
            allamount = sum(self.open_changehis)
        else:
            dealhis = self.liquid_dealhis
            allamount = sum(self.liquid_changehis)
        a_change = abs(amount_change)
        cur = 0
        price = 0
        curdeal = 0
        for index,deal in enumerate(dealhis):
            cur += deal[0]
            if cur >= allamount:
                amd = 0
                for i in range(index,-1,-1):
                    if i == index and cur > allamount:
                        curdeal = dealhis[i][0] - (cur - allamount)
                    else:
                        curdeal = dealhis[i][0]
                    if a_change - curdeal > 0:
                            amd += curdeal*dealhis[i][1]
                            a_change -= curdeal
                    else:
                        amd += a_change*dealhis[i][1]
                        break
                price = round(amd/a_change,2)
                break
        return price

    def flush_status(self,amount_change):
        self.lastUpdate = datetime.datetime.now()
        if amount_change != 0:
            self.ok_sell_balance += amount_change
            self.basis_create += round(float(amount_change) / float(self.deal_amount) * float(self.step_price), 3)
            self.conn.set(constants.higher_basic_create_key, self.basis_create)
            self.update_orders_status(amount_change)
            self.record_deal_status(amount_change)
            self.remove_no_use_orders(amount_change)
        if not self.waitevent.isSet():
            logger.info("###########set higher free##########")
            self.waitevent.set()

    def update_split_position(self,amount_change):
        if self.balancelock.acquire():
            last_pos = 0
            logger.info("###balancelock acqurie")
            self.split_position.sort(key=lambda x: x[1])
            left_amount = -amount_change
            prices = self.conn.get(constants.ok_mex_price)
            now_create = prices[4] - prices[1]  # 两种算法，1用当前差价  2 用split_position最新平仓差价
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
            if (last_create - self.expected_profit + self.higher_back_distant) > now_create:  # 计算basic_create是否大于市场差价，大于，则说明平仓后再开仓需继续等待，小于则说明1 行情迅速反弹至下一建仓点以上，2被套，手动平仓，这2种情况都无需修改下一建仓点
                self.basis_create = round(last_create + self.higher_back_distant - self.expected_profit, 3)
                self.conn.set(constants.higher_basic_create_key, self.basis_create)
            self.balancelock.release()
            logger.info("#####balancelock release")
            return last_pos

    def update_orders_status(self,amount_change):
        if amount_change >0 :
            if self.openlock.acquire():
                ids = []
                for order in self.openorders.values():
                    ids.append(str(order[0]['order_id']))
                neworders = self.okcoin.get_order_info(self.contract_type, ids)
                logger.info(neworders)
                for order in neworders['orders']:
                    self.openorders[order['order_id']][0] = order
                self.openlock.release()
        else:
            if self.liquidlock.acquire():
                ids = []
                for order in self.liquidorders.values():
                    ids.append(str(order[0]['order_id']))
                neworders = self.okcoin.get_order_info(self.contract_type, ids)
                for order in neworders['orders']:
                    self.liquidorders[['order_id']][0] = order
                self.liquidlock.release()

    def remove_no_use_orders(self,amount_change):
        if amount_change >0 :
            if self.openlock.acquire():
                for order in self.openorders.values():
                    if order[0]['status'] == 2 or order[0]['status'] == -1:
                        del self.openorders[order[0]['order_id']]
                        del self.open_his[order[0]['order_id']]
                        if order[0]['status'] == 2: #订单全部成交，说明可以重新开仓了
                            self.openstatus = True
                self.openlock.release()
        else:
            if self.liquidlock.acquire():
                for order in self.liquidorders.values():
                    if order[0]['status'] == 2 or order[0]['status'] == -1:
                        del self.liquidorders[order[0]['order_id']]
                        del self.liquid_his[order[0]['order_id']]
                        if order[0]['status'] == 2: #订单全部成交，说明可以重新平仓了
                            self.liquidstatus = True
                self.liquidlock.release()

    def add_new_open_orders(self,orders,levels):
        rightorders = []
        for order in orders:
            if order != -1:
                rightorders.append(str(order))
        neworders = self.okcoin.get_order_info(self.contract_type, rightorders)
        if neworders.has_key('orders'):
            if self.openlock.acquire():
                for order in neworders['orders']:
                    for level in levels:
                        if order['price'] == level[1]:
                            self.openorders[order['order_id']] = [order,level[2],level[0]]
                self.openlock.release()
        logger.info(self.openorders)

    def add_new_liquid_orders(self,orders,levels):
        rightorders = []
        for order in orders:
            if order != -1:
                rightorders.append(str(order))
        neworders = self.okcoin.get_order_info(self.contract_type, rightorders)
        logger.info(neworders)
        logger.info(levels)
        if neworders.has_key('orders'):
            if self.liquidlock.acquire():
                for order in neworders['orders']:
                    for level in levels:
                        if order['price'] == level[1]:
                            self.liquidorders[order['order_id']] = [order,level[2],level[0]]
                self.liquidlock.release()
        logger.info("###########fuck you")

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


    def submit_buy_order(self):
        while 1:
            trade_back = []
            try:
                if not self.status:
                    logger.info("###############################Higher 平仓 thread shutdown");
                    break
                if not self.event.isSet(): #停止信号
                    logger.info("###############################Higher 平仓 thread stopped");
                    self.event.wait()
                if not self.liquidevent.isSet():#平仓暂停
                    logger.info("###############################Higher 平仓 suspend");
                    self.liquidevent.wait()
                start = datetime.datetime.now()
                price = self.market.q_bids_price.get()
                end = datetime.datetime.now()
                logger.info("############buy order1 spend" + bytes(((end - start).microseconds) / 1000.0) + "milli seconds ")
                escape = (datetime.datetime.now() - self.lastUpdate).seconds
                if escape > 5:
                    self.waitevent.clear()
                    self.waitevent.wait()
                reopen_orders = []
                subedorders = [0, 0, 0]
                tosuborders = [0, 0, 0]
                couldsub = self.ok_sell_balance
                if self.split_position:
                    highest = self.split_position[len(self.split_position) - 1]
                    if self.liquidorders:
                        for order in self.liquidorders.values():
                            if order[0]['status'] != 2 and order[0]['status'] != -1:  # 排除全部成交、已撤单成功的，其它全都视为已提交等待成交订单
                                subedorders[order[2]] += order[0]['amount'] - order[0]['deal_amount']
                        couldsub = self.ok_sell_balance - sum(subedorders)  # 剩余可提交订单

                        bidprice = round(price + highest[1] - self.expected_profit,2)
                        for order in self.liquidorders.values():
                            logger.info("######### order " + str(order[0]['order_id']) + "level = " + str(order[2]) + " 平仓价 = " + str(order[0]['price']) + " 重开价 =" + str(round(order[0]['price'] - bidprice - 5*order[2],2)))
                            if not (-0.1 < round(order[0]['price'] - bidprice - 5*order[2],2) < order[1]):  # 向上波动价格小于1.5 且没有成交情况下，无需重新下单 openorder[order,ignoreprice,level]
                                reopen_orders.append(order)

                            if couldsub < self.deal_amount and not order[2]:
                                if order not in reopen_orders:
                                    reopen_orders.append(order)  # 所剩提交空间不多，取消全部2,3级订单

                        if reopen_orders: #存在需要重新提交订单，以及强制取消订单
                            ids = []
                            for i in reopen_orders:
                                ids.append(str(i[0]['order_id']))
                            if self.sublock.acquire():
                                logger.info("###sublock acqurie")
                                escape = (datetime.datetime.now() - self.lastsub).microseconds
                                if escape < 430000:
                                    time.sleep(round((430000 - escape) / 1000000.0, 2))
                                    self.lastsub = datetime.datetime.now()
                                self.sublock.release()
                                logger.info("#####sublock released")
                            cancel_result = self.okcoin.cancel_all_orders(self.contract_type, ids)#一次最多3笔
                            logger.info(cancel_result)
                            self.update_orders_status(-1)

                            for order in self.openorders.values(): #取消后需重新刷新 subedorders 及 couldsub
                                if order[0]['status'] != 2 and order[0]['status'] != -1:  # 排除全部成交、已撤单成功的，其它全都视为已提交等待成交订单
                                    subedorders[order[2]] += order[0]['amount'] - order[0]['deal_amount']
                            couldsub = self.MAX_Size - self.ok_sell_balance - sum(subedorders)  # 剩余可提交订单

                    logger.info(reopen_orders)
                    logger.info(subedorders)
                    if reopen_orders or self.liquidstatus or not sum(subedorders):  # reopen不为空 或者 有订单已完成,或者没有没有挂单
                        if not subedorders[0] and couldsub > 0:#一级为零
                            tosuborders[0] = self.deal_amount if couldsub > self.deal_amount else couldsub
                            couldsub -= tosuborders[0]
                        if not subedorders[1] and (couldsub-self.deal_amount*3) > 0:
                            tosuborders[1] = self.deal_amount*2
                            couldsub -= tosuborders[1]
                        if not subedorders[2] and couldsub-self.deal_amount*2 > 0:
                            tosuborders[2] = self.deal_amount
                            couldsub -= tosuborders[2]
                        if sum(tosuborders):
                            price = round(price + highest[1] - self.expected_profit,2)
                            tradlist = []
                            levels = []
                            for x in [0,1,2]:
                                if tosuborders[x]:
                                    tradlist.append([round(price - 5*x,2),tosuborders[x]])
                                    levels.append([x,round(price - 5*x,2),1.5*x+1.5])
                            # 提交订单
                            logger.info(tradlist)
                            logger.info("下单，下单，平平平 amount= " + str(tradlist) + "mex price = " + bytes(price + self.expected_profit - highest[1]) + " coin price = " + bytes(price) + " baiss= " + bytes(highest[1]))
                            trade_back = self.okcoin.batch_trade(self.contract_type,tradlist, 4)
                            logger.info(trade_back)
                            self.add_new_liquid_orders(trade_back,levels)
                    if self.liquidstatus:
                        self.liquidstatus = False
            except Exception, e:
                logger.info(trade_back)
                logger.info(e)
                logger.info("平平平oid error")
                self.okcoin.cancel_all(self.contract_type)

                    # self.okcoin.cancel_all(self.contract_type)
            finally:
                pass
                end = datetime.datetime.now()
                logger.info("############sell order3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")


    def submit_sell_order(self):
        while 1:
            trade_back = []
            try:
                if not self.status:
                    logger.info("###############################Higher 开仓 thread shutdown");
                    break
                if not self.event.isSet(): #停止信号
                    logger.info("###############################Higher 开仓 thread stopped");
                    self.event.wait()
                if not self.openevent.isSet():#开仓暂停
                    logger.info("###############################Higher 开仓 suspend");
                    self.openevent.wait()
                start = datetime.datetime.now()
                price = self.market.q_asks_price.get()
                end = datetime.datetime.now()
                logger.info("############sell order1 spend " + bytes(((end - start).microseconds) / 1000.0) + " milli seconds ")
                escape = (datetime.datetime.now() - self.lastUpdate).seconds
                if escape > 5:
                    self.waitevent.clear()
                    self.waitevent.wait()
                reopen_orders = []
                subedorders = [0, 0, 0]
                tosuborders = [0, 0, 0]
                couldsub = self.MAX_Size - self.ok_sell_balance
                logger.info(self.openorders.values())
                if self.openorders:
                    for order in self.openorders.values():
                        if order[0]['status'] != 2 and order[0]['status'] != -1:  # 排除全部成交、已撤单成功的，其它全都视为已提交等待成交订单
                            subedorders[order[2]] += order[0]['amount'] - order[0]['deal_amount']
                    couldsub = self.MAX_Size - self.ok_sell_balance - sum(subedorders) #剩余可提交订单

                    for order in self.openorders.values():
                        logger.info("######### order "+str(order[0]['order_id']) + "level = " +str(order[2]) +" 开仓价 = " + str(order[0]['price']) +" 重开价 ="+ str(round(price+ self.basis_create +self.expected_profit*order[2]*0.5,2)))
                        if not(-0.1< (round(price+ self.basis_create +self.expected_profit*order[2]*0.5,2)) - order[0]['price'] <order[1]):  #向上波动价格小于1.5 且没有成交情况下，无需重新下单 openorder[order,ignoreprice,level]
                            reopen_orders.append(order)
                        if couldsub < self.deal_amount and not order[2]:
                            if order not in reopen_orders:
                                reopen_orders.append(order) #所剩提交空间不多，取消全部2,3级订单
                    logger.info(reopen_orders)
                    if reopen_orders: #存在需要重新提交订单，以及强制取消订单
                        ids = []
                        for i in reopen_orders:
                            ids.append(str(i[0]['order_id']))
                        if self.sublock.acquire():
                            logger.info("###sublock acqurie")
                            escape = (datetime.datetime.now() - self.lastsub).microseconds
                            if escape < 430000:
                                time.sleep(round((430000 - escape) / 1000000.0, 2))
                                self.lastsub = datetime.datetime.now()
                            self.sublock.release()
                            logger.info("#####sublock released")
                        cancel_result = self.okcoin.cancel_all_orders(self.contract_type, ids)#一次最多3笔
                        logger.info(cancel_result)

                        #if couldsub < self.deal_amount*2
                        self.update_orders_status(1)
                        logger.info("#######不让更新？")
                        for order in self.openorders.values(): #取消后需重新刷新 subedorders 及 couldsub
                            if order[0]['status'] != 2 and order[0]['status'] != -1:  # 排除全部成交、已撤单成功的，其它全都视为已提交等待成交订单
                                subedorders[order[2]] += order[0]['amount'] - order[0]['deal_amount']
                        couldsub = self.MAX_Size - self.ok_sell_balance - sum(subedorders)  # 剩余可提交订单

                if reopen_orders or self.openstatus or not sum(subedorders): #reopen不为空 或者 有订单已完成,或者没有挂单
                    if not subedorders[0] and couldsub > 0:#一级为零
                        tosuborders[0] = self.deal_amount if couldsub > self.deal_amount else couldsub
                        couldsub -= tosuborders[0]
                    if not subedorders[1] and (couldsub-self.deal_amount*3) > 0:
                        tosuborders[1] = self.deal_amount*2
                        couldsub -= tosuborders[1]
                    if not subedorders[2] and couldsub-self.deal_amount*2 > 0:
                        tosuborders[2] = self.deal_amount
                        couldsub -= tosuborders[2]
                    logger.info(tosuborders)
                    if sum(tosuborders):
                        price = round(price + self.basis_create,2)
                        tradlist = []
                        levels = []
                        for x in [0,1,2]:
                            if tosuborders[x]:
                                tradlist.append([round(price + self.expected_profit*x*0.5,2),tosuborders[x]])
                                levels.append([x,round(price + self.expected_profit*x*0.5,2),3*x+1.5])
                        # 提交订单
                        logger.info(tradlist)
                        logger.info("下单，下单，买买买 amount= " + str(tradlist) + "mex price = " + bytes(price - self.basis_create) + " coin price= " + bytes(price) + " basis_create= " + bytes(self.basis_create))
                        trade_back = self.okcoin.batch_trade(self.contract_type,tradlist, 2)
                        logger.info(trade_back)
                        self.add_new_open_orders(trade_back,levels)
                if self.openstatus:
                    self.openstatus = False

            except Exception, e:
                logger.info(trade_back)
                logger.info(e)
                logger.info("买买买oid error")
                self.okcoin.cancel_all(self.contract_type)
            finally:
                pass
                end = datetime.datetime.now()
                logger.info("############sell order3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")


            # okprice = self.conn.get(constants.ok_mex_price)
            # logger.info("#######current ok bid price =" + bytes(okprice[4]) + " while wanna 开空 price=" + bytes(price))
            # if (price - okprice[4] > 5):
            #     continue


    def setting_check(self):
        try:
            fastformh = self.conn.get("fastformh")
            if fastformh:
                logger.info("############fast formh setting################")
                beforestatus = self.event.isSet()  #
                if beforestatus:
                    self.event.clear()  # 没停的话，先暂停
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
                self.conn.delete("fastformh")
                if beforestatus:
                    self.event.set()

                logger.info("###########now event status="+str(self.event.isSet()))
                logger.info("###########now openevent status=" + str(self.openevent.isSet()))
                logger.info("###########now liquidevent status=" + str(self.liquidevent.isSet()))
                logger.info("###########now waitevent status=" + str(self.waitevent.isSet()))

        except:
            pass


    def start(self,basis=None):
        if not self.status:
            logger.info("###############################Higher跑起来了，哈哈哈");
            self.status = True
            self.openevent.set()
            self.liquidevent.set()
            self.conn.set(constants.higher_buy_run_key, True)
            self.conn.set(constants.higher_sell_run_key, True)

            if basis:
                self.conn.set(constants.higher_basic_create_key, basis)
                self.basis_create = basis

            sell = threading.Thread(target=self.submit_sell_order)
            sell.setDaemon(True)
            sell.start()

            buy = threading.Thread(target=self.submit_buy_order)
            buy.setDaemon(True)
            buy.start()

            # check = threading.Thread(target=self.setting_check)
            # check.setDaemon(True)
            # check.start()
        self.event.set()  # 开启

    def stop(self):
        self.event.clear()
        logger.info("###############################Higher stopped");

    def stopOpen(self):
        self.openevent.clear()
        run = self.conn.get(constants.higher_buy_run_key)
        if run:
            self.conn.set(constants.higher_buy_run_key,False)

    def remainOpen(self):
        self.openevent.set()
        run = self.conn.get(constants.higher_buy_run_key)
        if not run:
            self.conn.set(constants.higher_buy_run_key,True)

    def stopLiquid(self):
        self.liquidevent.clear()
        logger.info("###########now liquidevent status=" + str(self.event.isSet()))
        run = self.conn.get(constants.higher_sell_run_key)
        if run:
            self.conn.set(constants.higher_sell_run_key,False)

    def remainLiquid(self):
        self.liquidevent.set()
        run = self.conn.get(constants.higher_sell_run_key)
        if not run:
            self.conn.set(constants.higher_sell_run_key,True)

    def liquidAll(self):
        if self.split_position:
            amount = 0
            for x in self.split_position:
                amount += x[0]
            self.okcoin.tradeRival(constants.higher_contract_type, amount, 4)


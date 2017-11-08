﻿# coding=utf-8
import sys
import Queue
import datetime
import logging.handlers
import threading
import time
import constants as constants
from market_maker import bitmex
import okcoinliquidation as liquid
import marketPrice
import api.okcoin_com_api as okcom
from db.rediscon import Conn_db

LOG_FILE = sys.path[0] + '/push.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024 * 8, backupCount=20)  # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('root')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)

class mexpush(object):
    def __init__(self,max_size,deal_amount,high_or_low,basis_create,profit,density):
        self.basis_create = basis_create
        self.profit = profit
        self.density = density
        self.conn = Conn_db()
        mex_key = constants.mex_key
        mex_skey = constants.mex_skey
        key = constants.coin_key
        skey = constants.coin_skey
        self.mex = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',symbol=constants.higher_mex_contract_type, apiKey=mex_key, apiSecret=mex_skey)
        self.okcoin = okcom.OkCoinComApi(key, skey)
        self.liquidation = liquid.okcoinLiquidation(self.mex,self,self.okcoin)
        self.status = False
        self.market = marketPrice.MarketPrice()
        self.market.start()
        self.max_size = max_size
        self.deal_amount = deal_amount
        self.detected_time = None
        self.openevent = threading.Event()  # 开仓暂停
        self.liquidevent = threading.Event() #平仓暂停

        if "high" == high_or_low:
            self.openhigh = True
            self.openlow = False
        else:
            self.openhigh = False
            self.openlow = True

        self.high_order = None
        self.high_liquid_order = None
        self.low_order = None
        self.low_liquid_order = None
        self.high_split_position = self.conn.get(constants.mexpush_higher_position)
        self.low_split_position = self.conn.get(constants.mexpush_lower_position)
        if not self.high_split_position:
            self.high_split_position = []
        if not self.low_split_position:
            self.low_split_position = []
        self.on_set = None
        self.on_liquid = None
        self.cur_liquid_diff = None
        self.balancelock = threading.Lock()
        mexpos = self.mex.position(constants.higher_mex_contract_type)
        okpos = self.okcoin.get_position(constants.higher_contract_type)['holding'][0]
        self.init_high_diff = round(mexpos['currentQty']/100.0,0)-okpos['sell_amount']

    def is_openhigh(self):
        #TODO 策略判断,比如差价过低，只做low
        if self.openhigh:

            recent = self.conn.get("recent2")
            recent.reverse()
            opendiff = round(recent[0][4] - recent[0][1], 2)
            curhold = 0.01
            start = self.basis_create
            if self.high_split_position:
                curhold = sum(i[0] for i in self.high_split_position)
                start = self.high_split_position[0][1]
            if ((opendiff - start) / curhold) > self.density:
                if self.cur_liquid_diff is not None:
                    logger.debug("opendiff = "+str(opendiff) +" cur_liquid_diff = "+str(self.cur_liquid_diff))
                    if opendiff - self.cur_liquid_diff > self.profit+5:
                        return True
                else:
                    if opendiff > self.basis_create:
                        if self.high_split_position:
                            highest = self.high_split_position[len(self.high_split_position) - 1]
                            logger.debug("opendiff = " + str(opendiff) + " highest[1] = " + str(highest[1]))
                            if opendiff > highest[1]+0.3:
                                return True
            else:
                logger.debug("###############density not fill##############")
        return False

    def is_openlow(self):
        # TODO 策略判断 1有low挂单，挂单是否需要重新挂 2 均线趋势
        if self.openlow:
            recent = self.conn.get("recent2")
            recent.reverse()
            opendiff = round(recent[0][3] - recent[0][2], 2)
            #if opendiff < self.basis_create:
            if self.cur_liquid_diff is not None:
                if opendiff - self.cur_liquid_diff < -(self.profit+5):
                    return True
            else:
                if opendiff < self.basis_create:
                    if self.low_split_position:
                        lowest = self.low_split_position[len(self.low_split_position) - 1]
                        if opendiff < lowest[1]-0.3:
                            return True
        return False

    def high_price(self,depth):
        pass

    def holdPosition(self):
        oldpos = self.mex.position(constants.higher_mex_contract_type).copy()
        while 1:
            time.sleep(0.5)
            pos = self.mex.position(constants.higher_mex_contract_type).copy()
            logger.debug(pos['currentQty']-oldpos['currentQty'])
            logger.debug(pos)
            if pos['currentQty']-oldpos['currentQty'] >0:#okcoin四舍五入建仓
                self.detected_time = time.time()
                if not self.openevent.isSet():
                    self.openevent.set()
                okpos = self.okcoin.get_position(constants.higher_contract_type)['holding'][0]
                okqty = round(pos['currentQty'] / 100.0, 2) - okpos['sell_amount']-self.init_high_diff
                logger.debug("okqty="+str(okqty))
                depth = self.market.get_depth_5_price()
                if(okqty>0.5):
                    openqty = pos['currentQty']-oldpos['currentQty']
                    #openprice = round((pos['avgCostPrice']*pos['currentQty']-oldpos['avgCostPrice']*oldpos['currentQty'])/openqty,2) mexprice 換成一
                    self.on_set = {"settime":time.time(),"mexprice":depth[0][0][0],"mexqty":openqty,"okqty":int(round(okqty,0))}
                    self.liquidation.highopenOrlowliquid()
            if pos['currentQty']-oldpos['currentQty'] <0:#okcoin四舍五入平仓
                self.detected_time = time.time()
                if not self.liquidevent.isSet():
                    self.liquidevent.set()
                okpos = self.okcoin.get_position(constants.higher_contract_type)['holding'][0]
                okqty = round(pos['currentQty'] / 100.0, 2) - okpos['sell_amount']-self.init_high_diff
                logger.debug("okqty=" + str(okqty))
                depth = self.market.get_depth_5_price()
                if (okqty < -0.5):
                    openqty = pos['currentQty'] - oldpos['currentQty']
                    self.on_liquid = {"settime": time.time(), "mexprice": depth[0][0][0],"mexqty":openqty, "okqty": int(round(okqty,0))}
                    self.liquidation.highliquidOrlowopen()
            oldpos = pos

    def openPosition(self):
        while 1:
            # if not self.status:
            #     logger.info("###############################Higher 开仓 thread shutdown");
            #     break
            # if not self.openevent.isSet():#开仓暂停
            #     logger.info("###############################Higher 开仓 suspend");
            #     self.openevent.wait()
            time.sleep(0.5)
            try:
                if self.is_openhigh():
                    depth = self.market.get_depth_5_price()
                    hold = 0
                    if self.high_split_position:
                        hold = sum(i[0] for i in self.high_split_position)
                    if not self.on_set:
                        if abs(hold) < self.max_size:
                            couldopen = True
                            if self.high_order:#已有挂单
                                couldopen = False
                                #nowstatus = self.mex.get(self.high_order['clOrdID'])
                                logger.debug(self.high_order)
                                if self.high_order['price'] < depth[1][1][0] or self.high_order['price'] > depth[0][0][0]:#当前挂单小于买2撤单重新提交;大于卖一 默认已成交
                                    if self.high_order['price'] > depth[0][0][0]:
                                        if time.time() - self.detected_time  > 5.0:
                                            self.openevent.clear()
                                            self.openevent.wait() #啥也别说了，停,直到有人能唤醒你
                                    logger.debug("open price = "+str(self.high_order['price'])+"买2 ="+str(depth[1][1][0]) +" 卖1 ="+str(depth[0][0][0]))
                                    self.mex.cancel(self.high_order['orderID'])
                                    self.high_order = None
                                    couldopen = True
                            if couldopen: #没有挂单或者挂单已取消
                                depth = self.market.get_depth_5_price()
                                self.high_order = self.mex.buy((abs(self.deal_amount) * 100), (depth[1][0][0]))
                        else:
                            logger.debug("#########exceding max size")
                            logger.debug(self.high_split_position)
                            if self.high_order:
                                self.mex.cancel(self.high_order['orderID'])
                                self.high_order = None
                    else:
                        if(time.time()-self.on_set['settime']>60):
                            logger.error("############################### high open order failure "+str(self.on_set));
                else:
                    if self.high_order:
                        self.mex.cancel(self.high_order['orderID'])
                        self.high_order = None
                #/***************** high low 分割线 **************************************************************************************/
                if self.is_openlow():
                    depth = self.market.get_depth_5_price()
                    hold = 0
                    if self.high_split_position:
                        hold = sum(i[0] for i in self.low_split_position)
                    if not self.on_liquid:
                        if abs(hold) < self.max_size:
                            couldopen = True
                            if self.low_order:  # 已有挂单
                                couldopen = False
                                # nowstatus = self.mex.get(self.high_order['clOrdID'])
                                logger.debug(self.low_order)
                                if self.low_order['price'] > depth[0][1][0] or self.low_order['price'] < depth[1][0][0]:  # 当前挂单大于卖2撤单重新提交;小于买一 默认已成交
                                    logger.debug("open price = " + str(self.high_order['price']) + "卖2 =" + str(depth[0][1][0]) + " 买1 =" + str(depth[1][0][0]))
                                    self.mex.cancel(self.low_order['orderID'])
                                    self.low_order = None
                                    couldopen = True
                            if couldopen:  # 没有挂单或者挂单已取消
                                depth = self.market.get_depth_5_price()
                                self.low_order = self.mex.sell((abs(self.deal_amount) * 100), (depth[0][0][0]))
                        else:
                            logger.debug("#########exceding max size")
                            logger.debug(self.low_split_position)
                            if self.low_order:
                                self.mex.cancel(self.low_order['orderID'])
                                self.low_order = None
                    else:
                        if (time.time() - self.on_liquid['settime'] > 60):
                            logger.error("############################### low open order failure " + str(self.on_liquid));
                else:
                    if self.low_order:
                        self.mex.cancel(self.low_order['orderID'])
                        self.low_order = None

            except Exception, e:
                logger.error("exception")
                logger.error(e)

    def liquidPosition(self):
        while 1:
            if not self.on_liquid and self.high_split_position:
                highest = self.high_split_position[len(self.high_split_position) - 1]
                logger.debug("##########highest[1] - current diff ="+str(highest[1] - self.get_cur_high_diff()))
                if self.high_liquid_order:
                    depth = self.market.get_depth_5_price()
                    if self.high_liquid_order['price'] < depth[1][0][0]:  # 当前挂单小于买1 默认成交
                        if time.time() - self.detected_time > 5.0:
                            self.liquidevent.clear()
                            self.liquidevent.wait()  # 啥也别说了，停,直到有人能唤醒你
                        self.high_liquid_order = None
                if highest[1] - self.get_cur_high_diff() < 3: #差价小于3 取消平仓，防止滑点亏损
                    if self.high_liquid_order:
                        self.mex.cancel(self.high_liquid_order['orderID'])
                        self.high_liquid_order = None
                if highest[1] - self.get_cur_high_diff() > self.profit and highest[1] - self.get_1min_high_diff() >3:
                    depth = self.market.get_depth_5_price()
                    if self.high_liquid_order:
                        if self.high_liquid_order['price'] > depth[0][1][0]:#当前挂单大于卖2
                            self.mex.cancel(self.high_liquid_order['orderID'])
                            self.high_liquid_order = self.mex.sell((abs(self.deal_amount) * 100), (depth[0][0][0]))
                    else:
                        self.high_liquid_order = self.mex.sell((abs(self.deal_amount) * 100), (depth[0][0][0]))

            if not self.on_set and self.low_split_position:
                highest = self.low_split_position[len(self.low_split_position) - 1]
                logger.debug("##########lowest[1] - current diff ="+str(highest[1] - self.get_cur_low_diff()))
                if self.low_liquid_order:
                    depth = self.market.get_depth_5_price()
                    if self.low_liquid_order['price'] > depth[0][0][0]:  # 当前挂单小于买1 默认成交
                        self.low_liquid_order = None
                if self.get_cur_low_diff() - highest[1] < 3: #差价小于3 取消平仓，防止滑点亏损
                    if self.low_liquid_order:
                        self.mex.cancel(self.low_liquid_order['orderID'])
                        self.low_liquid_order = None
                if self.get_cur_low_diff() - highest[1] > self.profit and self.get_1min_low_diff() - highest[1] >3:
                    depth = self.market.get_depth_5_price()
                    if self.low_liquid_order:
                        if self.low_liquid_order['price'] < depth[1][1][0]:#当前挂单小于买2
                            self.mex.cancel(self.low_liquid_order['orderID'])
                            self.low_liquid_order = self.mex.buy((abs(self.deal_amount) * 100), (depth[1][0][0]))
                    else:
                        self.low_liquid_order = self.mex.buy((abs(self.deal_amount) * 100), (depth[1][0][0]))
            time.sleep(1)

    def get_cur_high_diff(self):
        recent = self.conn.get("recent2")
        recent.reverse()
        return round(recent[0][3]-recent[0][2],2)

    def get_cur_low_diff(self):
        recent = self.conn.get("recent2")
        recent.reverse()
        return round(recent[0][4]-recent[0][1],2)

    def get_1min_high_diff(self):
        recent = self.conn.get("recent2")
        recent.reverse()
        p1 = sum(i[3] for i in recent[0:30])
        p2 = sum(i[2] for i in recent[0:30])
        return round((p1-p2)/30.0,2)

    def get_1min_low_diff(self):
        recent = self.conn.get("recent2")
        recent.reverse()
        p1 = sum(i[4] for i in recent[0:4])
        p2 = sum(i[1] for i in recent[0:4])
        return round((p1-p2)/4.0,2)

    def recordSet(self,order):
        if self.balancelock.acquire():
            his = self.conn.get(constants.mexpush_trade_his_key)
            if self.openhigh:
                his.append(((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),self.on_set['mexqty'],order["deal_amount"],round(order["price_avg"]-self.on_set["mexprice"],2),1))
                self.high_split_position.append((int(order["deal_amount"]),round(order["price_avg"]-self.on_set["mexprice"],2)))
                self.high_split_position.sort(key=lambda x: x[1])
                self.conn.set(constants.mexpush_higher_position,self.high_split_position)
                self.on_set = None
                logger.info(self.conn.get(constants.mexpush_higher_position))
            if self.openlow:
                self.cur_liquid_diff = order["price_avg"] - self.on_set["mexprice"]
                his.append(((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),self.on_set['mexqty'], order["deal_amount"],round(order["price_avg"]-self.on_set["mexprice"],2),4))
                ammount = order["deal_amount"]
                if self.balancelock.acquire():
                    self.on_set = None
                    while (self.low_split_position and ammount > 0):
                        last_pos = self.low_split_position.pop()
                        ammount = ammount - last_pos[0]
                        if (ammount < 0):
                            self.low_split_position.append((-ammount, last_pos[1]))
                            break
                    if ammount > 0:
                        print "what? sell too much"
                    self.conn.set(constants.mexpush_lower_position, self.low_split_position)
            self.conn.set(constants.mexpush_trade_his_key, his)
            self.balancelock.release()

    def removeSet(self,order):
        if self.balancelock.acquire():
            his = self.conn.get(constants.mexpush_trade_his_key)
            if self.openhigh:
                his.append(((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')), self.on_liquid['mexqty'], order["deal_amount"], round(order["price_avg"] - self.on_liquid["mexprice"], 2), 2))
                self.cur_liquid_diff = order["price_avg"] - self.on_liquid["mexprice"]
                ammount = order["deal_amount"]
                self.on_liquid = None
                while (self.high_split_position and ammount > 0):
                    last_pos = self.high_split_position.pop()
                    ammount = ammount - last_pos[0]
                    if (ammount < 0):
                        self.high_split_position.append((-ammount, last_pos[1]))
                        break
                if ammount > 0:
                    print "what? sell too much"
                self.conn.set(constants.mexpush_higher_position,self.high_split_position)
            if self.openlow:
                his.append(((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),self.on_liquid['mexqty'], order["deal_amount"], round(order["price_avg"] - self.on_liquid["mexprice"], 2), 3))
                self.low_split_position.append((int(order["deal_amount"]), round(order["price_avg"] - self.on_liquid["mexprice"], 2)))
                self.low_split_position.sort(key=lambda x: x[1])
                self.low_split_position.reverse()
                self.conn.set(constants.mexpush_lower_position, self.low_split_position)
                self.on_liquid = None
                logger.info(self.conn.get(constants.mexpush_lower_position))
            self.conn.set(constants.mexpush_trade_his_key, his)
        self.balancelock.release()


    def start(self):
        hold = threading.Thread(target=self.holdPosition)
        hold.setDaemon(True)
        hold.start()
        open = threading.Thread(target=self.openPosition)
        open.setDaemon(True)
        open.start()
        liquid = threading.Thread(target=self.liquidPosition)
        liquid.setDaemon(True)
        liquid.start()


if __name__ == '__main__':
    push = mexpush(28,1,'high',50,9,7)
    push.start()

    while 1:
        try:
            time.sleep(1)
        except Exception as e:
            print "fuck", e
            pass




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

# 自动平仓，按时间、获利优先原则
logger = logging.getLogger('root')
class mexliquidation(object):
    def __init__(self, mex):
        self.mex = mex
        self.hserver = None
        self.lserver = None
        self.startime = datetime.datetime.now()
        self.conn = Conn_db()
        tradehis = self.conn.get(constants.trade_his_key)
        if not tradehis:
            self.conn.set(constants.trade_his_key,[])

    def setServers(self,hserver,lserver):
        self.hserver = hserver
        self.lserver = lserver



    # okprice ok成交价,根据（本次持仓金额-上次持仓金额）/持仓量变化 计算得出，似乎跟实际本次成交均价有出入，咋整
    # price mex 初始挂单价
    # deal_amount 持仓量变化
    # expected_profit 期望获利
    # basis_create 下单时2平台差价
    # direction 方向
    def suborder(self,okprice,price,deal_amount,expected_profit,basis_create,direction):
        if direction == 'buy':
            order = (okprice, price, deal_amount, expected_profit, basis_create, direction)
            buy = threading.Thread(target=self.buyThread, args=(order,))
            buy.setDaemon(True)
            buy.start()
        else:
            order = (okprice, price, deal_amount, expected_profit, basis_create, direction)
            buy = threading.Thread(target=self.sellThread, args=(order,))
            buy.setDaemon(True)
            buy.start()

    def start(self):
        logger.info("mexliquidation 跑起来了，哈哈哈");
        #self.server.test()

    def buyThread(self,order):
        partdel = 0
        slipp = 0
        waiting = 0
        while 1:
            # print self.price+slipp
            rst = None
            try:
                if order[2] > 0:
                    logger.info('###mex买入建仓### price= ' + bytes(order[1]) + " slipp = " + bytes(slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                else:
                    logger.info('###mex卖出平仓### price= ' + bytes(order[1]) + " slipp = " + bytes(slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                rst = self.mex.buy((abs(order[2]) * 100 - partdel), (order[1] + slipp))
                logger.info(rst)
                if rst['ordStatus'] and 'Filled' == rst['ordStatus']:
                    if order[2] > 0:
                        self.hserver.plusUpdate(order[0], rst['avgPx'], order[2])
                        logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(rst['avgPx']) + "##amount=" + bytes(order[2]) + " ##basic_create=" + bytes(order[4]) + "建仓滑点 " + bytes(order[4] - order[0] + rst['avgPx']) + " #######")
                        his = self.conn.get(constants.trade_his_key)
                        his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, order[0], rst['avgPx'],order[2], order[4], order[4] - order[0] + rst['avgPx']))
                        self.conn.set(constants.trade_his_key, his)

                    else:
                        self.lserver.plusUpdate(order[0], rst['avgPx'], order[2])
                        logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(rst['avgPx']) + "##amount=" + bytes(order[2]) + " ##basic_create=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] + order[4] - order[0] + rst['avgPx']) + " #######")
                        his = self.conn.get(constants.trade_his_key)
                        his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, order[0], rst['avgPx'],order[2], order[4], order[3] + order[4] - order[0] + rst['avgPx']))
                        self.conn.set(constants.trade_his_key, his)

                    # logger.info("############"+bytes(order[4])+"以实际成交均价建仓滑点 " + bytes(rst['avgPx'] - order[1]) + " ##############")
                    break
                else:
                    waiting += 1
                    time.sleep(0.5)
                    cel = self.mex.cancel(rst['orderID'])
                    logger.info(cel)
                    if 'Filled' == cel[0]['ordStatus']:
                        if order[2] > 0:
                            self.hserver.plusUpdate(order[0], cel[0]['avgPx'], order[2])
                            logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(cel[0]['avgPx']) + "##amount=" + bytes(order[2]) + " ##basic_create=" + bytes(order[4]) + "建仓以持仓变化均价建仓滑点 " + bytes(order[4] - order[0] + cel[0]['avgPx']) + " #######")

                            his = self.conn.get(constants.trade_his_key)
                            his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, order[0],cel[0]['avgPx'], order[2], order[4], order[4] - order[0] + cel[0]['avgPx']))
                            self.conn.set(constants.trade_his_key, his)
                        else:
                            self.lserver.plusUpdate(order[0], cel[0]['avgPx'], order[2])
                            logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(cel[0]['avgPx']) + "##amount=" + bytes(order[2]) + " ##basic_create=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] + order[4] - order[0] + cel[0]['avgPx']) + " #######")

                            his = self.conn.get(constants.trade_his_key)
                            his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, order[0], cel[0]['avgPx'],order[2], order[4], order[3] + order[4] - order[0] + cel[0]['avgPx']))
                            self.conn.set(constants.trade_his_key, his)

                        # logger.info("############" + bytes(order[4]) + "以实际成交均价建仓滑点 " + bytes(rst['avgPx'] - order[1]) + " ##############")
                        break
                    if 'Canceled' == cel[0]['ordStatus']:
                        if cel[0]['cumQty']:
                            partdel += cel[0]['cumQty']
                            # 应该还有部分成交的情形
                # if waiting % 2 == 0:
                slipp += 10
            except Exception, e:
                logger.info(e)
                if rst:
                    logger.info('###异常订单### orderID =' + rst['orderID'])
                    self.mex.cancel(rst['orderID'])
                break
            finally:
                pass

    def sellThread(self,order):
        partdel = 0
        slipp = 0
        waiting = 0
        while 1:
            # print self.price+slipp
            rst = None
            try:
                if (slipp > order[3]):
                    logger.info("############ " + bytes(order[1]) + " 这单要亏了##############")
                if order[2] > 0:
                    logger.info('###mex卖出开仓### price= ' + bytes(order[1]) + " slipp = " + bytes(slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                else:
                    logger.info('###mex买入平仓### price= ' + bytes(order[1]) + " slipp = " + bytes(slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                rst = self.mex.sell((abs(order[2]) * 100 - partdel), (order[1] - slipp))
                logger.info(rst)
                if rst['ordStatus'] and 'Filled' == rst['ordStatus']:
                    if order[2] > 0:
                        self.lserver.plusUpdate(order[0], rst['avgPx'], order[2])
                        logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(rst['avgPx']) + "##amount=" + bytes(order[2]) + " ##liquid_bais=" + bytes(order[4]) + "建仓滑点 " + bytes(order[0] - rst['avgPx'] - order[4]) + " #######")

                        his = self.conn.get(constants.trade_his_key)
                        his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0],rst['avgPx'], order[2], order[4], order[0] - rst['avgPx'] - order[4]))
                        self.conn.set(constants.trade_his_key, his)
                    else:
                        self.hserver.plusUpdate(order[0], rst['avgPx'], order[2])
                        logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(rst['avgPx']) + "##amount=" + bytes(order[2]) + " ##liquid_bais=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] - order[4] + order[0] - rst['avgPx']) + " #######")
                        his = self.conn.get(constants.trade_his_key)
                        his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0], rst['avgPx'],order[2], order[4], order[3] - order[4] + order[0] - rst['avgPx']))
                        self.conn.set(constants.trade_his_key, his)
                    break
                else:
                    waiting += 1
                    time.sleep(0.5)
                    cel = self.mex.cancel(rst['orderID'])
                    if order[2] > 0:
                        logger.info('###mex2秒后取消卖出建仓###')
                    else:
                        logger.info('###mex2秒后取消卖出平仓###')
                    logger.info(cel)
                    if 'Filled' == cel[0]['ordStatus']:  # 已经成交无法取消了，哈哈哈
                        if order[2] > 0:
                            self.lserver.plusUpdate(order[0], cel[0]['avgPx'], order[2])
                            logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(cel[0]['avgPx']) + "##amount=" + bytes(order[2]) + " ##liquid_bais=" + bytes(order[4]) + "建仓滑点 " + bytes(order[0] - cel[0]['avgPx'] - order[4]) + " #######")
                            his = self.conn.get(constants.trade_his_key)
                            his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0],cel[0]['avgPx'], order[2], order[4], order[0] - cel[0]['avgPx'] - order[4]))
                            self.conn.set(constants.trade_his_key, his)
                        else:
                            self.hserver.plusUpdate(order[0], cel[0]['avgPx'], order[2])
                            logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(cel[0]['avgPx']) + "##amount=" + bytes(order[2]) + " ##liquid_bais=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] - order[4] + order[0] - cel[0]['avgPx']) + " #######")
                            his = self.conn.get(constants.trade_his_key)
                            his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0],cel[0]['avgPx'],order[2], order[4], order[3] - order[4] + order[0] - cel[0]['avgPx']))
                            self.conn.set(constants.trade_his_key, his)
                        break
                    # 应该还有部分成交的情形
                    if 'Canceled' == cel[0]['ordStatus']:
                        if cel[0]['cumQty']:
                            partdel += cel[0]['cumQty']
                # if waiting % 6 == 0:
                slipp += 10
            except Exception, e:
                logger.info(e)
                if rst:
                    logger.info('###异常订单### orderID =' + rst['orderID'])
                    self.mex.cancel(rst['orderID'])
                break
            finally:
                pass


if __name__ == '__main__':
    LOG_FILE = 'test.log'
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5)  # 实例化handler
    fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'


    formatter = logging.Formatter(fmt)  # 实例化formatter
    handler.setFormatter(formatter)  # 为handler添加formatter

    logger = logging.getLogger('tst')  # 获取名为tst的logger
    logger.addHandler(handler)  # 为logger添加handler
    logger.setLevel(logging.DEBUG)

    mex2 = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',
                         symbol='XBTM17', apiKey="zIVjSm0kq6U7jDFXci9R7ka3", apiSecret="T3u98kN4pfvwFQztpmlE6qJQtKOr92dFiZeb8B2mRmHw0GIB")
    liq = mexliquidation(mex2)
    liq.start()
# coding=utf-8
import sys

reload(sys)
sys.setdefaultencoding('utf8')
import Queue
import datetime
import logging.handlers
import threading
import time
from db.rediscon import Conn_db
import constants as constants
from market_maker import bitmex

# 自动平仓，按时间、获利优先原则
logger = logging.getLogger('tst')
class mexliquidation(object):
    def __init__(self, mex,server):
        self.mex = mex
        self.server = server
        self.startime = datetime.datetime.now()
        self.buyqueue = Queue.Queue(10)
        self.sellqueue = Queue.Queue(10)
        self.conn = Conn_db()
        tradehis = self.conn.get(constants.trade_his_key)
        if not tradehis:
            self.conn.set(constants.trade_his_key,[])



    # okprice ok成交价,根据（本次持仓金额-上次持仓金额）/持仓量变化 计算得出，似乎跟实际本次成交均价有出入，咋整
    # price mex 初始挂单价
    # deal_amount 持仓量变化
    # expected_profit 期望获利
    # basis_create 下单时2平台差价
    # direction 方向
    def suborder(self,okprice,price,deal_amount,expected_profit,basis_create,direction):
        if direction == 'buy':
            self.buyqueue.put((okprice,price,deal_amount,expected_profit,basis_create,direction))
        else:
            self.sellqueue.put((okprice, price, deal_amount, expected_profit,basis_create, direction))

    def start(self):
        logger.info("老子跑起来了，哈哈哈");
        #self.server.test()
        buy = threading.Thread(target=self.liquidBuy)
        buy.setDaemon(True)
        buy.start()

        sell = threading.Thread(target=self.liquidSell)
        sell.setDaemon(True)
        sell.start()


    def liquidBuy(self):
        while(1):
            try:
                partdel = 0
                slipp = 0
                waiting = 0
                order = self.buyqueue.get()
                while 1:
                    #print self.price+slipp
                    rst =None
                    try:
                        if order[2] > 0:
                            logger.info('###mex买入建仓### price= '+bytes(order[1])+" slipp = "+bytes(slipp)+" amount= "+bytes(abs(order[2]) * 100-partdel))
                        else:
                            logger.info('###mex卖出平仓### price= ' + bytes(order[1]) + " slipp = " + bytes(
                                slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                        rst = self.mex.buy((abs(order[2]) * 100-partdel),(order[1]+slipp))
                        logger.info(rst)
                        if rst['ordStatus'] and 'Filled' == rst['ordStatus']:
                            self.server.plusUpdate(order[0], rst['avgPx'], order[2])
                            if order[2] > 0:
                                logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(
                                    rst['avgPx']) + "##amount="+bytes(order[2])+" ##basic_create=" + bytes(order[4]) + "建仓滑点 " + bytes(
                                    order[4] - order[0] + rst['avgPx']) + " #######")
                                his = self.conn.get(constants.trade_his_key)
                                his.append((datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S'),1,order[0],rst['avgPx'],order[2],order[4],order[4] - order[0] + rst['avgPx']))
                                self.conn.set(constants.trade_his_key,his)

                            else:
                                logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(
                                rst['avgPx']) + "##amount="+bytes(order[2])+" ##basic_create=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] +order[4] - order[0] + rst['avgPx']) + " #######")
                                his = self.conn.get(constants.trade_his_key)
                                his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),1, order[0], rst['avgPx'],
                                            order[2], order[4], order[3] +order[4] - order[0] + rst['avgPx']))
                                self.conn.set(constants.trade_his_key, his)

                            #logger.info("############"+bytes(order[4])+"以实际成交均价建仓滑点 " + bytes(rst['avgPx'] - order[1]) + " ##############")
                            break
                        else:
                            waiting += 4
                            time.sleep(1)
                            cel = self.mex.cancel(rst['orderID'])
                            logger.info(cel)
                            if 'Filled' == cel[0]['ordStatus']:
                                self.server.plusUpdate(order[0],rst['avgPx'],order[2])
                                if order[2] > 0:
                                    logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(
                                        rst['avgPx']) + "##amount="+bytes(order[2])+" ##basic_create=" + bytes(order[4]) + "建仓以持仓变化均价建仓滑点 " + bytes(
                                        order[4] - order[0] + rst['avgPx']) + " #######")

                                    his = self.conn.get(constants.trade_his_key)
                                    his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, order[0],
                                                rst['avgPx'], order[2], order[4], order[4] - order[0] + rst['avgPx']))
                                    self.conn.set(constants.trade_his_key, his)
                                else:
                                    logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(
                                        rst['avgPx']) + "##amount="+bytes(order[2])+" ##basic_create=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] + order[4] - order[0] + rst['avgPx']) + " #######")

                                his = self.conn.get(constants.trade_his_key)
                                his.append(
                                    (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1, order[0], rst['avgPx'],
                                     order[2], order[4], order[3] + order[4] - order[0] + rst['avgPx']))
                                self.conn.set(constants.trade_his_key, his)

                                #logger.info("############" + bytes(order[4]) + "以实际成交均价建仓滑点 " + bytes(rst['avgPx'] - order[1]) + " ##############")
                                break
                            #应该还有部分成交的情形
                        if waiting % 6 == 0:
                            slipp += 3
                    except Exception, e:
                        logger.info(e)
                        logger.info('###异常订单### orderID =' + rst['orderID'])
                        self.mex.cancel(rst['orderID'])
                        break
                    finally:
                        pass
            except Exception, e:
                logger.info("########what the fuck error############")
                logger.info(e)
                pass


    def liquidSell(self):
        while(1):
            try:
                partdel = 0
                slipp = 0
                waiting = 0
                order = self.sellqueue.get()
                while 1:
                    #print self.price+slipp
                    rst = None
                    try:
                        if(slipp>order[3]):
                            logger.info("############ "+bytes(order[1])+" 这单要亏了##############")
                        if order[2] > 0:
                            logger.info('###mex卖出开仓### price= ' + bytes(order[1]) + " slipp = " + bytes(slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                        else :
                            logger.info('###mex买入平仓### price= ' + bytes(order[1]) + " slipp = " + bytes(slipp) + " amount= " + bytes(abs(order[2]) * 100 - partdel))
                        rst = self.mex.sell((abs(order[2]) * 100-partdel),(order[1]-slipp))
                        logger.info(rst)
                        if rst['ordStatus'] and 'Filled' == rst['ordStatus']:
                            self.server.plusUpdate(order[0], rst['avgPx'], order[2])
                            if order[2] > 0:
                                logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(
                                    rst['avgPx']) + "##amount="+bytes(order[2])+" ##liquid_bais=" + bytes(order[4]) + "建仓滑点 " + bytes(
                                    order[0] - rst['avgPx'] - order[4]) + " #######")

                                his = self.conn.get(constants.trade_his_key)
                                his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0],
                                            rst['avgPx'], order[2], order[4], order[0] - rst['avgPx'] - order[4]))
                                self.conn.set(constants.trade_his_key, his)
                            else:
                                logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(rst['avgPx']) + "##amount="+bytes(order[2])+" ##liquid_bais=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] + order[4] - order[0] + rst['avgPx']) + " #######")
                                his = self.conn.get(constants.trade_his_key)
                                his.append(
                                    (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0], rst['avgPx'],
                                     order[2], order[4], order[3] + order[4] - order[0] + rst['avgPx']))
                                self.conn.set(constants.trade_his_key, his)
                            break
                        else:
                            waiting += 4
                            time.sleep(1)
                            cel = self.mex.cancel(rst['orderID'])
                            if order[2] > 0:
                                logger.info('###mex2秒后取消卖出建仓###')
                            else:
                                logger.info('###mex2秒后取消卖出平仓###')
                            logger.info(cel)
                            if 'Filled' == cel[0]['ordStatus']:#已经成交无法取消了，哈哈哈
                                self.server.plusUpdate(order[0], rst['avgPx'], order[2])
                                if order[2] > 0:
                                    logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(
                                        rst['avgPx']) + "##amount="+bytes(order[2])+" ##liquid_bais=" + bytes(order[4]) + "建仓滑点 " + bytes(
                                        order[0] - rst['avgPx'] - order[4]) + " #######")
                                    his = self.conn.get(constants.trade_his_key)
                                    his.append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0],
                                                rst['avgPx'], order[2], order[4], order[0] - rst['avgPx'] - order[4]))
                                    self.conn.set(constants.trade_his_key, his)
                                else:
                                    logger.info("#####okcoin=" + bytes(order[0]) + " #####mex=" + bytes(rst['avgPx']) + "##amount="+bytes(order[2])+" ##liquid_bais=" + bytes(order[4]) + "平仓滑点 " + bytes(order[3] + order[4] - order[0] + rst['avgPx']) + " #######")
                                    his = self.conn.get(constants.trade_his_key)
                                    his.append(
                                        (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2, order[0],
                                         rst['avgPx'],
                                         order[2], order[4], order[3] + order[4] - order[0] + rst['avgPx']))
                                    self.conn.set(constants.trade_his_key, his)
                                break
                            #应该还有部分成交的情形
                        if waiting % 6 == 0:
                            slipp += 3
                    except Exception:
                        logger.info('###异常订单### orderID ='+rst['orderID'])
                        self.mex.cancel(rst['orderID'])
                        break
                    finally:
                        pass
            except Exception, e:
                logger.info("########what the fuck error############")
                logger.info(e)
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
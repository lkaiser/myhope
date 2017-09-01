# -*- coding: utf-8 -*-

import logging.handlers
import threading
import time
import datetime


import constants as constants

from db.rediscon import Conn_db
logger = logging.getLogger('root')  # 获取名为tst的logger

class HoldPostion(object):
    def __init__(self, okcoin, market, mexliquidation, hserver,
                 lserver):
        self.okcoin = okcoin
        self.mexliquidation = mexliquidation
        self.market = market
        self.hserver = hserver
        self.lserver = lserver
        self.conn = Conn_db()
        logger.info("########### position init ##########")

    def position_mon(self):
        init_holding = None
        okposition = self.okcoin.get_position(constants.higher_contract_type)['holding']
        if okposition:
            init_holding = okposition[0]
        while 1:
            try:
                new_holding = self.okcoin.get_position(constants.higher_contract_type)['holding'][0]
                h_amount_change = new_holding['sell_amount'] - init_holding['sell_amount']
                l_amount_change = new_holding['buy_amount'] - init_holding['buy_amount']
                logger.info("ok_sell_balance="+bytes(self.hserver.ok_sell_balance)+"h_amount_change = "+bytes(h_amount_change))
                logger.info("ok_buy_balance=" + bytes(self.lserver.ok_sell_balance) + "l_amount_change = " + bytes(l_amount_change))
                h_basis_create = self.hserver.basis_create
                l_basis_create = self.lserver.basis_create
                if h_amount_change != 0 or l_amount_change != 0:
                    logger.info(init_holding)
                    logger.info(new_holding)
                    self.hserver.flush_status(h_amount_change)
                    self.lserver.flush_status(l_amount_change)
                # OKcoin挂单成交后，mex立刻以市价做出反向操作
                if h_amount_change > 0: #ok卖单变化，higher
                    holdokprice = self.hserver.get_deal_price(h_amount_change)
                    #holdokprice = (new_holding['sell_price_avg'] * (new_holding['sell_amount']) - init_holding['sell_price_avg'] * (init_holding['sell_amount'])) / h_amount_change
                    okprice = holdokprice
                    sell_price = round(self.market.mex_bids_price + 8, 1)  # 以成交为第一目的
                    logger.info("avarage ok deal price" + bytes(okprice) + " while mex bid price =" + bytes(self.market.mex_bids_price))
                    logger.info("################ammout 增加了 " + bytes(h_amount_change) + "，持仓变化如下 #######################")
                    #self.hserver.up_basis_create(h_amount_change)
                    self.mexliquidation.suborder(okprice, sell_price, h_amount_change, self.hserver.expected_profit, h_basis_create, 'buy')
                if h_amount_change < 0:  # 有仓位被平
                    #okprice = self.hserver.lastevenuprice # 木有啥好办法，取个近似值吧
                    okprice = self.hserver.get_deal_price(h_amount_change) # 好办法来了
                    buy_price = round(self.market.mex_asks_price - 8, 1)
                    # 按bais价格从高到低减,排序
                    last_pos = self.hserver.update_split_position(h_amount_change)
                    self.mexliquidation.suborder(okprice, buy_price, h_amount_change, self.hserver.expected_profit, last_pos[1], 'sell')

                if l_amount_change > 0:
                    holdokprice = (new_holding['buy_price_avg'] * new_holding['buy_amount'] - init_holding['buy_price_avg'] * init_holding['buy_amount']) / l_amount_change
                    okprice = holdokprice
                    sell_price = round(self.market.mex_bids_price - 8, 1)  # 以成交为第一目的
                    logger.info("avarage ok deal price" + bytes(okprice) + " while mex bid price =" + bytes(self.market.mex_bids_price))
                    logger.info("################ammout 增加了 " + bytes(l_amount_change) + "，持仓变化如下 #######################")
                    #self.lserver.up_basis_create(h_amount_change)
                    self.mexliquidation.suborder(okprice, sell_price, l_amount_change, self.lserver.expected_profit, l_basis_create, 'sell')
                if l_amount_change <0:
                    okprice = self.lserver.lastevenuprice
                    buy_price = round(self.market.mex_asks_price + 8, 1)
                    # 按bais价格从高到低减,排序
                    last_pos = self.lserver.update_split_position(l_amount_change)
                    self.mexliquidation.suborder(okprice, buy_price, l_amount_change, self.lserver.expected_profit, last_pos[1], 'buy')



                init_holding = new_holding
            except Exception, e:
                time.sleep(1.25)
                logger.info(e)
                self.okcoin.cancel_all(constants.higher_contract_type)
            time.sleep(0.5)
            # end = datetime.datetime.now()
            # logger.info("############position3 spend" + bytes(((end - start).microseconds) / 1000.0) + " milli seconds")

    def start(self):
        logger.info("########### what the fuck wrong ##########")
        pm = threading.Thread(target=self.position_mon)
        pm.setDaemon(True)
        pm.start()
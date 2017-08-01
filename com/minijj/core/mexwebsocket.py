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


def calc_price(order_list):
    l = []
    k = 0
    for i in order_list:
        k += i[0] * i[1]
        l.append(i[1])
    return k / sum(l)

def calc_mex_order_price(recv_data):
    asks_price = calc_price(json.loads(recv_data)['data'][0]['asks'][0:3])
    bids_price = calc_price(json.loads(recv_data)['data'][0]['bids'][0:3])
    return asks_price, bids_price

if __name__ == '__main__':
    key = "f2e919df-378e-4c75-8c09-0ffa910649fe"
    skey = "2D2E421A1ECC4FE5481629ED824C388D"

    mex_key = 'J3LTq4n69Cpwzzwo_RNo7rXM'
    mex_skey = 'FirA0TKwY_I14byDi9ohKYX9FV4uz7qzBeTphrcNvN5w31Vm'
    bmext = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',
                          symbol='XBTU17', apiKey=mex_key, apiSecret=mex_skey)

    ws = websocket.WebSocket()
    mex_contract_type = 'XBTU17'
    init_asks_price, init_bids_price = None, None
    while 1:
        try:
            ws.close()
            ws.connect("wss://www.bitmex.com/realtime")
            print '{"op": "subscribe", "args": ["orderBook10:XBTU17"]}'
            ws.send('{"op": "subscribe", "args": ["orderBook10:' + mex_contract_type + '"]}')
            ws.timeout = 8
            recv_data = ""
            print "#####new init##########3"
            print ws.recv()
            while '"table":"orderBook10"' not in recv_data:
                recv_data = ws.recv()
                #init_asks_price, init_bids_price = calc_mex_order_price(recv_data)

            print json.loads(recv_data)['data'][0]['asks'][0:3]
        except Exception, e:
            print "################what the fuck"
            print e
            time.sleep(8)
            pass
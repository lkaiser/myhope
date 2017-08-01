# coding=utf-8
import datetime

import api.okcoin_com_api as okcom
import db
from api import bitmex_api
from market_maker import bitmex
from db.rediscon import Conn_db
import time
import constants as constants

if __name__ == '__main__':
    conn = Conn_db()
    holding = (0, 0, 0, 0)
    sposition = []
    hsplit_position = []
    lsplit_position = []
    #print split_position
    key = constants.coin_key
    skey = constants.coin_skey
    #print split_position

    #print conn.get("split_position")
    #sposition.sort(key=lambda x: x[1])
    #conn.set(skey, conn.get("split_position"))
    input_s = None
    while(input_s !="exit"):
        input_s = raw_input("what you want do\n")
        if input_s.find("showh") != -1:
            print conn.get(skey+'higher')
        if input_s.find("showl") != -1:
            print conn.get(skey+'lower')
        if input_s.find("inith") != -1:
            s = input_s[5:].split()
            for t in s:
                hsplit_position.append(tuple( map(eval,(t.split(",")))))

            print hsplit_position
            hsplit_position.sort(key=lambda x: x[1])
            conn.set(skey+'higher', hsplit_position)
        if input_s.find("initl") != -1:
            s = input_s[5:].split()
            for t in s:
                lsplit_position.append(tuple( map(eval,(t.split(",")))))

            print lsplit_position
            lsplit_position.sort(key=lambda x: x[1])
            lsplit_position.reverse()
            conn.set(skey+'lower', lsplit_position)
    #print input_s

    print "Bye,Bye"



    #okcoin = okcom.OkCoinComApi(key, skey)
    #print "########before##########",okcoin.get_position('quarter')['holding']
    #trade_back = okcoin.trade('quarter', 2860, 5, 2)
    #print trade_back

    #print "########after##########", okcoin.get_position('quarter')['holding']

import ConfigParser
from db.rediscon import Conn_db
import constants as constants
import time
from market_maker import bitmex
import api.okcoin_com_api as okcom

def printcfg():
    #global config
    #a = config.get("all", "lower_basic_create_key")
    print constants.trade_his_key

#print -int(round(-2.7,0))
mex_key = constants.mex_key
mex_skey = constants.mex_skey
key = constants.coin_key
skey = constants.coin_skey
#mex = bitmex.BitMEX(base_url='https://www.bitmex.com/api/v1/',symbol=constants.higher_mex_contract_type, apiKey=mex_key, apiSecret=mex_skey)
#mexpos = mex.position(constants.higher_mex_contract_type)
# print "fuck"
# okcoin = okcom.OkCoinComApi(key, skey)
# print "you"
# print okcoin.cancel_orders(constants.higher_contract_type,['12687012700'])
# print okcoin.get_order_info(constants.higher_contract_type,['12687012700'])
# okpos = okcoin.get_position(constants.higher_contract_type)['holding']

# a = []
# a.append((1,2))
# a.append((3,1))
# a.append((2,1.5))
# b = sum(i[0] for i in a)
# print -9500 - (-9400)

# print conn.get(constants.mexpush_higher_position)
# recent = conn.get("recent2")
# recent.reverse()
# print recent[0:5]


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
            print conn.get(skey+'higher_push')
        if input_s.find("showl") != -1:
            print conn.get(skey+'lower_push')
        if input_s.find("inith") != -1:
            s = input_s[5:].split()
            for t in s:
                hsplit_position.append(tuple( map(eval,(t.split(",")))))

            print hsplit_position
            hsplit_position.sort(key=lambda x: x[1])
            conn.set(skey+'higher_push', hsplit_position)
        if input_s.find("initl") != -1:
            s = input_s[5:].split()
            for t in s:
                lsplit_position.append(tuple( map(eval,(t.split(",")))))

            print lsplit_position
            lsplit_position.sort(key=lambda x: x[1])
            lsplit_position.reverse()
            conn.set(skey+'lower_push', lsplit_position)
    #print input_s

    print "Bye,Bye"
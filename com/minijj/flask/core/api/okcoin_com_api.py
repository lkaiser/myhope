# -*- coding: utf-8 -*-
import requests
import hashlib
from retrying import retry


class OkCoinComApi(object):
    def __init__(self, key, skey):
        self.api_key = key
        self.secret_key = skey
        self.headers = {"Content-type": "application/x-www-form-urlencoded"}
        self.timeout = 6
        # self.rate = self.get_rate()

    def sign(self, params):
        sign = ''
        for key in sorted(params.keys()):
            sign += key + '=' + str(params[key]) + '&'
        data = sign + 'secret_key=' + self.secret_key
        return hashlib.md5(data.encode("utf8")).hexdigest().upper()

    def get_rate(self):
        url = 'https://www.okcoin.com/api/v1/exchange_rate.do'
        req = requests.get(url, headers=self.headers, timeout=self.timeout)
        return req.json()['rate']

    def get_depth(self, contract_type):
        """
        contract_type String 合约类型: this_week:当周   next_week:下周   quarter:季度
        size  Integer  是 value: 1-200
        merge Integer 否（默认0）value: 1 （合并深度）
        """
        url = "https://www.okex.com/api/v1/future_depth.do?symbol=btc_usd" \
              "&contract_type=" + contract_type + "&size=200"
        req = requests.get(url, headers=self.headers, timeout=self.timeout)
        depth = req.json()
        return depth

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def trade(self, contract_type, usd_price, amount, type_):
        """
        contract_type :合约类型: this_week:当周   next_week:下周   quarter:季度
        type 1:开多   2:开空   3:平多   4:平空
        match_price 否为对手价 0:不是    1:是   ,当取值为1时,price无效
        """
        url = "https://www.okex.com/api/v1/future_trade.do"
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['contract_type'] = contract_type
        p['price'] = usd_price
        p['type'] = type_
        p['amount'] = amount
        p['match_price'] = 0
        p['lever_rate'] = '20'
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        return req.json()

    def tradeRival(self, contract_type, amount, type_):
        """
        contract_type :合约类型: this_week:当周   next_week:下周   quarter:季度
        type 1:开多   2:开空   3:平多   4:平空
        match_price 否为对手价 0:不是    1:是   ,当取值为1时,price无效
        """
        url = "https://www.okex.com/api/v1/future_trade.do"
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['contract_type'] = contract_type
        p['price'] = 0
        p['type'] = type_
        p['amount'] = amount
        p['match_price'] = 1
        p['lever_rate'] = '20'
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        return req.json()

    def __batch_trade(self, contract_type, orders_data):
        """
        contract_type  String 合约类型: this_week:当周   next_week:下周   quarter:季度
        orders_data String 是JSON类型的字符串 例：
        [{price:5,amount:2,type:1,match_price:1},{price:2,amount:3,type:1,
        match_price:1}]
        最大下单量为5，price,amount,type,match_price参数参考future_trade接口中的说明
        """
        url = 'https://www.okex.com/api/v1/future_batch_trade.do'
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['orders_data'] = orders_data
        p['contract_type'] = contract_type
        p['lever_rate'] = '20'
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        return req.json()

    def get_order_info(self, contract_type, orders_id):
        """
        订单ID(多个订单ID中间以","分隔,一次最多允许查询50个订单)
        """
        url = 'https://www.okex.com/api/v1/future_orders_info.do'
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['status'] = '2'
        p['contract_type'] = contract_type
        p['order_id'] = ','.join(orders_id)
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        return req.json()

    def batch_get_order_info(self, contract_type):
        url = 'https://www.okex.com/api/v1/future_order_info.do'
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['contract_type'] = contract_type
        p['status'] = '1'
        p['order_id'] = '-1'
        p['current_page'] = '1'
        p['page_length'] = '50'
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        return req.json()

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def cancel_orders(self, contract_type, orders_id):
        url = 'https://www.okex.com/api/v1/future_cancel.do'
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['contract_type'] = contract_type
        p['order_id'] = ','.join(orders_id)
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        return req.json()

    def cancel_all_orders(self, contract_type, orders_id):
        orders_num = len(orders_id)
        return_list = []
        for i in range(0, orders_num, 3):
            return_list.append(self.cancel_orders(contract_type, orders_id[i:i + 3]))
        return return_list

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def get_position(self, contract_type):
        url = 'https://www.okex.com/api/v1/future_position.do'
        p = dict()
        p['api_key'] = self.api_key
        p['symbol'] = 'btc_usd'
        p['contract_type'] = contract_type
        p['sign'] = self.sign(p)
        req = requests.post(url, headers=self.headers, params=p, timeout=self.timeout)
        #print req
        return req.json()

    @retry(stop_max_attempt_number=500000, wait_fixed=2000)
    def cancel_all(self, contract_type):
        l = []
        for i in self.batch_get_order_info(contract_type)['orders']:
            l.append(str(i['order_id']))
        self.cancel_all_orders(contract_type, l)

    @staticmethod
    def creat_orders_data_str(price, amount, type_):
        """
        type  1:开多  2:开空  3:平多  4:平空
        """
        str_ = "{" + "price:" + str(price) + ",amount:" + str(amount) + ",type:" + str(
            type_) + ",match_price:0" + "}"
        return str_

    def batch_trade(self, contract_type, trade_list, type_):
        """
        trade_list  类似:[(1053.82, 6), (1053.43, 6), (1053.43, 6), (1053.43, 6)]
季度 BTC0630
周期
分时 1分钟 3分钟 15分钟 1小时 2小时 日线 周线 技术指标画线工具
更多
        """
        l = []
        return_list = []
        i = 0
        while i < len(trade_list):
            for k in trade_list[i:i + 5]:
                l.append(self.creat_orders_data_str(k[0], k[1], type_))
            for x in self.__batch_trade(contract_type, "[" + ",".join(l) + "]", )[
                'order_info']:
                return_list.append(x['order_id'])

            l = []
            i += 5
        return return_list

    def get_order_info(self,contract_type):
        url = 'https://www.okex.com/api/v1/future_order_info.do'
        p = dict()
        p['symbol'] = 'btc_usd'
        p['contract_type'] = contract_type
        p['api_key'] = self.api_key

        p['status'] = '2'
        p['order_id'] = '-1'
        p['current_page'] = '0'
        p['page_length'] = '10'
        p['sign'] = self.sign(p)
        #print p
        req = requests.post(url, headers=self.headers, params=p,timeout=self.timeout)
        return req.json()

    def get_userinfo(self):
        url = 'https://www.okex.com/api/v1/future_userinfo.do'
        p = dict()
        p['api_key'] = self.api_key
        p['sign'] = self.sign(p)
        #print p
        req = requests.post(url, headers=self.headers, params=p,timeout=self.timeout)
        return req.json()



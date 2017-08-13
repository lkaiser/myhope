# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import requests
import time
import urlparse

from future.builtins import bytes
from retrying import retry


class Bitmex(object):
    def __init__(self,apiSecret,apiKey):
        self.apiSecret = apiSecret
        self.apiKey = apiKey

    @staticmethod
    def generate_signature(secret, verb, url, nonce, data):
        parsed_u_r_l = urlparse.urlparse(url)
        path = parsed_u_r_l.path
        if parsed_u_r_l.query:
            path = path + '?' + parsed_u_r_l.query
        message = verb + path + str(nonce) + data

        signature = hmac.new(bytes(secret, 'utf8'), bytes(message, 'utf8'),
                             digestmod=hashlib.sha256).hexdigest()

        return signature

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def buy(self, symbol, price, amount):
        expires = int(round(time.time()) + 10)
        postdict = {"orderQty": amount, "symbol": symbol, "price": price}
        data = json.dumps(postdict)
        headers = {'api-expires': str(expires), 'api-key': self.apiKey,
                   'api-signature': self.generate_signature(self.apiSecret, 'POST',
                                                            '/api/v1/order', expires,
                                                            data),
                   'content-type': 'application/json'}
        req = requests.post("https://www.bitmex.com/api/v1/order", headers=headers,
                            json=postdict)
        return req.json()

    def sell(self, symbol, price, amount):
        return self.buy(symbol, price, -amount)

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def buy_bulk(self, symbol, price, amount):
        expires = int(round(time.time()) + 10)
        postdict = {
            'orders': [{"orderQty": amount, "symbol": symbol, "price": price},
                       {"orderQty": amount, "symbol": symbol, "price": price}]}
        data = json.dumps(postdict)
        headers = {'api-expires': str(expires),
                   'api-key': self.apiKey,
                   'api-signature': self.generate_signature(self.apiSecret, 'POST',
                                                            '/api/v1/order/bulk',
                                                            expires,
                                                            data),
                   'content-type': 'application/json'}
        req = requests.post("https://www.bitmex.com/api/v1/order/bulk", headers=headers,
                            json=postdict)

        return req.json()

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def get_position(self, symbol):
        expires = int(round(time.time()) + 10)
        headers = {'api-expires': str(expires), 'api-key': self.apiKey,
                   'api-signature': self.generate_signature(self.apiSecret, 'GET',
                                                            '/api/v1/position', expires,
                                                            ""),
                   'content-type': 'application/json'}
        req = requests.get("https://www.bitmex.com/api/v1/position", headers=headers,
                           )
        return_l = req.json()
        for i in return_l:
            if i['symbol'] == symbol:
                count = return_l.index(i)
                #print return_l
                return return_l[count]['avgCostPrice'], return_l[count]['currentQty']


    def get_positionAll(self,):
        expires = int(round(time.time()) + 10)
        headers = {'api-expires': str(expires), 'api-key': self.apiKey,
                   'api-signature': self.generate_signature(self.apiSecret, 'GET',
                                                            '/api/v1/position', expires,
                                                            ""),
                   'content-type': 'application/json'}
        req = requests.get("https://www.bitmex.com/api/v1/position", headers=headers,
                           )
        return_l = req.json()
        return return_l
        # for i in return_l:
        #     if i['symbol'] == symbol:
        #         count = return_l.index(i)
        #         return return_l[count]

    def get_userCommission(self):
        expires = int(round(time.time()) + 10)
        headers = {'api-expires': str(expires), 'api-key': self.apiKey,
                   'api-signature': self.generate_signature(self.apiSecret, 'GET',
                                                            '/api/v1/position', expires,
                                                            ""),
                   'content-type': 'application/json'}
        req = requests.get("https://www.bitmex.com/api/v1/position", headers=headers,
                           )
        return_l = req.json()
        return return_l
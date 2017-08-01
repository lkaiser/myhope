# -*- coding: utf-8 -*-
import ConfigParser
import sys
import os

#print os.path
inipath = os.path.split(os.path.realpath(__file__))[0]

config = ConfigParser.ConfigParser()
config.readfp(open(inipath+'/constants.ini'))

coin_key = config.get("all", "coin_key")
coin_skey = config.get("all", "coin_skey")

mex_key = config.get("all", "mex_key")
mex_skey = config.get("all", "mex_skey")

trade_his_key = config.get("all", "trade_his_key")
lower_basic_create_key = config.get("all", "lower_basic_create_key")

lower_sell_run_key = config.get("all", "lower_sell_run_key")
lower_buy_run_key = config.get("all", "lower_buy_run_key")
lower_main_run_key = config.get("all", "lower_main_run_key")

higher_sell_run_key = config.get("all", "higher_sell_run_key")
higher_buy_run_key = config.get("all", "higher_buy_run_key")
higher_main_run_key = config.get("all", "higher_main_run_key")

lower_max_size = config.getint("all", "lower_max_size")
lower_deal_amount = config.getint("all", "lower_deal_amount")
lower_expected_profit = config.getint("all", "lower_expected_profit")
lower_basis_create = config.getint("all", "lower_basis_create")
lower_step_price = config.getint("all", "lower_step_price")
lower_contract_type = config.get("all", "lower_contract_type")
lower_mex_contract_type = config.get("all", "lower_mex_contract_type")

higher_max_size = config.getint("all", "higher_max_size")
higher_deal_amount = config.getint("all", "higher_deal_amount")
higher_expected_profit = config.getint("all", "higher_expected_profit")
higher_basis_create = config.getint("all", "higher_basis_create")
higher_step_price = config.getint("all", "higher_step_price")
higher_contract_type = config.get("all", "higher_contract_type")
higher_mex_contract_type = config.get("all", "higher_mex_contract_type")




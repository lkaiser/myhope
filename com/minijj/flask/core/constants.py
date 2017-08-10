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

passwrod = config.get("all", "password")

trade_his_key = config.get("all", "trade_his_key")

higher_server = "higher_server"
lower_server = "lower_server"


higher_split_position = coin_skey + "higher"
lower_split_position = coin_skey + "lower"

lower_basic_create_key = config.get("all", "lower_basic_create_key")
higher_basic_create_key = config.get("all", "higher_basic_create_key")

lower_sell_run_key = config.get("all", "lower_sell_run_key")
lower_buy_run_key = config.get("all", "lower_buy_run_key")
lower_main_run_key = config.get("all", "lower_main_run_key")

higher_sell_run_key = config.get("all", "higher_sell_run_key")
higher_buy_run_key = config.get("all", "higher_buy_run_key")
higher_main_run_key = config.get("all", "higher_main_run_key")

lower_max_size = config.getint("all", "lower_max_size")
lower_deal_amount = config.getint("all", "lower_deal_amount")
lower_expected_profit = config.getfloat("all", "lower_expected_profit")
lower_basis_create = config.getfloat("all", "lower_basis_create")
lower_back_distant = config.getfloat("all", "lower_back_distant")
lower_step_price = config.getfloat("all", "lower_step_price")
lower_contract_type = config.get("all", "lower_contract_type")
lower_mex_contract_type = config.get("all", "lower_mex_contract_type")

higher_max_size = config.getint("all", "higher_max_size")
higher_deal_amount = config.getint("all", "higher_deal_amount")
higher_expected_profit = config.getfloat("all", "higher_expected_profit")
higher_back_distant = config.getfloat("all", "higher_back_distant")
higher_basis_create = config.getfloat("all", "higher_basis_create")
higher_step_price = config.getfloat("all", "higher_step_price")
higher_contract_type = config.get("all", "higher_contract_type")
higher_mex_contract_type = config.get("all", "higher_mex_contract_type")

def getCfg():
    config = ConfigParser.ConfigParser()
    config.readfp(open(inipath + '/constants.ini'))
    return config

def update(cfg):
    config.set('all', "lower_max_size",cfg.lower_max_size.data)
    config.set('all', "lower_deal_amount", cfg.lower_deal_amount.data)
    config.set('all', "lower_expected_profit", cfg.lower_expected_profit.data)
    config.set('all', "lower_back_distant", cfg.lower_back_distant.data)
    config.set('all', "lower_basis_create", cfg.lower_basis_create.data)
    config.set('all', "lower_step_price", cfg.lower_step_price.data)
    config.set('all', "lower_contract_type", cfg.lower_contract_type.data)
    config.set('all', "lower_mex_contract_type", cfg.lower_mex_contract_type.data)

    config.set('all', "higher_max_size", cfg.higher_max_size.data)
    config.set('all', "higher_deal_amount", cfg.higher_deal_amount.data)
    config.set('all', "higher_expected_profit", cfg.higher_expected_profit.data)
    config.set('all', "higher_back_distant", cfg.higher_back_distant.data)
    config.set('all', "higher_basis_create", cfg.higher_basis_create.data)
    config.set('all', "higher_step_price", cfg.higher_step_price.data)
    config.set('all', "higher_contract_type", cfg.higher_contract_type.data)
    config.set('all', "higher_mex_contract_type", cfg.higher_mex_contract_type.data)
    config.write(open(inipath + '/constants.ini', 'w'))






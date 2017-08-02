import sys
import os
parentpath = os.path.dirname(sys.path[0])

#print "#########parentpath=",parentpath
sys.path.append(parentpath)

import bit.constants as constants
from flask_wtf import Form
from wtforms import StringField, FloatField,SubmitField,IntegerField
from wtforms.validators import Required

class settingForm(Form):
    lower_max_size = IntegerField("lower_max_size", validators=[Required()])
    lower_deal_amount = IntegerField("lower_deal_amount", validators=[Required()])
    lower_expected_profit = FloatField("lower_expected_profit", validators=[Required()])
    lower_basis_create = FloatField("lower_basis_create", validators=[Required()])
    lower_step_price = FloatField("lower_step_price", validators=[Required()])
    lower_contract_type = StringField("lower_contract_type", validators=[Required()])
    lower_mex_contract_type = StringField("lower_mex_contract_type", validators=[Required()])

    higher_max_size = IntegerField("higher_max_size", validators=[Required()])
    higher_deal_amount = IntegerField("higher_deal_amount", validators=[Required()])
    higher_expected_profit = FloatField("higher_expected_profit", validators=[Required()])
    higher_basis_create = FloatField("higher_basis_create", validators=[Required()])
    higher_step_price = FloatField("higher_step_price", validators=[Required()])
    higher_contract_type = StringField("higher_contract_type", validators=[Required()])
    higher_mex_contract_type = StringField("higher_mex_contract_type", validators=[Required()])
    submit = SubmitField('Submit')

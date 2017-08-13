# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms import StringField, FloatField,SubmitField,IntegerField,TextAreaField
from wtforms.validators import Required

class fastHigherForm(Form):
    higher_max_size = IntegerField("higher_max_size", validators=[Required()])
    higher_deal_amount = IntegerField("higher_deal_amount", validators=[Required()])
    higher_expected_profit = FloatField("higher_expected_profit", validators=[Required()])
    higher_back_distant = FloatField("higher_back_distant", validators=[Required()])
    higher_basis_create = FloatField("higher_basis_create", validators=[Required()])
    higher_step_price = FloatField("higher_step_price", validators=[Required()])
    submit = SubmitField('submit')

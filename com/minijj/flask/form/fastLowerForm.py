# -*- coding: utf-8 -*-


from flask_wtf import Form
from wtforms import StringField, FloatField,SubmitField,IntegerField,TextAreaField
from wtforms.validators import Required

class fastLowerForm(Form):
    lower_max_size = IntegerField("lower_max_size", validators=[Required()])
    lower_deal_amount = IntegerField("lower_deal_amount", validators=[Required()])
    lower_expected_profit = FloatField("lower_expected_profit", validators=[Required()])
    lower_back_distant = FloatField("lower_back_distant", validators=[Required()])
    lower_basis_create = FloatField("lower_basis_create", validators=[Required()])
    lower_step_price = FloatField("lower_step_price", validators=[Required()])
    submit = SubmitField('submit')

from flask_wtf import FlaskForm
from wtforms import FloatField, HiddenField, SubmitField
from wtforms.validators import DataRequired


class LocationForm(FlaskForm):
    order_id = HiddenField('订单ID')
    latitude = FloatField('纬度', validators=[DataRequired()])
    longitude = FloatField('经度', validators=[DataRequired()])
    submit = SubmitField('更新位置')

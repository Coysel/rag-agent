from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length


class AddressForm(FlaskForm):
    label = StringField('标签', validators=[DataRequired('请输入地址标签')])
    address_detail = StringField('详细地址', validators=[DataRequired('请输入详细地址')])
    submit = SubmitField('保存')


class CheckoutForm(FlaskForm):
    address_id = SelectField('收货地址', coerce=int, validators=[DataRequired('请选择收货地址')])
    note = TextAreaField('订单备注')
    submit = SubmitField('提交订单')


class ReviewForm(FlaskForm):
    order_id = HiddenField('订单ID', validators=[DataRequired()])
    target_type = SelectField('评价对象', choices=[
        ('merchant', '商家'),
        ('rider', '骑手'),
        ('menu_item', '菜品'),
    ], validators=[DataRequired()])
    target_id = HiddenField('目标ID', validators=[DataRequired()])
    rating = IntegerField('评分（1-5分）', validators=[
        DataRequired(), NumberRange(min=1, max=5, message='评分必须在1-5之间')
    ])
    comment = TextAreaField('评价内容', validators=[Length(max=500)])
    submit = SubmitField('提交评价')


class RefundForm(FlaskForm):
    order_id = HiddenField('订单ID', validators=[DataRequired()])
    reason = TextAreaField('退款原因', validators=[DataRequired('请填写退款原因'), Length(min=5, max=500)])
    submit = SubmitField('提交退款申请')

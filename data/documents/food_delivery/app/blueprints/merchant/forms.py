from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length


class ShopForm(FlaskForm):
    name = StringField('店铺名称', validators=[DataRequired('请输入店铺名称')])
    description = TextAreaField('店铺描述')
    address = StringField('店铺地址', validators=[DataRequired('请输入店铺地址')])
    phone = StringField('联系电话', validators=[DataRequired('请输入联系电话')])
    submit = SubmitField('保存')


class MenuItemForm(FlaskForm):
    name = StringField('菜品名称', validators=[DataRequired('请输入菜品名称')])
    description = TextAreaField('菜品描述')
    price = FloatField('单价 (元)', validators=[DataRequired('请输入价格'), NumberRange(min=0.01, message='价格必须大于0')])
    stock = IntegerField('库存数量', validators=[DataRequired('请输入库存'), NumberRange(min=0)])
    category = SelectField('分类', choices=[
        ('热菜', '热菜'), ('凉菜', '凉菜'), ('汤品', '汤品'),
        ('主食', '主食'), ('饮品', '饮品'),
    ])
    is_available = SelectField('状态', choices=[('1', '上架'), ('0', '下架')])
    submit = SubmitField('保存')


class ReviewReplyForm(FlaskForm):
    review_id = HiddenField(validators=[DataRequired()])
    content = TextAreaField('回复内容', validators=[DataRequired('请输入回复内容'), Length(max=500)])
    submit = SubmitField('提交回复')

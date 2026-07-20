from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField('用户名 / 邮箱', validators=[DataRequired('请输入用户名或邮箱')])
    password = PasswordField('密码', validators=[DataRequired('请输入密码')])
    submit = SubmitField('登录')


class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired('请输入用户名'),
        Length(min=3, max=80, message='用户名长度3-80个字符'),
    ])
    email = StringField('邮箱', validators=[
        DataRequired('请输入邮箱'),
        Email('请输入有效的邮箱地址'),
    ])
    name = StringField('姓名', validators=[DataRequired('请输入姓名')])
    phone = StringField('手机号', validators=[DataRequired('请输入手机号')])
    password = PasswordField('密码', validators=[
        DataRequired('请输入密码'),
        Length(min=6, message='密码长度不能少于6位'),
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired('请确认密码'),
        EqualTo('password', message='两次输入的密码不一致'),
    ])
    role = SelectField('注册角色', choices=[
        ('user', '普通用户'),
        ('merchant', '商家'),
        ('rider', '骑手'),
    ], validators=[DataRequired('请选择角色')])
    submit = SubmitField('注册')


class ProfileForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired('请输入姓名')])
    phone = StringField('手机号', validators=[DataRequired('请输入手机号')])
    email = StringField('邮箱', validators=[
        DataRequired('请输入邮箱'),
        Email('请输入有效的邮箱地址'),
    ])
    old_password = PasswordField('原密码')
    new_password = PasswordField('新密码', validators=[
        Length(min=0, max=128),
    ])
    confirm_password = PasswordField('确认新密码', validators=[
        EqualTo('new_password', message='两次输入的密码不一致'),
    ])
    submit = SubmitField('保存修改')

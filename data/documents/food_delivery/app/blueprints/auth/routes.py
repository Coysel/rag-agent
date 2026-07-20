from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import LoginForm, RegisterForm, ProfileForm
from app.services.auth_service import register_user, authenticate, update_profile, change_password


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user, error = authenticate(form.username.data, form.password.data)
        if user:
            login_user(user, remember=True)
            flash(f'欢迎回来，{user.name or user.username}！', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        flash(error, 'danger')
    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user, error = register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            name=form.name.data,
            phone=form.phone.data,
            role=form.role.data,
        )
        if user:
            if user.role == 'merchant':
                flash('注册成功！商家账号需等待管理员审核。', 'info')
            else:
                login_user(user, remember=True)
                flash(f'注册成功！欢迎，{user.name or user.username}！', 'success')
                return redirect(url_for('main.index'))
            return redirect(url_for('auth.login'))
        flash(error, 'danger')
    return render_template('register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已退出登录。', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        user, error = update_profile(
            user=current_user,
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
        )
        if user:
            if form.new_password.data:
                success, pw_error = change_password(
                    current_user, form.old_password.data, form.new_password.data
                )
                if not success:
                    flash(pw_error, 'danger')
                    return render_template('profile.html', form=form)
            flash('个人信息更新成功！', 'success')
            return redirect(url_for('auth.profile'))
        flash(error, 'danger')
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.phone.data = current_user.phone
        form.email.data = current_user.email
    return render_template('profile.html', form=form)

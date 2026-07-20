from app.extensions import db
from app.models.user import User
from app.models.shop import Shop


def register_user(username, email, password, name, phone, role='user'):
    """Register a new user. Returns (user, error_message)."""
    if User.query.filter_by(username=username).first():
        return None, '用户名已存在。'
    if User.query.filter_by(email=email).first():
        return None, '邮箱已被注册。'
    if len(password) < 6:
        return None, '密码长度不能少于6位。'

    user = User(
        username=username,
        email=email,
        name=name,
        phone=phone,
        role=role,
        is_approved=(role != 'merchant'),  # Auto-approve non-merchants
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def authenticate(username_or_email, password):
    """Authenticate a user. Returns (user, error_message)."""
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if user is None:
        return None, '用户名或邮箱不存在。'
    if not user.check_password(password):
        return None, '密码错误。'
    if not user.is_active:
        return None, '账号已被禁用，请联系管理员。'
    if user.role == 'merchant' and not user.is_approved:
        return None, '商家账号尚未通过审核，请等待管理员审批。'
    return user, None


def update_profile(user, name, phone, email):
    """Update user profile. Returns (user, error_message)."""
    if email != user.email and User.query.filter_by(email=email).first():
        return None, '邮箱已被其他用户使用。'
    user.name = name
    user.phone = phone
    user.email = email
    db.session.commit()
    return user, None


def change_password(user, old_password, new_password):
    """Change user password. Returns (success, error_message)."""
    if not user.check_password(old_password):
        return False, '原密码错误。'
    if len(new_password) < 6:
        return False, '新密码长度不能少于6位。'
    user.set_password(new_password)
    db.session.commit()
    return True, None

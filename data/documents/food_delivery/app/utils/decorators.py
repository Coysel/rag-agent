from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """Decorator to restrict access to specific user roles.

    Must be used together with @login_required.
    Usage: @role_required('admin') or @role_required('user', 'merchant')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('您没有权限访问该页面。', 'danger')
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

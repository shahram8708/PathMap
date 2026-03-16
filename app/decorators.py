from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def premium_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_premium:
            flash('Upgrade to Premium to access this feature.', 'warning')
            return redirect(url_for('main.pricing'))
        return view_func(*args, **kwargs)
    return wrapper

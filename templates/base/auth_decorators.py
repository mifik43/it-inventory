from functools import wraps
from flask import flash, redirect, url_for, session
from models import User

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(int(user_id))
    return None
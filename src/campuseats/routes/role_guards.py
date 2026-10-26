#This code will be used to check if the user is a student or vendor and will be used to restrict access to certain routes based on the user's role.

from functools import wraps
from flask import abort
from flask_login import current_user


def vendor_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(403)

        if current_user.role != "vendor":
            abort(403)

        return view(*args, **kwargs)

    return wrapper
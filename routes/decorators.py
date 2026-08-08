# from functools import wraps
# from flask import session, redirect
from functools import wraps
from flask import session, redirect, flash, request, url_for

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# def role_required(role):
#     def wrapper(f):
#         @wraps(f)
#         def decorated(*args, **kwargs):
#             if session.get('role') != role:
#                 return 'Forbidden', 403
#             return f(*args, **kwargs)
#         return decorated
#     return wrapper

def role_required(role, redirect_endpoint=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session["user"].get('role') != role:
                flash('Anda tidak memiliki hak akses', 'danger')

                # jika redirect tujuan ditentukan
                if redirect_endpoint:
                    return redirect(url_for(redirect_endpoint))

                # fallback: kembali ke halaman sebelumnya
                return redirect(request.referrer or url_for('/'))

            return f(*args, **kwargs)
        return decorated
    return wrapper

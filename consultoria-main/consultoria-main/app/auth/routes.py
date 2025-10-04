import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, UserMixin

bp = Blueprint('auth', __name__)

# Usuario simple en memoria usando Flask-Login compatible
class SimpleUser(UserMixin):
    def __init__(self, id):
        self.id = id
        
from ..extensions import login_manager

@login_manager.user_loader
def load_user(user_id):
    # Como no tenemos tabla de usuarios, devolvemos el usuario en memoria
    if user_id:
        return SimpleUser(id=user_id)
    return None

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == os.getenv('ADMIN_USER') and password == os.getenv('ADMIN_PASSWORD'):
            login_user(SimpleUser(id=username))
            return redirect(url_for('dashboard.index'))
        flash('Credenciales inválidas', 'danger')
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

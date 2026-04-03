import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models.user import User
from flask_login import login_user, login_required, logout_user

auth_bp = Blueprint('auth', __name__)


def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('at least 8 characters')
    if not any(c.isdigit() for c in password):
        errors.append('at least one number')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('at least one special character')
    return errors


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return redirect(url_for('auth.signup'))

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.signup'))

        errors = validate_password(password)
        if errors:
            flash(f'Password needs: {", ".join(errors)}.', 'error')
            return redirect(url_for('auth.signup'))

        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback()
            flash('Something went wrong. Please try again.', 'error')
            return redirect(url_for('auth.signup'))

    return render_template('login_page/signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('login_page/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

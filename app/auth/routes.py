from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models.user import User
from flask_login import login_user, login_required, logout_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists.')
            return redirect(url_for('auth.signup'))

        if password != confirm:
            flash('Passwords do not match.')
            return redirect(url_for('auth.signup'))

        if len(password) < 8 or " " in password or not any(c.isdigit() for c in password) or not any(not c.isalnum() for c in password):
            flash('Password does not meet requirements.')
            return redirect(url_for('auth.signup'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Signup successful. Please log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('login_page/signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.home'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))

    return render_template('login_page/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

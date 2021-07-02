from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Organization
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user, title="Login")


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    organizations = Organization.query.all()
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        authorization = request.form.get('authorization')
        org_id = int(request.form.get('org'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        elif authorization != '123':
            flash('Invalid authorization code. Please contact the developer for access.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, last_name=last_name, password=generate_password_hash(
                password1, method='sha256'), organization_id=org_id)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created! Now add locations for your organization.', category='success')
            return redirect(url_for('views.locations'))

    return render_template("sign_up.html", user=current_user, title="Sign Up", organizations=organizations)


@auth.route('/organizations', methods=['GET','POST'])
def organizations():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        authorization = request.form.get('authorization')
        if authorization != '852':
            flash('Invalid authorization code. Please contact the developer for access.', category='error')
        else: 
            # creates new organization
            org = Organization(name=name, address=address)
            # adds org to db
            db.session.add(org)
            db.session.commit()
            flash('Organization added. Now create an account under your organization.', category='success')
            return redirect(url_for('auth.sign_up'))
    return render_template("organizations.html", user=current_user, title="Add Organization")
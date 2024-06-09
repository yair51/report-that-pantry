from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
@auth.route('/login/', methods=['GET', 'POST'])
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
@auth.route('/sign-up/', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        age = request.form.get('age')
        user_type = request.form.get('description')

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        # Server-side form validation
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
        # Create new user
        else:
            new_user = User(email=email, first_name=first_name, last_name=last_name, password=generate_password_hash(
                password1, method='sha256'), age=age, user_type=user_type)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            if user_type == "owner":
                flash('Account created! Now add your pantry locations, if you have any.', category='success')
                return redirect(url_for('views.add_location'))
            else:
                flash("Account created! Now set your notification preferences.")
                return redirect(url_for('views.notifications'))

    return render_template("sign_up.html", user=current_user, title="Sign Up")


# @auth.route('/organizations', methods=['GET','POST'])
# def organizations():
#     if request.method == 'POST':
#         name = request.form.get('name')
#         address = request.form.get('address')
#         authorization = request.form.get('authorization')
#         if authorization != '852':
#             flash('Invalid authorization code. Please contact the developer for access.', category='error')
#         else: 
#             # creates new organization
#             org = Organization(name=name, address=address)
#             # adds org to db
#             db.session.add(org)
#             db.session.commit()
#             flash('Organization added. Now create an account under your organization.', category='success')
#             return redirect(url_for('auth.sign_up'))
#     return render_template("organizations.html", user=current_user, title="Add Organization")
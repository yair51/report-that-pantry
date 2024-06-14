from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message


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


@auth.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    # Intialize serializer
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a token (time-sensitive)
            token = serializer.dumps(user.id, salt='password-reset-salt')

            # Create the reset password link
            reset_link = url_for('auth.reset_password', token=token, _external=True)

            # Pass the token to the send_email function
            send_email(user.email, "Reset Your Password", token)

            flash('An email with instructions to reset your password has been sent.', 'info')
            return redirect(url_for('auth.login'))

        flash('That email does not exist.', category='error')
    return render_template('forgot_password.html', user=current_user, title='Forgot Password')
    

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiry
    except:
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        new_password = request.form['newPassword']
        confirm_password = request.form['confirmPassword']
        
        if new_password == confirm_password:
            user = User.query.get(user_id)
            user.password = generate_password_hash(new_password, method='sha256')  # Hash the new password
            db.session.commit()
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash("Passwords do not match", category="error")

    return render_template('reset_password.html', token=token, user=current_user, title='Reset Password')


# Function to send emails
def send_email(to, subject, token):
    msg = Message(subject, sender='info.reportthatpantry@gmail.com', recipients=[to])
    
    # Create a clickable reset link with HTML
    reset_link = url_for('auth.reset_password', token=token, _external=True)  # Generate the full URL
    msg.html = f'<p>To reset your password, please click on the following link:</p><a href="{reset_link}">{reset_link}</a>'

    mail.send(msg)

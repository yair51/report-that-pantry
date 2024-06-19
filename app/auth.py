from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from app.models import User, Notification, Location, Report
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message

# from flask_dance.contrib.google import make_google_blueprint, google
# from flask_dance.contrib.facebook import make_facebook_blueprint, facebook


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
@auth.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('Password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.status'))
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
        password = request.form.get('Password')
        # password2 = request.form.get('password2')
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
        # elif password1 != password2:
        #     flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters.', category='error')
        # Create new user
        else:
            print(age)
            print(len(age))
            new_user = User(email=email, first_name=first_name, last_name=last_name, password=generate_password_hash(
                password, method='sha256'), user_type=user_type)
            
            # Set age if it is inputted
            if len(age) != 0:
                new_user.age = age

            db.session.add(new_user)
            db.session.commit()
            # Log in user
            login_user(new_user, remember=True)
            if user_type == "owner":
                flash('Account created! Now add your pantry locations, if you have any.', category='success')
                return redirect(url_for('views.add_location'))
            else:
                flash("Account created! Subscribe to a location to recieve pantry status updates.")
                return redirect(url_for('views.status'))

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
        new_password = request.form['Password']
        confirm_password = request.form['confirmPassword']
        
        # Check password length
        if len(new_password) > 6:
            user = User.query.get(user_id)
            user.password = generate_password_hash(new_password, method='sha256')  # Hash the new password
            db.session.commit()
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash("Password must be at least 7 characters.", category="error")

    return render_template('reset_password.html', token=token, user=current_user, title='Reset Password')


@auth.route('/profile')
@auth.route('/profile/')
@login_required
def profile():
    locations = db.session.query(Location).options(joinedload(Location.notifications)).all()

    # # Query all the locations a user is subscribed to
    # locations = db.session.query(Location, Notification).outerjoin(
    #     Notification, and_(
    #         Location.id == Notification.location_id,
    #         Notification.user_id == current_user.id
    #     )
    # ).all()

 

    # Create a list of all locations the current user is subscribed to. 
    subscribed_locations = [notification.location_id for notification in current_user.notifications]

    # print(subscribed_locations)

    return render_template(
        "profile.html",
        title="Manage Profile",
        user=current_user,
        locations=locations,
        subscribed_locations=subscribed_locations
    )


# Create update_profile view function
@auth.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        user_type = request.form.get('userType')
        
        # Check for email validity (if you want)
        # Update user's profile data
        current_user.email = email
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.user_type = user_type
        db.session.commit()
        flash('Your profile has been updated!', 'success')

    return redirect(url_for('auth.profile'))


@auth.route('/update_notifications', methods=['POST'])
@login_required
def update_notifications():
    # Retrieve notification preferences from form
    low_inventory = request.form.get('low_inventory') == 'on'  # Check if checkbox is checked
    new_location = request.form.get('new_location') == 'on'
    # ... (get other preferences)

    # Update or create a Notification object for the current user
    notification = Notification.query.filter_by(user_id=current_user.id).first()
    if notification:
        notification.low_inventory = low_inventory
        notification.new_location = new_location
        # ... update other preferences
    else:
        notification = Notification(
            user_id=current_user.id,
            low_inventory=low_inventory,
            new_location=new_location,
        )
        db.session.add(notification)

    db.session.commit()
    flash('Your notification preferences have been updated!', 'success')
    return redirect(url_for('auth.profile'))


@auth.route('/update_subscriptions', methods=['POST'])
@login_required
def update_subscriptions():
    # Retrieve selected location IDs from the form
    selected_location_ids = request.form.getlist('subscriptions')
    # Convert the values in the list to integers
    selected_location_ids = [int(id) for id in selected_location_ids]

    # Get all existing subscriptions for this user
    existing_subscriptions = Notification.query.filter_by(user_id=current_user.id).all()

    # Create a set of existing subscription IDs for faster lookups
    existing_location_ids = {sub.location_id for sub in existing_subscriptions}

    # Update subscriptions
    for location_id in selected_location_ids:
        if location_id not in existing_location_ids:
            # Create new subscription
            new_subscription = Notification(user_id=current_user.id, location_id=location_id)
            db.session.add(new_subscription)

    # Delete removed subscriptions
    for subscription in existing_subscriptions:
        if subscription.location_id not in selected_location_ids:
            db.session.delete(subscription)

    db.session.commit()
    flash('Your subscriptions have been updated!', 'success')

    return redirect(url_for('auth.profile'))



# Function to send emails
def send_email(to, subject, token):
    msg = Message(subject, sender='info.reportthatpantry@gmail.com', recipients=[to])
    
    # Create a clickable reset link with HTML
    reset_link = url_for('auth.reset_password', token=token, _external=True)  # Generate the full URL
    msg.html = f'<p>To reset your password, please click on the following link:</p><a href="{reset_link}">{reset_link}</a>'

    mail.send(msg)



# from flask import Blueprint, redirect, url_for, flash

# from app.models import User
# from app import db


# auth = Blueprint('auth', __name__)

# Google Blueprint
# google_blueprint = make_google_blueprint(
#     client_id=current_app.config['GOOGLE_OAUTH_CLIENT_ID'],
#     client_secret=current_app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
#     scope=["profile", "email"],
#     offline=True,
# )

# # app.register_blueprint(google_blueprint, url_prefix="/login")

# # Facebook Blueprint
# facebook_blueprint = make_facebook_blueprint(
#     client_id=current_app.config['FACEBOOK_OAUTH_CLIENT_ID'],
#     client_secret=current_app.config['FACEBOOK_OAUTH_CLIENT_SECRET'],
#     scope=["email"]
# )

# # app.register_blueprint(facebook_blueprint, url_prefix="/login")


# @auth.route('/google_login')
# def google_login():
#     if not google.authorized:
#         return redirect(url_for("google.login"))
#     account_info = google.get('/oauth2/v2/userinfo')
#     if account_info.ok:
#         account_info_json = account_info.json()
#         email = account_info_json['email']

#         # Check if user exists; if not, create them
#         user = User.query.filter_by(email=email).first()
#         if user is None:
#             user = User(email=email, first_name=account_info_json.get('given_name'), last_name=account_info_json.get('family_name'))
#             db.session.add(user)
#             db.session.commit()

#         login_user(user)
#         return redirect(url_for('views.home'))  
    
#     flash("Google login failed.", category="error")  
#     return redirect(url_for('auth.login'))

# @auth.route('/facebook_login')
# def facebook_login():
#     if not facebook.authorized:
#         return redirect(url_for("facebook.login"))
#     account_info = facebook.get('/me?fields=name,email')
#     if account_info.ok:
#         account_info_json = account_info.json()
#         email = account_info_json['email']
        
#         # Check if user exists; if not, create them
#         user = User.query.filter_by(email=email).first()
#         if user is None:
#             user = User(email=email, first_name=account_info_json.get('name'))
#             db.session.add(user)
#             db.session.commit()

#         login_user(user)
#         return redirect(url_for('views.home'))
    
#     flash("Facebook login failed.", category="error")  
#     return redirect(url_for('auth.login'))


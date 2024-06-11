from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import true
from .models import Location, Report, Notification, User
from . import db, Message, mail
import json
from datetime import datetime
from time import mktime
from sqlalchemy import func, and_
from werkzeug.utils import secure_filename
import os

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@views.route('/index')
def home(id=0):
    # # queries all of the locations
    locations = Location.query.all()

    return render_template("index.html", user=current_user, title="Home")


# # view details of location
# @views.route('/location', methods=['GET'])
# @views.route('/location/', methods=['GET'])
# def location():
#     return render_template("locations.html", user=current_user, editing=False, location=location, title="Location")


@views.route('/location/add', methods=['GET', 'POST'])
@views.route('/location/add/', methods=['GET', 'POST'])
# @views.route('/add/<int:id>', methods=['GET', 'POST'])
def add_location():
    # handles form submissions
    if request.method == 'POST':
        # Get form details
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip = request.form.get('zipCode')
        # checks if the location exists
        location = Location.query.filter_by(address=address).first()
        if location:
            flash('Address already exists.', category='error')
            return redirect(url_for('views.locations'))
        # Add location to database
        else:
            new_location = Location(address=address, name=name, city=city, state=state, zip=zip)
            db.session.add(new_location)
            db.session.commit()
            id = new_location.id
            # Create intial status update for location
            new_status = Report(status='Full', time=datetime.utcnow(), location_id=new_location.id)
            db.session.add(new_status)
            db.session.commit()

        # Redirect user to poster page
        return redirect(url_for("views.poster", id=id, isNew1=1))

    return render_template("locations.html", user=current_user, editing=False, title="Locations")


# Handles Location edits
@views.route('/location/edit/<int:location_id>', methods=['GET','POST'])
@views.route('/location/edit/<int:location_id>/', methods=['GET','POST'])
def edit(location_id):
    # Check if location exists
    location = Location.query.get(location_id)
    if not location:
        flash("Location does not exist", category='error')
        return redirect(url_for('views.status'))
    # Check if user owns this location
    if current_user.id != location.user_id:
        print(current_user.id)
        print(location.user_id)
        flash("You cannot edit this location.", category='error')
        return redirect(url_for('views.status'))
    if request.method == 'POST':
        # Edit details of given location
        location.name = request.form.get('name')
        location.address = request.form.get('address')
        location.city = request.form.get('city')
        location.state = request.form.get('state')
        location.zip = request.form.get('zipCode')
        db.session.commit()
        flash('Location updated.', category='success')
        # Redirect to status page
        return redirect(url_for('views.status'))
    return render_template("locations.html", user=current_user, location=location, editing=True)


@views.route('/delete-location', methods=['POST'])
def delete_location():
    print("delete-location")
    location = json.loads(request.data)
    locationId = location['locationId']
    location = Location.query.get(locationId)
    if location:
        #if note.user_id == current_user.id:
        db.session.delete(location)
        db.session.commit()
        flash("Location Deleted.", category="success")

    return jsonify({})


# # Report on status of given location
# @views.route('report/<int:id>/')
# @views.route('/report/<int:id>')
# @views.route('/report<int:id>')
# def report(id):
#     # Get current location
#     location = Location.query.get(id)
#     status = request.args.get('status')
#     pantry_fullness = request.form.get('pantryFullness')
#     print(pantry_fullness)
#     # a status is given, create add a new location_status to db for the current location
#     if status:
#         time = datetime.utcnow()
#         # Create location status object
#         new_status = Report(status=status, time=time, location_id=location.id)
#         # Commit status to database
#         db.session.add(new_status)
#         db.session.commit()
#         flash("Thank you for your feedback!", category='success')
#         # send email if empty
#         if status == "Empty":
#             users = db.session.query(User, Notification, Location).filter(User.id == Notification.user_id, Notification.location_id == id, Location.id == Notification.location_id)
#             with mail.connect() as conn:
#                 for user in users:
#                     subject = '%s Update' % user[2].name
#                     message = '%s is currently EMPTY. Click Here to check the current status.' % user[2].name
#                     html = '''<p>%s is currently EMPTY.
#                             <br>
#                             <a href="http://www.reportthatpantry.org/status"> Click Here</a> to check the current status.</p>''' % user[2].name
#                     msg = Message(recipients=[user[0].email],
#                                 body=message, html=html,
#                                 subject=subject, sender='info.reportthatpantry@gmail.com')
#                     conn.send(msg)
#         elif status == "Damaged":
#             users = db.session.query(User, Notification, Location).filter(User.id == Notification.user_id, Notification.location_id == id, Location.id == Notification.location_id)
#             with mail.connect() as conn:
#                 for user in users:
#                     subject = '%s Update' % user[2].name
#                     message = '%s is currently DAMAGED. Click Here to check the current status.' % user[2].name
#                     html = '''<p>%s is currently DAMAGED.
#                             <br>
#                             <a href="http://www.reportthatpantry.org/status"> Click Here</a> to check the current status.</p>''' % user[2].name
#                     msg = Message(recipients=[user[0].email],
#                                 body=message, html=html,
#                                 subject=subject, sender='info.reportthatpantry@gmail.com')
#                     conn.send(msg)
#         return redirect(url_for('views.home'))
#     return render_template("report.html", user=current_user, title="Report")


# Report on status of given location
@views.route('/report/<int:id>', methods=['GET', 'POST'])
def report(id):
    # Get current location
    location = Location.query.get(id)
    # TODO - check if location exists

    if request.method == 'POST':
        # Extract the fullness level from the form
        pantry_fullness = request.form.get('pantryFullness')

        # Get the description and photo
        description = request.form.get('pantryDescription')
        photo = request.files.get('pantryPhoto')
    
        # Create Report object
        new_report = Report(
            pantry_fullness=pantry_fullness,
            time=datetime.utcnow(),
            location_id=location.id,
            user_id=current_user.id if current_user.is_authenticated else None  # Associate with logged-in user if possible
        )

        # Handle the uploaded photo (if provided)
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_report.photo = filename  # Assuming you have a photo field in your Report model

        db.session.add(new_report)
        db.session.commit()

        # Send email notifications (if applicable)
        # You can modify the conditions for sending emails based on the pantry_fullness value
        # For example:
        # if int(pantry_fullness) <= 33:  # Empty pantry
        #    # ... your email notification code ...

        flash("Thank you for your feedback!", category='success')
        return redirect(url_for('views.home'))

    return render_template("report.html", user=current_user, title="Report", location_id=id) 


@views.route('/status', methods=['GET', 'POST'])
def status():
    # Joins Report and Location tables, ordered by most recently reported
    subquery = db.session.query(Report.user_id, Report.location_id, Report.status,
                                 Report.time, Location.address, Location.city, Location.state,
                                   Location.name.label("location_name"), Location.zip, Location.user_id,
                                   func.rank().over(order_by=Report.time.desc(),
                                    partition_by=Report.location_id).label('rnk')).filter(
                                        Location.id == Report.location_id).subquery()
    # Query most recent update from each location
    locations = db.session.query(subquery).filter(subquery.c.rnk==1)
    # counts number of locations
    count = 0
    for location in locations:
        count += 1

    return render_template("status.html", user=current_user, title="Status", locations=locations, count=count)


# Returns all locations in JSON format
@views.route('/get_locations')
def get_locations():
    locations = Location.query.all()
    location_data = [location.to_dict() for location in locations]
    print(jsonify(location_data))
    return jsonify(location_data)


@views.route('/team')
def team():
    return render_template("team.html", user=current_user, title="Team")

@views.route('/logs/<int:id>')
@views.route('/logs/<int:id>/')
def logs(id):
    count = 0
    # Get report logs for given location
    logs = db.session.query(Report.time, Report.id, Report.status).filter(Report.location_id == id).order_by(Report.time.desc())
    for log in logs:
        count += 1
    return render_template("logs.html", user=current_user, title="Logs", logs=logs, count=count)

@views.route('/poster<int:isNew1>/<int:id>')
@views.route('/poster/<int:isNew1>/<int:id>')
def poster(isNew1, id):
    location = db.session.query(Location.name.label("location_name")).filter(Location.id == id)[0][0]
    return render_template("poster.html", user=current_user, title="Poster", pantrynumber = id, isNew = isNew1, name = location)

@views.route('/setup')
@views.route('/setup/')
def setup():
    return render_template("setup.html", user=current_user, title="Setup")

@views.route('/contactus', methods=['GET','POST'])
@views.route('/contactus/', methods=['GET','POST'])
def contact_us():
    return render_template('contact_us.html', user=current_user, title = 'Contact Us')

@login_required
@views.route('/notifications', methods=['GET', 'POST'])
@views.route('/notifications/', methods=['GET', 'POST'])
def notifications():
    # queries all of the locations under the organization with the user's notification preferances
    locations = db.session.query(Location, Notification).outerjoin(Notification, and_(Notification.location_id == Location.id, current_user.id == Notification.user_id)).order_by(Location.name)
    for location in locations:
        print(location)
    if request.method == "POST":
        # loops through list of locations to find the selected ones
        for location in locations:
            selected_location = request.form.get("location" + str(location[0].id))
            # converts the location id to an integer
            # checks to see if the user is already recieving notifications for a specific loction
            notification = db.session.query(Notification).filter(Notification.location_id == location[0].id, Notification.user_id == current_user.id).first()
            if selected_location:
                selected_location = int(selected_location)
                # if not recieving notification from a selected organization, adds current user and that location to the database
                if not notification:
                    notification = Notification(location_id=location[0].id, user_id=current_user.id)
                    db.session.add(notification)
                    db.session.commit()
            # else if the notification exists, it should be removed
            elif notification:
                db.session.delete(notification)
                db.session.commit()
        flash("Your preferences have been updated.", category="success")
    return render_template("notifications.html", title="Manage Notifications", user=current_user, locations=locations)


@login_required
@views.route('/subscribe/<int:location_id>', methods=['POST'])
@views.route('/subscribe/<int:location_id>/', methods=['POST'])
def subscribe(location_id):
    # Check if user is authenticated
    if not current_user.is_authenticated:
        flash("You must create an account to subscribe to locations.", category='error')
        return redirect(url_for('auth.sign_up'))
    # Check if user if subscription exists for this location
    notification = Notification(location_id=location_id, user_id=current_user.id)

    flash('Subscribed to location {INSERT number}', category='success')
    return redirect(url_for('views.status'))
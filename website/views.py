import os

from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask import jsonify
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import true
from .models import Location, LocationStatus, Notification, Organization, User
from . import db, Message, mail
import json
from datetime import datetime
from time import mktime
from sqlalchemy import func, and_

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@views.route('/index')
@views.route('/<int:id>')
@views.route('/<int:id>/')
def home(id=0):
    # # queries all of the locations
    locations = Location.query.all()

    # if id != 0:
    # location = Location.query.get(id)
    # weight = request.args.get('weight')
    # if weight:
    #     location.weight = weight
    #     db.session.commit()
    return render_template("index.html", user=current_user, locations=locations, title="Home")


# @views.route('/mission')
# def mission():
#     return render_template("mission.html", user=current_user, title="Mission")

@views.route('/locations', methods=['GET', 'POST'])
@views.route('/locations/<int:id>', methods=['GET', 'POST'])
def locations(id=0):
    editing = False
    # queries the location and the organization associated with it
    location = Location.query.get(id)
    current_org = 'none'
    pantrynum = id
    if id != 0:
        # sets editing to true if the post is being edited
        editing = True
        current_org = Organization.query.get(location.organization_id)
    if request.method == 'POST':
        name = request.form.get('name')
        # returns the org as an int representing organization_id
        organization_id = current_user.organization_id
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip = request.form.get('zipCode')
        # if editing changes, reset all fields of the location to the current values
        if id != 0:
            location.name = name
            location.organization_id = current_user.organization_id
            location.address = address
            location.city = city
            location.state = state
            location.zip = zip
            db.session.commit()
            flash('Location edited.', category='success')
            return redirect(url_for("views.status"))

        else:
            # checks if the location exists
            location = Location.query.filter_by(address=address).first()
            if location:
                flash('Address already exists.', category='error')
                return redirect(url_for('views.locations'))
            else:
                # create a location with the following information
                new_location = Location(address=address, name=name, organization_id=organization_id, city=city,
                                        state=state, zip=zip)
                # adds the location to the database
                db.session.add(new_location)
                db.session.commit()
                id = new_location.id
                pantrynum = new_location.id
                # adds a new status row, with status set to full and last_updated to current time
                new_status = LocationStatus(status='Full', time=datetime.utcnow(), location_id=new_location.id)
                db.session.add(new_status)
                db.session.commit()

                # flash('Location added.', category='success')
                # sends user back to home page after new location is created
        return redirect(url_for("views.poster", id=pantrynum, isNew1=1))
    # locations = Location.query.all()
    organizations = Organization.query.all()
    return render_template(
        "locations.html",
        user=current_user,
        editing=editing,
        location=location,
        title="Locations",
        organizations=organizations,
        current_org=current_org,
        google_maps_key=os.getenv('GOOGLE_MAPS_KEY')
    )

    # @views.route('/edit', methods=['GET','POST'])
    # def edit():
    #     return render_template("locations.html", user=current_user)


@views.route('/delete-location', methods=['POST'])
def delete_location():
    print("delete-location")
    location = json.loads(request.data)
    locationId = location['locationId']
    location = Location.query.get(locationId)
    if location:
        # if note.user_id == current_user.id:
        db.session.delete(location)
        db.session.commit()
        flash("Location Deleted.", category="success")

    return jsonify({})


@views.route('report/<int:id>/')
@views.route('/report/<int:id>')
@views.route('/report<int:id>')
def report(id):
    location = Location.query.get(id)
    status = request.args.get('status')
    # a status is given, create add a new location_status to db for the current location
    if status:
        time = datetime.utcnow()
        # sets the location's last update to current time and status to current status
        new_status = LocationStatus(status=status, time=time, location_id=location.id)
        # adds new status to database and commits it
        db.session.add(new_status)
        db.session.commit()
        flash("Thank you for your feedback!", category='success')
        if status == "Empty":
            users = db.session.query(User, Notification, Location).filter(User.id == Notification.user_id,
                                                                          Notification.location_id == id,
                                                                          Location.id == Notification.location_id)
            with mail.connect() as conn:
                for user in users:
                    subject = '%s Update' % user[2].name
                    message = '%s is currently EMPTY. Click Here to check the current status.' % user[2].name
                    html = '''<p>%s is currently EMPTY.
                            <br>
                            <a href="http://www.reportthatpantry.org/status"> Click Here</a> to check the current status.</p>''' % \
                           user[2].name
                    msg = Message(recipients=[user[0].email],
                                  body=message, html=html,
                                  subject=subject, sender='info.reportthatpantry@gmail.com')
                    conn.send(msg)
        elif status == "Damaged":
            users = db.session.query(User, Notification, Location).filter(User.id == Notification.user_id,
                                                                          Notification.location_id == id,
                                                                          Location.id == Notification.location_id)
            with mail.connect() as conn:
                for user in users:
                    subject = '%s Update' % user[2].name
                    message = '%s is currently DAMAGED. Click Here to check the current status.' % user[2].name
                    html = '''<p>%s is currently DAMAGED.
                            <br>
                            <a href="http://www.reportthatpantry.org/status"> Click Here</a> to check the current status.</p>''' % \
                           user[2].name
                    msg = Message(recipients=[user[0].email],
                                  body=message, html=html,
                                  subject=subject, sender='info.reportthatpantry@gmail.com')
                    conn.send(msg)
        return redirect(url_for('views.home'))
    return render_template("report.html", user=current_user, title="Report")


@views.route('/status', methods=['GET', 'POST'])
def status():
    # state = 'FL'
    org = 0
    # # if logged in, only shows locations affiliated with the user's organization
    if current_user.is_authenticated:
        org = current_user.organization_id

    subquery = db.session.query(LocationStatus.location_id, LocationStatus.status, LocationStatus.time,
                                Location.address, Location.city, Location.state, Organization.name,
                                Location.name.label("location_name"), Location.zip,
                                func.rank().over(order_by=LocationStatus.time.desc(),
                                                 partition_by=LocationStatus.location_id).label('rnk')).filter(
        Location.id == LocationStatus.location_id, Location.organization_id == Organization.id).subquery()
    # queries locations and takes the first locations
    locations = db.session.query(subquery).filter(
        subquery.c.rnk == 1)
    # counts number of locations
    count = 0
    for location in locations:
        count += 1
    organizations = Organization.query.all()
    return render_template("status.html", user=current_user, title="Status", locations=locations, count=count,
                           organizations=organizations, current_org=org)


@views.route('/map', methods=['GET', 'POST'])
def map():
    org = 0
    # # if logged in, only shows locations affiliated with the user's organization
    if current_user.is_authenticated:
        org = current_user.organization_id
    subquery = db.session.query(LocationStatus.location_id, LocationStatus.status, LocationStatus.time,
                                Location.address, Location.city, Location.state, Organization.name,
                                Location.name.label("location_name"), Location.zip,
                                func.rank().over(order_by=LocationStatus.time.desc(),
                                                 partition_by=LocationStatus.location_id).label('rnk')).filter(
        Location.id == LocationStatus.location_id, Location.organization_id == Organization.id).subquery()
    # queries locations and takes the first locations
    locations = db.session.query(subquery).filter(
        subquery.c.rnk == 1)
    # counts number of locations
    count = 0
    for location in locations:
        count += 1
    organizations = Organization.query.all()
    return render_template(
        "map.html",
        user=current_user,
        title="Map",
        locations=locations,
        count=count,
        organizations=organizations,
        current_org=org,
        google_maps_key=os.getenv('GOOGLE_MAPS_KEY')
    )


@views.route('/team')
def team():
    return render_template("team.html", user=current_user, title="Team")


# moved to auth.py now to check auth code (can be deleted)
# @views.route('/organizations', methods=['GET','POST'])
# def organizations():
#     if request.method == 'POST':
#         name = request.form.get('name')
#         address = request.form.get('address')
#         # creates new organization
#         org = Organization(name=name, address=address)
#         # adds org to db
#         db.session.add(org)
#         db.session.commit()
#         flash('Organization added. Now create an account under your organization.', category='success')
#         return redirect(url_for('auth.sign_up'))
#     return render_template("organizations.html", user=current_user, title="Add Organization")

@views.route('/logs/<int:id>')
@views.route('/logs/<int:id>/')
def logs(id):
    count = 0
    # count variable used for numbers on logs
    # queries location status table and shows only the current location based on the route
    logs = db.session.query(LocationStatus.time, LocationStatus.id, LocationStatus.status).filter(
        LocationStatus.location_id == id).order_by(LocationStatus.time.desc())
    for log in logs:
        count += 1
    return render_template("logs.html", user=current_user, title="Logs", logs=logs, count=count)


@views.route('/poster<int:isNew1>/<int:id>')
@views.route('/poster/<int:isNew1>/<int:id>')
def poster(isNew1, id):
    location = db.session.query(Location.name.label("location_name")).filter(Location.id == id)[0][0]
    return render_template("poster.html", user=current_user, title="Poster", pantrynumber=id, isNew=isNew1,
                           name=location)


@views.route('/setup')
@views.route('/setup/')
def setup():
    return render_template("setup.html", user=current_user, title="Setup")


@views.route('/contactus', methods=['GET', 'POST'])
@views.route('/contactus/', methods=['GET', 'POST'])
def contact_us():
    return render_template('contact_us.html', user=current_user, title='Contact Us')


@login_required
@views.route('/notifications', methods=['GET', 'POST'])
@views.route('/notifications/', methods=['GET', 'POST'])
def notifications():
    # queries all of the locations under the organization with the users notification preferances
    locations = db.session.query(Location, Notification).outerjoin(Notification,
                                                                   and_(Notification.location_id == Location.id,
                                                                        current_user.id == Notification.user_id)).filter(
        Location.organization_id == current_user.organization_id).order_by(Location.name)
    for location in locations:
        print(location)
    if request.method == "POST":
        # loops through list of locations to find the selected ones
        for location in locations:
            selected_location = request.form.get("location" + str(location[0].id))
            # converts the location id to an integer
            # checks to see if the user is already recieving notifications for a specific loction
            notification = db.session.query(Notification).filter(Notification.location_id == location[0].id,
                                                                 Notification.user_id == current_user.id).first()

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


# @views.route('/sendmail', methods=['GET', 'POST'])
# def sendmail():
#     fname = request.form.get('fname')
#     lname = request.form.get('lname')
#     email = request.form.get('email')
#     state = request.form.get('state')
#     subject = request.form.get('subject')
#     bodyText = 'First name: ' + fname + '\n'
#     bodyText += 'Last name: ' + lname + '\n'
#     bodyText += 'Email: ' + email + '\n'
#     bodyText += 'State: ' + state + '\n'
#     bodyText += 'Message: ' + subject + '\n'
#     msg = Message('Message from \'Contact Us Page\'', sender=email,
#     recipients=['info.reportthatpantry@gmail.com'], body = bodyText)
#     mail.send(msg)
#     return redirect(url_for('views.contact_us'))
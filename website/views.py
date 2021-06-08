from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Location, LocationStatus
from . import db
import json
from datetime import datetime
from sqlalchemy import func

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
    location = Location.query.get(id)
    if id != 0:
        # sets editing to true if the post is being editing
        editing = True
    if request.method == 'POST':
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip = request.form.get('zipCode')
        # if editing changes, reset all fields of the location to the current values
        if id != 0:
            location.address = address
            location.city = city
            location.state = state
            location.zip = zip
            db.session.commit()
            flash('Location edited.', category='success')
        else:
            # checks if the location exists
            location = Location.query.filter_by(address=address).first()
            if location:
                flash('Address already exists.', category='error')
                return redirect(url_for('views.locations'))
            else:
                # create a location with the following information
                new_location = Location(address=address, city=city, state=state, zip=zip, status="Full")
                # adds the location to the database
                db.session.add(new_location)
                db.session.commit()
                # adds a new status row, with status set to full and last_updated to current time
                new_status = LocationStatus(status='Full', time=datetime.utcnow(), location_id=new_location.id)
                db.session.add(new_status)
                db.session.commit()

                flash('Location added.', category='success')
                # sends user back to home page after new location is created
        return redirect(url_for('views.home'))
    return render_template("locations.html", user=current_user, editing=editing, location=location, title="Locations")

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
        #if note.user_id == current_user.id:
        db.session.delete(location)
        db.session.commit()

    return jsonify({})

@views.route('report/<int:id>/')
@views.route('/report/<int:id>')
def report(id):
    location = Location.query.get(id)
    status = request.args.get('status')
    # a status is given, create add a new location_status to db for the current location
    if status:
        time = datetime.utcnow()
        new_status = LocationStatus(status=status, time=time, location_id=location.id)
        # sets the location's last update to current time and status to current status
        location.last_update = time
        location.current_status = status
        # adds new status to database and commits it
        db.session.add(new_status)
        db.session.commit()
        flash("Thank you for your feedback!", category='success')
        return redirect(url_for('views.home'))
        

    return render_template("report.html", user=current_user, title="Report")

@views.route('/status')
def status():
    # subquery that joins both tables together and ranks them
    subquery = db.session.query(LocationStatus.location_id, LocationStatus.status, LocationStatus.time, Location.address, Location.city, Location.state, Location.zip,
    func.rank().over(order_by=LocationStatus.time.desc(),
    partition_by=LocationStatus.location_id).label('rnk')).filter(Location.id == LocationStatus.location_id).subquery()
    # queries locations and takes the first locations
    locations = db.session.query(subquery).filter(
        subquery.c.rnk==1)
    # counts number of locations
    count = 0
    for location in locations:
        count += 1
    return render_template("status.html", user=current_user, title="Status", locations=locations, count=count)

@views.route('/team')
def team():
    return render_template("team.html", user=current_user, title="Team")

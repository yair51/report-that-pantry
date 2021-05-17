from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Location
from . import db
import json

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@views.route('/index')
@views.route('/<int:id>')
@views.route('/<int:id>/')
def home(id=0):
    # # queries all of the locations
    locations = Location.query.all()
    # # loops through all locations
    # for location in locations:
    #     # takes the value from the url key 'weight' + location's id
    #     weight = request.args.get('weight' + str(location.id))
    #     # changes the location's weight if the weight param exists in the url
    #     if weight:
    #         location.weight = weight
    # # changes the value of the weight in the database and on screen
    # db.session.commit()
    #return render_template("index.html", user=current_user, locations=locations, weight=weight)
    if id != 0:
        location = Location.query.get(id)
        weight = request.args.get('weight')
        if weight:
            location.weight = weight
            db.session.commit()
    return render_template("index.html", user=current_user, locations=locations, title="Home")

@views.route('/mission')
def mission():
    return render_template("mission.html", user=current_user, title="Mission")

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
                new_location = Location(address=address, city=city, state=state, zip=zip, weight=0)
                # adds the location to the database
                db.session.add(new_location)
                # resets the ids
                # locations = Location.query.all()
                # for count, location in enumerate(locations, start=1):
                #     location.id = count
                db.session.commit()
                flash('Location added.', category='success')
                # locations = Location.query.all()
                # for place in locations:
                #     print(place.address)
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
        # count = 1
        # locations = Location.query.all()
        # for location in locations:
        #     location.id = count
        #     count += 1
        # db.session.commit()

    return jsonify({})

@views.route('report/<int:id>/')
@views.route('/report/<int:id>')
def report(id):
    location = Location.query.get(id)
    # for i in range(1, 11):
    #     # takes the value from the url key 'weight' + location's id
    #     status = request.args.get('status' + str(i))
    #     # changes the location's weight if the weight param exists in the url
    status = request.args.get('status')
    if status:
        location.status2 = status
        db.session.commit()
        flash("Thank you for your feedback!", category='success')
        return redirect(url_for('views.home'))
        

    return render_template("report.html", user=current_user, title="Report")

@views.route('/status')
def status():
    locations = Location.query.all()
    return render_template("status.html", user=current_user, title="Status", locations=locations)

@views.route('/team')
def team():
    return render_template("team.html", user=current_user, title="Team")

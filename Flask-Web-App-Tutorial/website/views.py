from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Location
from . import db
import json

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@views.route('/index')
def home():
    locations = Location.query.all()
    # counts the number of locations to send to index.html
    # if request.method == 'POST':
    #     note = request.form.get('note')
    #     if len(note) < 1:
    #         flash('Note is too short!', category='error')
    #     else:
    #         new_note = Note(data=note, user_id=current_user.id)
    #         db.session.add(new_note)
    #         db.session.commit()
    #         flash('Note added!', category='success')

    return render_template("index.html", user=current_user, locations=locations)

@views.route('/about')
def about():
    return render_template("about.html", user=current_user)

@views.route('/locations', methods=['GET', 'POST'])
def locations():
    if request.method == 'POST':
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip = request.form.get('zipCode')
        # checks if the location exists
        location = Location.query.filter_by(address=address).first()
        if location:
            flash('Address already exists.', category='error')
            return redirect(url_for('views.locations'))
        else:
            # create a location with the following information
            new_location = Location(address=address, city=city, state=state, zip=zip)
            # adds the location to the database
            db.session.add(new_location)
            db.session.commit()
            flash('Location added.', category='success')
            # locations = Location.query.all()
            # for place in locations:
            #     print(place.address)
            # sends user back to home page after new location is created
            return redirect(url_for('views.home'))
    return render_template("locations.html", user=current_user)


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

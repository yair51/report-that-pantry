from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import true
from sqlalchemy.orm import joinedload
from .models import Location, Report, Notification, User
from . import db, Message, mail
import json
from datetime import datetime
from time import mktime
from sqlalchemy import func, and_, desc
from werkzeug.utils import secure_filename
import os
import base64  # Import base64 for encoding images
from PIL import Image, ImageOps
import io
import uuid

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@views.route('/index')
def home(id=0):
    # # queries all of the locations
    locations = Location.query.all()

    return render_template("index.html", user=current_user, title="Home")


@views.route('/location/<int:location_id>')
def location(location_id):
    # Unauthenticated user has no subscribed locations
    subscribed_locations = None
    # Eager load reports for the location
    location = Location.query.options(joinedload(Location.reports)).get_or_404(location_id)

    # Get user's subscribed locations if authenticated
    if current_user.is_authenticated:
            subscribed_locations = [notification.location_id for notification in current_user.notifications]
            print(subscribed_locations)



    # Get the latest report
    latest_report = location.reports[-1] if location.reports else None  # Handle the case where there are no reports

    # Check if user can edit this location
    can_edit = current_user.is_authenticated and location.user_id == current_user.id
    return render_template("pantry.html", user=current_user, location=location, latest_report=latest_report, subscribed_locations=subscribed_locations, can_edit=can_edit, title="Pantry Details")


# Determines if file submitted is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@views.route('/location/add', methods=['GET', 'POST'])
@views.route('/location/add/', methods=['GET', 'POST'])
@login_required
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
        description = request.form.get('description')
        contact_info = request.form.get('contactInfo')

        # checks if the location exists
        location = Location.query.filter_by(address=address).first()
        if location:
            flash('Address already exists.', category='error')
            return render_template()
    

        print(zip.isnumeric())
        if not zip.isnumeric():
            flash('Zip code must contain only digits.', category='error')
            return redirect(url_for("views.add_location"))
            # return render_template("locations2.html", user=current_user, location=location, editing=True, title="Edit Location", states=us_states)
        # Add location to database
        new_location = Location(
            address=address, 
            name=name, 
            city=city, 
            state=state, 
            zip=zip,
            user_id=current_user.id,
            description=description,
            contact_info=contact_info
        )
        db.session.add(new_location)
        db.session.commit()

        # Handle photo upload
        photo = request.files.get('locationPhoto')  # Get the uploaded file
        photo_path = None
        # Check if photo exists and file type is allowed
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            # Create or access location file directory
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(new_location.id))
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            photo.save(save_path)
            # Update database value
            new_location.photo = filename
            db.session.commit()
            
        # Add location to database
        # else:
        #     new_location = Location(address=address, name=name, city=city, state=state, zip=zip)
        #     db.session.add(new_location)
        #     db.session.commit()
        # id = new_location.id

        # Create intial status update for location
        new_status = Report(pantry_fullness=100, time=datetime.utcnow(), location_id=new_location.id)
        db.session.add(new_status)
        db.session.commit()

        # Redirect user to poster page
        return redirect(url_for("views.poster", id=new_location.id, isNew1=1))

    return render_template("location.html", user=current_user, editing=False, title="Add Location", states=us_states)


# Edit Location
@views.route('/location/edit/<int:location_id>', methods=['GET', 'POST'])
@views.route('/location/edit/<int:location_id>/', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)

    # Check if the user owns this location
    if location.user_id != current_user.id:
        flash("You do not have permission to edit this location.", category='error')
        return redirect(url_for('views.status'))

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zipCode')
        description = request.form.get('description')
        photo = request.files.get('locationPhoto')
        contact_info = request.form.get('contactInfo')


        # Basic input validation (add more as needed)
        if not all([name, address, city, state, zip_code]):
            flash('All fields are required.', category='error')
        else:
            # Update location details
            location.name = name
            location.address = address
            location.city = city
            location.state = state
            location.zip = zip_code
            location.description = description
            location.contact_info = contact_info

            # Handle photo update (if a new photo is uploaded)
            if photo and allowed_file(photo.filename):
                # Delete old photo if exists
                if location.photo:
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], location.photo))
                    except FileNotFoundError:
                        pass  # Ignore if the file is already deleted

                filename = secure_filename(photo.filename)
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(location.id))
                os.makedirs(upload_dir, exist_ok=True)
                save_path = os.path.join(upload_dir, filename)
                photo.save(save_path)

                # Store the filename in uploads folder
                location.photo = filename

            db.session.commit()
            flash('Location updated successfully!', category='success')
            return redirect(url_for('views.location', location_id=location.id))

    return render_template("locations.html", user=current_user, location=location, editing=True, title="Edit Location", states=us_states)


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



# Report on status of given location
@views.route('/report/<int:id>', methods=['GET', 'POST'])
def report(id):
    # Get current location
    location = Location.query.get(id)
    if not location:
        flash("Location does not exist.", category='error')
        return redirect(url_for('views.status'))

    if request.method == 'POST':
        # Get fullness level from the form
        pantry_fullness = request.form.get('pantryFullness')

        # Get the description and photo
        description = request.form.get('pantryDescription')

        print(description)
        photo = request.files.get('pantryPhoto')
    
        # Create Report object
        new_report = Report(
            pantry_fullness=pantry_fullness,
            time=datetime.utcnow(),
            location_id=location.id,
            description=description,
            user_id=current_user.id if current_user.is_authenticated else None  # Associate with logged-in user if possible
        )

        # Add photo to uploads folder
        if photo:
            filename = secure_filename(photo.filename)
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(location.id))
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            photo.save(save_path)
            # Store the relative path (relative to the UPLOAD_FOLDER)
            relative_path = os.path.join(str(location.id), filename)  # Adjust if necessary
            new_report.photo = filename 

        db.session.add(new_report)
        db.session.commit()

        # Send email notification if the pantry is empty
        if new_report.pantry_fullness <= 33:  # Check for empty status
            image_data = None
            if new_report.photo:
                with open(os.path.join(current_app.config['UPLOAD_FOLDER'], str(location.id), new_report.photo), "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()  # Encode image to base64

            send_notification_emails(location, new_report, image_data)

        flash("Thank you for your feedback!", category='success')
        return redirect(url_for('views.location', location_id=id))

    return render_template("report.html", user=current_user, title="Report", location_id=id) 




@views.route('/uploads/<int:location_id>/<filename>')  
def uploaded_file(location_id, filename):
    # Construct the full path to the uploads directory for the given location
    uploads_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(location_id))
    print(uploads_folder)

    # Check if the file exists and is allowed
    if not filename or not os.path.exists(os.path.join(uploads_folder, filename)):
        abort(404)  # Return 404 Not Found if file doesn't exist
    
    # Check if the file extension is allowed (optional, but recommended)
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        abort(403)  # Return 403 Forbidden for invalid file types

    return send_from_directory(uploads_folder, filename) 




@views.route('/status', methods=['GET', 'POST'])
def status():
    # Get every report for every location, ordered by report time
    locations = db.session.query(Location).options(joinedload(Location.reports)).all()
    # Safely access subscribed_locations only if the user is authenticated
    subscribed_locations = [notification.location_id for notification in current_user.notifications] if current_user.is_authenticated else []


    return render_template("status.html", user=current_user, title="Status", locations=locations, subscribed_locations=subscribed_locations)



# Returns all locations in JSON format
@views.route('/get_locations')
def get_locations():
    locations = Location.query.all()
    location_data = [location.to_dict() for location in locations]
    print(jsonify(location_data))
    return jsonify(location_data)


# @views.route('/team')
# def team():
#     return render_template("team.html", user=current_user, title="Team")

@views.route('/logs/<int:id>')
@views.route('/logs/<int:id>/')
def logs(id):
    count = 0
    # Get report logs for given location
    logs = db.session.query(Report.time, Report.id, Report.pantry_fullness).filter(Report.location_id == id).order_by(Report.time.desc())
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

# @views.route('/contactus', methods=['GET','POST'])
# @views.route('/contactus/', methods=['GET','POST'])
# def contact_us():
#     return render_template('contact_us.html', user=current_user, title = 'Contact Us')

# @login_required
# @views.route('/notifications', methods=['GET', 'POST'])
# @views.route('/notifications/', methods=['GET', 'POST'])
# def notifications():
#     # queries all of the locations under the organization with the user's notification preferances
#     locations = db.session.query(Location, Notification).outerjoin(Notification, and_(Notification.location_id == Location.id, current_user.id == Notification.user_id)).order_by(Location.name)
#     for location in locations:
#         print(location)
#     if request.method == "POST":
#         # loops through list of locations to find the selected ones
#         for location in locations:
#             selected_location = request.form.get("location" + str(location[0].id))
#             # converts the location id to an integer
#             # checks to see if the user is already recieving notifications for a specific loction
#             notification = db.session.query(Notification).filter(Notification.location_id == location[0].id, Notification.user_id == current_user.id).first()
#             if selected_location:
#                 selected_location = int(selected_location)
#                 # if not recieving notification from a selected organization, adds current user and that location to the database
#                 if not notification:
#                     notification = Notification(location_id=location[0].id, user_id=current_user.id)
#                     db.session.add(notification)
#                     db.session.commit()
#             # else if the notification exists, it should be removed
#             elif notification:
#                 db.session.delete(notification)
#                 db.session.commit()
#         flash("Your preferences have been updated.", category="success")
#     return render_template("notifications.html", title="Manage Notifications", user=current_user, locations=locations)






# Handles changes to subscription preferences on status page
@views.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    location_id = request.form.get('location_id')

    if location_id:
        location_id = int(location_id)
        # Check if the user is already subscribed
        existing_subscription = Notification.query.filter_by(user_id=current_user.id, location_id=location_id).first()
        
        if existing_subscription:
            # Unsubscribe
            db.session.delete(existing_subscription)
            db.session.commit()
            return jsonify({'status': 'unsubscribed', 'message': 'Unsubscribed successfully'})
        else:
            # Subscribe
            new_subscription = Notification(user_id=current_user.id, location_id=location_id)
            db.session.add(new_subscription)
            db.session.commit()
            return jsonify({'status': 'subscribed', 'message': 'Subscribed successfully'})

    return jsonify({'status': 'error', 'message': 'Invalid location_id'})


# Handles changes to subscription preferances on pantry homepage
@views.route('/location/subscribe/<int:location_id>', methods=['POST'])
@login_required
def subscribe_location(location_id):
    # Check if location exists
    location = Location.query.get(location_id)
    print(location)
    if location:
        location_id = int(location_id)
        # Check if the user is already subscribed and toggle the subscription
        existing_subscription = Notification.query.filter_by(user_id=current_user.id, location_id=location_id).first()
        
        if existing_subscription:
            # Unsubscribe
            db.session.delete(existing_subscription)
            db.session.commit()
            flash('You have successfully unsubscribed from this pantry.', 'success')
        else:
            # Subscribe
            new_subscription = Notification(user_id=current_user.id, location_id=location_id)
            db.session.add(new_subscription)
            db.session.commit()
            flash('You have successfully subscribed to this pantry.', 'success')
    else:
        flash("Location does not exist", category='error')
        return redirect(url_for('views.location', location_id=location_id))

    return redirect(url_for('views.location', location_id=location_id))  # Redirect back to the location page


def send_notification_emails(location, report, image_data=None):
    recipients = [n.user.email for n in location.notifications] 
    if recipients:
        subject = f"{location.name} is Empty!"
        message = f"The Little Free Pantry located at {location.address}, {location.city}, {location.state} is currently empty.<br>"
        message += "Can you help restock it?<br>"
        if report.description:
            message += f"Description: {report.description}<br>"
        message += f"View more details: <a href='{url_for('views.location', location_id=location.id, _external=True)}''>{url_for('views.location', location_id=location.id, _external=True)}</a>"

        html = f"""
            <p>{message}</p>
            """
        if report.photo:
            with Image.open(os.path.join(current_app.config['UPLOAD_FOLDER'], str(report.location_id), report.photo)) as img:
                # Transpose image
                img = ImageOps.exif_transpose(img)
                img.thumbnail((800, 800))  # Resize 
                # If image has an alpha channel, convert to RGB
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGB')
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", optimize=True, quality=85)
                img_data = base64.b64encode(buffer.getvalue()).decode()

            filename = f"{uuid.uuid4().hex}.jpg"
            html += f'<img src="data:image/jpeg;base64,{img_data}" alt="Pantry Photo" style="max-width: 100%; height: auto; image-orientation: from-image;">'  # Force upright display
            
        with mail.connect() as conn:
            for recipient in recipients:
                msg = Message(subject, sender='info.reportthatpantry@gmail.com', recipients=[recipient])
                msg.html = html
                conn.send(msg)


# List of US states and abbreviations
us_states = {
        "Alabama": "AL",
        "Alaska": "AK",
        "Arizona": "AZ",
        "Arkansas": "AR",
        "California": "CA",
        "Colorado": "CO",
        "Connecticut": "CT",
        "Delaware": "DE",
        "Florida": "FL",
        "Georgia": "GA",
        "Hawaii": "HI",
        "Idaho": "ID",
        "Illinois": "IL",
        "Indiana": "IN",
        "Iowa": "IA",
        "Kansas": "KS",
        "Kentucky": "KY",
        "Louisiana": "LA",
        "Maine": "ME",
        "Maryland": "MD",
        "Massachusetts": "MA",
        "Michigan": "MI",
        "Minnesota": "MN",
        "Mississippi": "MS",
        "Missouri": "MO",
        "Montana": "MT",
        "Nebraska": "NE",
        "Nevada": "NV",
        "New Hampshire": "NH",
        "New Jersey": "NJ",
        "New Mexico": "NM",
        "New York": "NY",
        "North Carolina": "NC",
        "North Dakota": "ND",
        "Ohio": "OH",
        "Oklahoma": "OK",
        "Oregon": "OR",
        "Pennsylvania": "PA",
        "Rhode Island": "RI",
        "South Carolina": "SC",
        "South Dakota": "SD",
        "Tennessee": "TN",
        "Texas": "TX",
        "Utah": "UT",
        "Vermont": "VT",
        "Virginia": "VA",
        "Washington": "WA",
        "West Virginia": "WV",
        "Wisconsin": "WI",
        "Wyoming": "WY"
    }

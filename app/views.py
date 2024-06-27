from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import true
from sqlalchemy.orm import joinedload
from .models import Location, Report, Notification, User
from app.helpers import send_email, allowed_file, upload_photo_to_s3, delete_photo_from_s3
from . import db, Message, mail
import json
from datetime import datetime, timezone
from time import mktime
from sqlalchemy import func, and_, desc
from werkzeug.utils import secure_filename
import os
import base64  # Import base64 for encoding images
from PIL import Image, ImageOps
import io
import uuid
import boto3
from boto3 import s3

views = Blueprint('views', __name__)


# Takes a report and location as arguments and sends notification emails for that location
def send_notification_emails(location, report, image_data=None):
    recipients = [n.user.email for n in location.notifications] 
    if recipients:
        subject = f"{location.name} is Empty!"
        message = f"The Little Free Pantry located at {location.address}, {location.city}, {location.state} is currently empty.<br>"
        message += "Can you help restock it?<br>"
        if report.description:
            message += f"Description: {report.description}<br>"
        if report.photo:
            message += "New pantry photo available on website!<br>"
        message += f"View more details: <a href='{url_for('views.location', location_id=location.id, _external=True)}''>{url_for('views.location', location_id=location.id, _external=True)}</a>"


        html = f"""
            <p>{message}</p>
            """
        
        send_email(recipients, subject, html)

        # TODO - show photo in email
        # if report.photo:
        #     with Image.open(os.path.join(current_app.config['UPLOAD_FOLDER'], str(report.location_id), report.photo)) as img:
        #         # Transpose image
        #         img = ImageOps.exif_transpose(img)
        #         img.thumbnail((800, 800))  # Resize 
        #         # If image has an alpha channel, convert to RGB
        #         if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        #             img = img.convert('RGB')
        #         buffer = io.BytesIO()
        #         img.save(buffer, format="JPEG", optimize=True, quality=85)
        #         img_data = base64.b64encode(buffer.getvalue()).decode()

        #     filename = f"{uuid.uuid4().hex}.jpg"
        #     html += f'<img src="data:image/jpeg;base64,{img_data}" alt="Pantry Photo" style="max-width: 100%; height: auto; image-orientation: from-image;">'  # Force upright display
            
        # with mail.connect() as conn:
        #     for recipient in recipients:
        #         msg = Message(subject, sender='info.reportthatpantry@gmail.com', recipients=[recipient])
        #         msg.html = html
        #         conn.send(msg)



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
    return render_template("pantry.html", user=current_user, location=location, latest_report=latest_report, subscribed_locations=subscribed_locations, can_edit=can_edit, current_app=current_app, title="Pantry Details")


# # Determines if file submitted is allowed
# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# Route for adding a location
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
        photo = request.files.get('locationPhoto')  # Get the uploaded file


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

        # Handle photo upload to S3
        s3_key = upload_photo_to_s3(photo, new_location.id)
        if s3_key:
            new_location.photo = s3_key
        db.session.commit()

        # # Check if photo exists and file type is allowed
        # if photo and allowed_file(photo.filename):
        #     filename = secure_filename(photo.filename)
        #     # Create or access location file directory
        #     upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(new_location.id))
        #     os.makedirs(upload_dir, exist_ok=True)
        #     save_path = os.path.join(upload_dir, filename)
        #     photo.save(save_path)
        #     # Update database value
        #     new_location.photo = filename
        #     db.session.commit()

        # Create intial report for location
        new_report = Report(
            pantry_fullness=100,
            time=datetime.now(timezone.utc),  # Use timezone-aware datetime in UTC
            location_id=new_location.id
            )
        db.session.add(new_report)
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
                # Delete old photo if it exists
                if location.photo:
                    s3_key = location.photo
                    delete_photo_from_s3(s3_key)
                # Upload new photo
                s3_key = upload_photo_to_s3(photo, location_id)
                if s3_key:
                    location.photo = s3_key
            # Commit changes
            db.session.commit()
            flash('Location updated successfully!', category='success')
            return redirect(url_for('views.location', location_id=location.id))

    return render_template("location.html", current_app=current_app, user=current_user, location=location, editing=True, title="Edit Location", states=us_states)


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
        photo = request.files.get('pantryPhoto')
    
        # Create Report object
        new_report = Report(
            pantry_fullness=pantry_fullness,
            time=datetime.now(timezone.utc),  # Use timezone-aware datetime in UTC
            location_id=location.id,
            description=description,
            user_id=current_user.id if current_user.is_authenticated else None  # Associate with logged-in user if possible
        )
        # Upload photo to Amazon S3, if provided
        s3_key = upload_photo_to_s3(photo, location.id)
        # Store relative path in database
        if s3_key:
            new_report.photo = s3_key
        db.session.add(new_report)
        db.session.commit()


        # TODO - send image in email
        # if new_report.photo:
        #     with open(os.path.join(current_app.config['UPLOAD_FOLDER'], str(location.id), new_report.photo), "rb") as f:
        #         image_data = base64.b64encode(f.read()).decode()  # Encode image to base64
        # Send email notification if the pantry is empty
        if new_report.pantry_fullness <= 33:  # Check for empty status
            recipients = [n.user.email for n in location.notifications] 
            if recipients:
                subject = f"{location.name} is Empty!"
                message = f"The Little Free Pantry located at {location.address}, {location.city}, {location.state} is currently empty.<br>"
                message += "Can you help restock it?<br>"
                if new_report.description:
                    message += f"Description: {new_report.description}<br>"
                if new_report.photo:
                    message += "New pantry photo available on website!<br>"
                message += f"View more details: <a href='{url_for('views.location', location_id=location.id, _external=True)}''>{url_for('views.location', location_id=location.id, _external=True)}</a>"
                html = f"""
                    <p>{message}</p>
                    """
                send_email(recipients, subject, html)
            # send_notification_emails(location, new_report, image_data)

        flash("Thank you for your feedback!", category='success')
        return redirect(url_for('views.location', location_id=id))

    return render_template("report.html", user=current_user, title="Report", location_id=id) 



# Route to serve images from S3
@views.route('/uploads/<filename>')
def uploaded_file(filename):
    s3 = boto3.client(
        's3',
        aws_access_key_id=current_app.config['S3_KEY'],
        aws_secret_access_key=current_app.config['S3_SECRET']
    )
    url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': current_app.config['S3_BUCKET'],
            'Key': filename
        },
        ExpiresIn=3600
    )  # URL valid for 1 hour
    return redirect(url, code=302)


@views.route('/status', methods=['GET', 'POST'])
def status():
    # Get every report for every location, ordered by report time
    locations = db.session.query(Location).options(joinedload(Location.reports)).all()
    # Safely access subscribed_locations only if the user is authenticated
    subscribed_locations = [notification.location_id for notification in current_user.notifications] if current_user.is_authenticated else []
    return render_template("status.html", user=current_user, title="Status", locations=locations, subscribed_locations=subscribed_locations)


# Returns all locations in JSON format (for status page)
@views.route('/get_locations')
def get_locations():
    locations = db.session.query(Location).options(joinedload(Location.reports)).all()
    location_data = []
    for location in locations:
        # Get latest report
        latest_report = location.reports[-1] if location.reports else None
        data = {
            'id': location.id,  # Use location.id instead of location.location_id
            'location': f"{location.name}<br>{location.address}, {location.city}, {location.state}",
            'time': latest_report.time.timestamp() if latest_report else None
        }
        location_data.append(data)
    print(jsonify(location_data))
    return jsonify(location_data)


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

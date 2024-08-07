from . import db
from flask import url_for
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime, timezone


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    age = db.Column(db.Integer, nullable=True)
    user_type = db.Column(db.String(150))
    notifications = db.relationship('Notification', backref='user')
    locations = db.relationship('Location', backref='user')
    reports = db.relationship('Report', backref='user')


class Location(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    address = db.Column(db.String(150), unique=True)
    city = db.Column(db.String(150))
    state = db.Column(db.String(50))
    zip = db.Column(db.Integer)
    photo = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    contact_info = db.Column(db.String(250))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reports = db.relationship('Report', backref='location')
    notifications = db.relationship('Notification', backref='location')


    def to_dict(self):
        return {
            'id': self.location_id,
            'location': f"{self.location_name}<br>{self.address}, {self.city}, {self.state}",
            'status': self.status,
            'time': self.time.strftime("%c")  # Format the datetime object
        }

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pantry_fullness  = db.Column(db.Integer)
    time = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    photo = db.Column(db.String(150), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    # points = db.Column(db.Integer)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Return path to photo on server
    def get_photo_url(self):
        if self.photo:
            return url_for('views.uploaded_file', location_id=self.location_id, filename=self.photo)
        else:
            return None

    # Get interpretation of status based on pantry fullness
    def get_status(self):
        fullness = self.pantry_fullness
        if fullness is None:
            return "Unknown"
        elif fullness > 66:
            return "Full"
        elif fullness > 33:
            return "Half Full"
        else:
            return "Empty"



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    low_inventory = db.Column(db.Boolean, default=True)   
    # ... other preferences you want to add ...



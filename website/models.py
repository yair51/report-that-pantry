from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime


# class Note(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     data = db.Column(db.String(10000))
#     date = db.Column(db.DateTime(timezone=True), default=func.now())
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    notifications = db.relationship('Notification', backref='user')

class Location(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    address = db.Column(db.String(150), unique=True)
    city = db.Column(db.String(150))
    state = db.Column(db.String(50))
    zip = db.Column(db.Integer)
    location_status = db.relationship('LocationStatus', backref='location')
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    notifications = db.relationship('Notification', backref='location')

class LocationStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(150))
    time = db.Column(db.DateTime, default=datetime.utcnow)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True)
    address = db.Column(db.String(150))
    locations = db.relationship('Location', backref='organization')
    users = db.relationship('User', backref='organization')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


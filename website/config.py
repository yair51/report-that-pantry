import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dfal;dfkad adf'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
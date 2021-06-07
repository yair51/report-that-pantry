import os

class Config(object):
    DEBUG = False
    DEVELOPMENT = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dfal;dfkad adf'
    SQLALCHEMY_DATABASE_URI = 'postgresql://qtpqgzckodngbz:3c43be88e6456a266d1b60c4795ad491661d3c5f1a0920820598d8580efa960d@ec2-107-22-83-3.compute-1.amazonaws.com:5432/dbs7vbee5trfb5'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:tamara12@localhost/tlc_pantry'


    
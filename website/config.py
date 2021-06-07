import os

class Config(object):
    DEBUG = False
    DEVELOPMENT = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dfal;dfkad adf'
    #SQLALCHEMY_DATABASE_URI = 'postgresql://qtpqgzckodngbz:3c43be88e6456a266d1b60c4795ad491661d3c5f1a0920820598d8580efa960d@ec2-107-22-83-3.compute-1.amazonaws.com:5432/dbs7vbee5trfb5'
    #SQLALCHEMY_DATABASE_URI = 'postgresql://liiwdhxggjphlp:10cf08d71a8e9b0610ccb156062a2d83ca2dcefe312aba9476e7da417b5fc352@ec2-3-212-75-25.compute-1.amazonaws.com:5432/d3q5mm115bmus7'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:tamara12@localhost/tlc_pantry'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///database1.db'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:tamara12@localhost/tlc_pantry'


    
import os
from dotenv import load_dotenv
load_dotenv()

class Config(object):
    DEBUG = False
    DEVELOPMENT = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dfal;dfkad adf")
    #SECRET_KEY = os.environ.get('SECRET_KEY') or 'dfal;dfkad adf'
    SQLALCHEMY_DATABASE_URI = 'postgresql://qtpqgzckodngbz:3c43be88e6456a266d1b60c4795ad491661d3c5f1a0920820598d8580efa960d@ec2-107-22-83-3.compute-1.amazonaws.com:5432/dbs7vbee5trfb5'
    # url is just a filler, uri is being used
    DATABASE_URL = "sqlite:///database.db"

    #SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class StagingConfig(Config):
    #SQLALCHEMY_DATABASE_URI = 'postgresql://liiwdhxggjphlp:10cf08d71a8e9b0610ccb156062a2d83ca2dcefe312aba9476e7da417b5fc352@ec2-3-212-75-25.compute-1.amazonaws.com:5432/d3q5mm115bmus7'
    if os.getenv("APP_SETTINGS") == "StagingConfig":
        SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[10:]
    #print(os.getenv("APP_SETTINGS"))
    #SQLALCHEMY_DATABASE_URI = "postgresql"
    #SQLALCHEMY_DATABASE_URI = "postgresql://cexzaxuopblmgq:eb3cff5072084b4ccb7d03e31a5bc3c0d515152571665c49e9f18d8c80265053@ec2-3-231-69-204.compute-1.amazonaws.com:5432/d5qjsv73ilnuiu"

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True
    # using the uri, the url is just a filler
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///database.db")
    FLASK_APP = "main.py"
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///database1.db'


    
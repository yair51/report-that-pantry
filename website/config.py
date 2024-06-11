import os
from dotenv import load_dotenv
load_dotenv()

class Config(object):
    DEBUG = False
    DEVELOPMENT = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dfal;dfkad adf")
    if os.getenv("APP_SETTINGS") == "Config":
        SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    UPLOAD_FOLDER = 
    

class StagingConfig(Config):
    if os.getenv("APP_SETTINGS") == "StagingConfig":
        SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///database.db")
    FLASK_APP = "main.py"
    MAIL_SERVER ='smtp.mailtrap.io'
    MAIL_PORT = 2525
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    


    
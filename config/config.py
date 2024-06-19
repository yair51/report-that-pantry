import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = False
    DEVELOPMENT = False
    TESTING = False
    FLASK_APP = "main.py"
    SECRET_KEY = os.getenv("SECRET_KEY")  # No default; this should always be set externally
    SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]  # Include +psycopg2
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS')  == 'True'  
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL')  == 'True' 
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'instance', 'uploads')

class ProductionConfig(Config):
    FLASK_ENV = 'production'

class StagingConfig(Config):
    FLASK_ENV = 'staging'

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True
    FLASK_ENV = 'development'
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")


# import os
# from dotenv import load_dotenv
# load_dotenv()

# class Config(object):
#     DEBUG = False
#     DEVELOPMENT = False
#     SECRET_KEY = os.getenv("SECRET_KEY", "dfal;dfkad adf")
#     if os.getenv("APP_SETTINGS") == "Config":
#         SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     MAIL_SERVER = 'smtp.gmail.com'
#     MAIL_PORT = 465
#     MAIL_USE_TLS = False
#     MAIL_USE_SSL = True
#     MAIL_USERNAME = os.getenv("MAIL_USERNAME")
#     MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
#     UPLOAD_FOLDER = os.path.join(os.getcwd(), 'instance', 'uploads')  # Use a dynamic path for uploads

    
# class StagingConfig(Config):
#     if os.getenv("APP_SETTINGS") == "StagingConfig":
#         SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]


# class DevelopmentConfig(Config):
#     DEBUG = True
#     DEVELOPMENT = True
#     SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///database.db")
#     FLASK_APP = "main.py"
#     MAIL_USERNAME = os.getenv("MAIL_USERNAME")
#     MAIL_SERVER ='smtp.mailtrap.io'
#     MAIL_PORT = 2525
#     MAIL_USE_TLS = True
#     MAIL_USE_SSL = False
#     APP_SETTINGS = "DevelopmentConfig"
    


    
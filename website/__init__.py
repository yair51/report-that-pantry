from flask import Flask
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from os import path, getenv
from flask_login import LoginManager, current_user
from .config import DevelopmentConfig, Config, StagingConfig
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask import render_template, request, redirect

db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)
    # sets development/production enviornment
    #env_config = DevelopmentConfig
    env_config = getenv("APP_SETTINGS", "DevelopmentConfig")
    if env_config == 'Config':
        env_config = Config
    elif env_config == 'StagingConfig':
        env_config = StagingConfig
    else:
        env_config = DevelopmentConfig
    print(env_config)
    app.config.from_object(env_config)
    # app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    # app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    # mail config: 
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config["MAIL_USE_TLS"]= False
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = 'info.reportthatpantry@gmail.com'
    app.config['MAIL_PASSWORD'] = 'vrucxrsmpacwcdsk'
    
    email = Mail(app)

    @app.route('/sendmail', methods=['GET', 'POST'])
    def sendmail():
        bodyText = 'First name: ' + request.form['fname'] + '\n'
        bodyText += 'Last name: ' + request.form['lname'] + '\n'
        bodyText += 'Email: ' + request.form['email'] + '\n'
        bodyText += 'State: ' + request.form['state'] + '\n'
        bodyText += 'Message: ' + request.form['subject'] + '\n'
        msg = Message('Message from \'Contact Us Page\'', sender= 'info.reportthatpantry@gmail.com', 
        recipients=['info.reportthatpantry@gmail.com'], body = bodyText)
        email.send(msg)
        return redirect(url_for('views.contact_us'))

    
    db.init_app(app)
    migrate.init_app(app, db)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Location, LocationStatus

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    # if not path.exists('website/' + DB_NAME):
    db.create_all(app=app)
    print('Created Database!')
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
load_dotenv()     # charge .env
import config     # configure Cloudinary



app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','you-will-never-guess')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL','sqlite:///gestock2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# create login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"



import routes, models



# with app.app_context():
#     db.create_all()

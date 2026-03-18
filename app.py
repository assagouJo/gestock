from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

load_dotenv()
import config
from config import CurrentConfig

app = Flask(__name__)

# Configurations de base
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'you-will-never-guess')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Appliquer la configuration (qui contient SQLALCHEMY_ENGINE_OPTIONS adaptée)
app.config.from_object(CurrentConfig)

# 🔥 VÉRIFICATION IMPORTANTE
print(f"🔧 Environnement: {config.ENV}")
print(f"💾 Base de données: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(f"⚙️  Engine options: {app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})}")

# Upload folder
UPLOAD_FOLDER = os.path.join('static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialisation
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Fermeture des connexions
@app.after_request
def close_db_connection(response):
    try:
        db.session.close()
    except:
        pass
    return response

# Imports
import models
import audit
import routes
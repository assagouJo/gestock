import cloudinary
import os
from datetime import timedelta

# Configuration Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

class Config:
    """Configuration de base"""
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuration du pool - sera adaptée selon la base
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # Autres configurations
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'

class DevelopmentConfig(Config):
    """Configuration pour le développement (SQLite)"""
    DEBUG = True
    
    # Pas d'options spéciales pour SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': False,  # SQLite n'en a pas besoin
    }

class ProductionConfig(Config):
    """Configuration pour la production (PostgreSQL sur Render)"""
    DEBUG = False
    
    # Options uniquement pour PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 240,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'sslmode': 'require'
        }
    }

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Choisir la configuration selon l'environnement
config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'test': TestingConfig
}

# Détection automatique de l'environnement
ENV = os.getenv('FLASK_ENV', 'dev')
if os.getenv('RENDER'):  # Sur Render, on est en prod
    ENV = 'prod'

CurrentConfig = config_by_name.get(ENV, DevelopmentConfig)
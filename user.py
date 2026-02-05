from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(username='joel', email='admin@ad.com', role='admin')
        user.set_password('12345')
        db.session.add(user)
        db.session.commit()
        print("Utilisateur test créé")
    else:
        print("Utilisateur test existe déjà")

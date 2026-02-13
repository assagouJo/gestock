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



# def creer_magasins_defaut():
#     magasins_defaut = ["Imedical", "Lavilla", "Gonzague"]

#     for nom in magasins_defaut:
#         existe = Magasin.query.filter_by(nom=nom).first()
#         if not existe:
#             db.session.add(Magasin(nom=nom))

#     db.session.commit()

# with app.app_context():
#     creer_magasins_defaut()

# ####################################

# def creer_vendeur_compagnie_defaut():
#     vendeur_compagnie_defaut = ["Imedical", "Fuji"]

#     for nom in vendeur_compagnie_defaut:
#         existe = VendeurCompagnie.query.filter_by(nom=nom).first()
#         if not existe:
#             db.session.add(VendeurCompagnie(nom=nom))

#     db.session.commit()

# with app.app_context():
#     creer_vendeur_compagnie_defaut()

######################################


# @app.route("/create-admin")
# def create_admin():
#     # éviter doublon
#     user = User.query.filter_by(username="admin").first()
#     if user:
#         return "Admin already exists"

#     user = User(
#         username="admin",
#         email="admin@gestock.com",
#         password_hash=generate_password_hash("admin123"),
#         role="admin"
#     )
#     db.session.add(user)
#     db.session.commit()
#     return "Admin created"
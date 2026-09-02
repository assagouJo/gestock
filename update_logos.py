from app import app, db
from models import Compagnie

with app.app_context():
    fuji = Compagnie.query.filter_by(nom="Fuji").first()
    if fuji:
        fuji.logo = "fuji.jpeg"
        print("Logo Fuji mis à jour")
    else:
        print("Fuji introuvable")

    imedical = Compagnie.query.filter_by(nom="iMedical").first()
    if imedical:
        imedical.logo = "imedical.jpeg"
        print("Logo iMedical mis à jour")
    else:
        print("iMedical introuvable")

    db.session.commit()
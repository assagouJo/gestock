from app import app, db
from models import Compagnie

with app.app_context():
    fuji = Compagnie.query.filter_by(nom="Fuji").first()
    if not fuji:
        fuji = Compagnie(
            nom="Fuji",
            telephone="0707750718",
            email="",
            adresse="26 BP 1099 ABIDJAN 26",
            ville="Abidjan",
            numero_rcc=""
        )
        db.session.add(fuji)
        print("Fuji créée")
    else:
        print("Fuji existe déjà")

    imedical = Compagnie.query.filter_by(nom="iMedical").first()
    if not imedical:
        imedical = Compagnie(
            nom="iMedical",
            telephone="2721593882",
            email="info@imboe.com",
            adresse="MARCORY BOULEVARD VGE",
            ville="Abidjan",
            numero_rcc=""
        )
        db.session.add(imedical)
        print("iMedical créée")
    else:
        print("iMedical existe déjà")

    db.session.commit()
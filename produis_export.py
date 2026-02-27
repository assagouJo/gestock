import pandas as pd
from app import app, db
from models import Produit

# Lire le fichier Excel
df = pd.read_excel("produits.xlsx")

with app.app_context():
    for _, row in df.iterrows():
        produit = Produit(
            nom_produit=row["nom_produit"],
            description=row["description"]
        )
        db.session.add(produit)

    db.session.commit()

print("Import terminé ✅")
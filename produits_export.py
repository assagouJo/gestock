import pandas as pd
from app import app, db
from models import Produit

# Lire le fichier Excel
df = pd.read_excel("produits.xlsx")

with app.app_context():

    for _, row in df.iterrows():

        # vérifier si le produit existe déjà (par code produit ou nom)
        produit = Produit.query.filter_by(nom_produit=row["nom_produit"]).first()

        if produit:
            # mettre à jour les informations
            produit.description = row["description"]
            produit.marque = row["marque"]
            produit.model = row["model"]
            produit.origine = row["origine"]

        else:
            # créer nouveau produit
            produit = Produit(
                nom_produit=row["nom_produit"],
                description=row["description"],
                marque=row["marque"],
                model=row["model"],
                origine=row["origine"],
            )
            db.session.add(produit)

    db.session.commit()

print("Import / mise à jour terminé ✅")
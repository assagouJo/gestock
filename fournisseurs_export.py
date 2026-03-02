import pandas as pd
from app import app, db
from models import Fournisseur

# Lire le fichier Excel
df = pd.read_excel("fournisseurs.xlsx")

with app.app_context():
    for _, row in df.iterrows():
        fournisseur = Fournisseur(
            nom_fournisseur=row["nom_fournisseur"],
            ville=row["ville"]
        )
        db.session.add(fournisseur)

    db.session.commit()

print("Import terminé ✅")
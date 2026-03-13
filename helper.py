import uuid
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
import os


def generate_numero_facture(id):
        annee = datetime.now().year
        return f"{uuid.uuid4().hex[:8].upper()}-{annee}-{id:03d}"


def generate_code_bon_livraison(commande, produits_ids, quantites):

    from models import BonLivraison

    base = commande.numero.replace("BC", "BL")

    count = BonLivraison.query.filter_by(
        commande_id=commande.id
    ).count()

    # Quantité commandée
    quantite_commande = {
        ligne.produit_id: ligne.quantite
        for ligne in commande.lignes
    }

    # Quantité déjà livrée
    quantite_livree = {}

    for bl in commande.livraisons:
        for ligne in bl.lignes:

            quantite_livree[ligne.produit_id] = \
                quantite_livree.get(ligne.produit_id, 0) + ligne.quantite

    # Quantité que l'on livre maintenant
    quantite_nouvelle = {}

    for pid, qte in zip(produits_ids, quantites):

        pid = int(pid)
        qte = int(qte or 0)

        quantite_nouvelle[pid] = qte

    # Vérifier livraison complète
    livraison_complete = True

    for pid, qte in quantite_commande.items():

        total = quantite_livree.get(pid, 0) + quantite_nouvelle.get(pid, 0)

        if total < qte:
            livraison_complete = False
            break

    if livraison_complete and count == 0:
        return base

    return f"{base}-{count+1}"



def generate_code_produit():
        annee = datetime.now().year
        return f"{uuid.uuid4().hex[:6].upper()}-{annee}"


def generate_code_proforma(id):
    annee = datetime.now().year
    return f"PF-{annee}-{20000000+id}"


def generate_code_bon_commande(id):
    annee = datetime.now().year
    return f"BC-{annee}-{40000000+id}"


def generer_code_barre(code_produit):
    EAN = barcode.get_barcode_class('code128')
    code = EAN(code_produit, writer=ImageWriter())

    chemin = os.path.join(
        'static/barcodes',
        code_produit
    )

    code.save(chemin)
    return f"barcodes/{code_produit}.png"


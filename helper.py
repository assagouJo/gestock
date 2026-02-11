import uuid
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
import os


def generate_numero_facture(id):
        annee = datetime.now().year
        return f"{uuid.uuid4().hex[:8].upper()}-{annee}-{id:03d}"


def generate_code_produit():
        annee = datetime.now().year
        return f"{uuid.uuid4().hex[:6].upper()}-{annee}"


def generer_code_barre(code_produit):
    EAN = barcode.get_barcode_class('code128')
    code = EAN(code_produit, writer=ImageWriter())

    chemin = os.path.join(
        'static/barcodes',
        code_produit
    )

    code.save(chemin)
    return f"barcodes/{code_produit}.png"


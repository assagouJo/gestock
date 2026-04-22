from app import db, app
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from decimal import Decimal
import enum
from sqlalchemy import event
from helper import generate_code_produit, generate_code_proforma
from sqlalchemy import Enum, func
import random
import string


class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(64), index=True, nullable=False)
  email = db.Column(db.String(120), unique=True, nullable=False)
  password_hash = db.Column(db.String(256))
  role = db.Column(db.String(20), nullable=False, default='operateur')
  joined_at = db.Column(db.DateTime(), default = datetime.utcnow, index = True)
  must_change_password = db.Column(db.Boolean, default=False)

  __table_args__ = (
      db.UniqueConstraint('email', name='uq_user_email'),
  )

  def __repr__(self):
    return '<User {}>'.format(self.username)

  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)
  

class Client(db.Model):
    __tablename__ = "client"

    id = db.Column(db.Integer, primary_key=True)
    nom_client = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(30))
    adresse = db.Column(db.String(255), nullable=False)
    attn = db.Column(db.String(255))

    bons_commande = db.relationship(
        "BonCommande",
        back_populates="client",
        cascade="all, delete-orphan"
    )

    bons_livraison = db.relationship(
        "BonLivraison",
        back_populates="client"
    )

    def __repr__(self):
        return f"<Client {self.nom_client}>"
    

class Fournisseur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_fournisseur = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(30))
    adresse = db.Column(db.String(255))

    # 🔥 NOUVELLE RELATION
    achats = db.relationship(
        "Achat",
        back_populates="fournisseur",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Founisseur {self.nom_fournisseur}>"
    

class Produit(db.Model):
    __tablename__ = "produit"

    id = db.Column(db.Integer, primary_key=True)

    nom_produit = db.Column(db.String(128), nullable=False, index=True)
    model = db.Column(db.String(128), index=True)
    marque = db.Column(db.String(128), index=True)

    code_produit = db.Column(db.String(256), unique=True, nullable=False)

    description = db.Column(db.Text)
    origine = db.Column(db.String(256))

    image = db.Column(db.String(255))

    stocks = db.relationship("Stock", backref="produit", lazy=True)

    lignes_bon_commande = db.relationship(
        "LigneBonCommande",
        back_populates="produit"
    )

    lignes_bon_livraison = db.relationship(
        "LigneBonLivraison",
        back_populates="produit"
    )

    lignes_achat = db.relationship(
        "LigneAchat",
        back_populates="produit",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Produit {self.nom_produit}>"
  

@event.listens_for(Produit, "before_insert")
def generate_code_before_insert(mapper, connection, target):
    if not target.code_produit:
        target.code_produit = generate_code_produit()



class TypeConditionnement(enum.Enum):
    CARTON = "carton"
    PAQUET = "paquet"
    UNITE = "unite"


class Achat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_achat = db.Column(db.DateTime, default=datetime.utcnow)

    magasin_id = db.Column(db.Integer, db.ForeignKey("magasin.id"), nullable=False)

    taxe_douane = db.Column(db.Float, default=0)
    total_ht = db.Column(db.Float, default=0)
    total_ttc = db.Column(db.Float, default=0)

    magasin = db.relationship("Magasin")

    fournisseur_id = db.Column(
        db.Integer,
        db.ForeignKey("fournisseur.id", name="fk_achat_fournisseur_id"),
        nullable=False
    )

    fournisseur = db.relationship("Fournisseur", back_populates="achats")

    lignes = db.relationship(
        "LigneAchat",
        back_populates="achat",
        cascade="all, delete-orphan"
    )

    def calculer_totaux(self):
        self.total_ht = sum(l.total_ligne for l in self.lignes)
        self.total_ttc = self.total_ht + self.taxe_douane


class LigneAchat(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    achat_id = db.Column(db.Integer, db.ForeignKey("achat.id"), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey("produit.id"), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id", name="fk_ligne_achat_stock_id"), nullable=True)

    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)
    total_ligne = db.Column(db.Float, nullable=False)

    type_conditionnement = db.Column(
        db.Enum(
            TypeConditionnement,
            values_callable=lambda x: [e.value for e in x],
            name="typeconditionnement"
        ),
        nullable=False
    )

    stock = db.relationship("Stock", backref="ligne_achat")
    achat = db.relationship("Achat", back_populates="lignes")
    produit = db.relationship("Produit", back_populates="lignes_achat")

    def calculer_total(self):
        self.total_ligne = self.quantite * self.prix_unitaire


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=False
    )

    lignes_achat = db.relationship("LigneAchat", back_populates="stock")
    numero_lot = db.Column(db.String(100))
    quantite = db.Column(db.Integer, nullable=False, default=0)
    seuil_alerte = db.Column(db.Integer, default=5)
    date_creation = db.Column(db.DateTime(), default = datetime.utcnow, index = True)

    type_conditionnement = db.Column(
    db.Enum(
        TypeConditionnement,
        values_callable=lambda x: [e.value for e in x],
        name="typeconditionnement"
    ),
    nullable=False  # a remplacer par False apres render ok
    )

    magasin_id = db.Column(db.Integer, db.ForeignKey("magasin.id"), nullable=False)

    @staticmethod
    def generer_numero_lot():
        """Génère un numéro de lot aléatoire à 5 chiffres"""
        while True:
            # Générer un nombre aléatoire à 5 chiffres (10000 à 99999)
            numero = str(random.randint(10000, 99999))
            
            # Vérifier que le numéro n'existe pas déjà
            existant = Stock.query.filter_by(numero_lot=numero).first()
            if not existant:
                return numero
    
    def __init__(self, **kwargs):
        # Si numero_lot n'est pas fourni, en générer un automatiquement
        if 'numero_lot' not in kwargs or not kwargs['numero_lot']:
            kwargs['numero_lot'] = self.generer_numero_lot()
        super().__init__(**kwargs)


    def ajouter(self, quantite):
        if quantite <= 0:
            raise ValueError("Quantité invalide")
        self.quantite += quantite

    def retirer(self, quantite):
        if quantite <= 0:
            raise ValueError("Quantité invalide")
        if quantite > self.quantite:
            raise ValueError("Stock insuffisant")
        self.quantite -= quantite

    def est_en_alerte(self):
        return self.quantite <= self.seuil_alerte

    def __repr__(self):
        return f"<Stock produit_id={self.produit_id} ({self.quantite})>"
    
    __table_args__ = (
    db.UniqueConstraint("produit_id", "magasin_id", "type_conditionnement", name="uix_stock_unique"),
)
    

class Magasin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), unique=True, nullable=False)

    stocks = db.relationship("Stock", backref="magasin", lazy=True)

    # 🔥 NOUVELLE RELATION
    achats = db.relationship(
        "Achat",
        back_populates="magasin",
        cascade="all, delete-orphan"
    )



class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date_vente = db.Column(db.DateTime(), default = datetime.utcnow, index = True)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    # 🔽 AJOUTS PAIEMENT
    montant_paye = db.Column(db.Numeric(10, 2), default=0)
    reste_a_payer = db.Column(db.Numeric(10, 2), nullable=False)

    bon_livraison_id = db.Column(
        db.Integer,
        db.ForeignKey("bon_livraison.id", name='fk_vente_bon_livraison'),
        nullable=True, index=True
    )
    
    # Relation
    bon_livraison = db.relationship("BonLivraison", backref="vente", uselist=False)

    statut_paiement = db.Column(
        db.String(20),
        default="impaye"   # impaye | partiel | paye
    )

    vendeur_id = db.Column(
        db.Integer,
        db.ForeignKey("vendeur.id", name='fk_vente_vendeur'),
        nullable=False, # a remplacer par False apres render ok
        index=True
    )

    compagnie_id = db.Column(
        db.Integer,
        db.ForeignKey("vendeur_compagnie.id", name='fk_vente_compagnie'),
        nullable=False,
        index=True
    )

    facture = db.relationship(
    "Facture",
    back_populates="vente",
    uselist=False,
    cascade="all, delete-orphan"
    )


    client = db.relationship('Client', backref='ventes')

    lignes = db.relationship(
        'LigneVente',
        backref='vente',
        lazy=True,
        cascade="all, delete-orphan"
    )

    paiements = db.relationship(
        'Paiement',
        backref='vente',
        cascade="all, delete-orphan"
    )


class LigneVente(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    vente_id = db.Column(
        db.Integer,
        db.ForeignKey("vente.id", name="fk_ligne_vente_vente_id", ondelete="CASCADE" ),
        nullable=False
    )

    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stock.id", name="fk_ligne_vente_stock_id"),
        nullable=False
    )

    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)

    stock = db.relationship(
        "Stock",
        backref=db.backref("lignes", lazy=True)
    )

    def __repr__(self):
        return (
            f"<LigneVente vente={self.vente_id} "
            f"produit={self.stock.produit.nom_produit} "
            f"lot={self.stock.numero_lot} "
            f"qte={self.quantite}>"
        )
    
    @property
    def sous_total(self):
        return self.quantite * self.prix_unitaire  
    

class VendeurCompagnie(db.Model):
    __tablename__ = "vendeur_compagnie"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)

    ventes = db.relationship("Vente", backref="compagnie", lazy=True)

    def __repr__(self):
        return f"<Compagnie {self.nom}>"


class Vendeur(db.Model):
    __tablename__ = "vendeur"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    
    # AJOUT DE LA RELATION AVEC COMPAGNIE
    compagnie_id = db.Column(
        db.Integer,
        db.ForeignKey("vendeur_compagnie.id", name="fk_vendeur_compagnie_id"),
        nullable=False,
        default=1
    )
    
    ventes = db.relationship("Vente", backref="vendeur", lazy=True)
    
    # AJOUT DE LA RELATION AVEC COMPAGNIE
    compagnie = db.relationship("VendeurCompagnie", backref="vendeurs", lazy=True)

    def __repr__(self):
        return f"<Vendeur {self.nom}>"

      

class Paiement(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    vente_id = db.Column(
        db.Integer,
        db.ForeignKey("vente.id", ondelete="CASCADE"),
        nullable=False
    )

    montant = db.Column(db.Numeric(10, 2), nullable=False)

    mode = db.Column(
        db.String(20)
    )  # cash | mobile_money | carte | virement

    reference_paiement = db.Column(db.String(150), nullable=True) 

    annule = db.Column(db.Boolean, default=False)

    date_paiement = db.Column(db.DateTime(), default = datetime.utcnow)

    def est_reversible(self):
        return not self.annule


class Facture(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    vente_id = db.Column(
        db.Integer,
        db.ForeignKey("vente.id", name="fk_facture_vente", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    numero = db.Column(db.String(50), nullable=False, unique=True)

    date_facture = db.Column(
        db.DateTime(),
        default=lambda: datetime.utcnow,
        nullable=False
    )

    total = db.Column(db.Numeric(10, 2), nullable=False)
    montant_paye = db.Column(db.Numeric(10, 2), nullable=False)
    reste_a_payer = db.Column(db.Numeric(10, 2), nullable=False)

    statut = db.Column(db.String(20), nullable=False)

    vente = db.relationship(
        "Vente",
        back_populates="facture"
    )


class KitProforma(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client.id"),
        nullable=False
    )

    blocs = db.relationship(
    "BlocKit",
    backref="kit",
    cascade="all, delete-orphan"
    )

    date = db.Column(db.DateTime, default=datetime.utcnow)

    attn = db.Column(db.String(100))
    condition_paiement = db.Column(db.String(200))
    delai_livraison = db.Column(db.String(200))
    garantie = db.Column(db.String(200))

    prix_global = db.Column(db.Float)

    client = db.relationship("Client")

    lignes = db.relationship(
        "LigneKitProforma",
        backref="kit",
        cascade="all, delete-orphan"
    )


class BlocKit(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    kit_id = db.Column(
        db.Integer,
        db.ForeignKey("kit_proforma.id"),
        nullable=False
    )

    nom = db.Column(db.String(100))  # ex: "Échographe complet"

    lignes = db.relationship(
        "LigneKitProforma",
        backref="bloc",
        cascade="all, delete-orphan"
    )



class LigneKitProforma(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    kit_id = db.Column(db.Integer, db.ForeignKey("kit_proforma.id"), nullable=False)

    bloc_id = db.Column(
        db.Integer,
        db.ForeignKey("bloc_kit.id", name="fk_lkp_bloc_id"),
        nullable=True
    )

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=False
    )

    quantite = db.Column(db.Integer, nullable=False, default=1)
    produit = db.relationship("Produit")


class Proforma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proforma_title = db.Column(db.String(500))
    proforma_comment = db.Column(db.String(500))
    condition_paiement = db.Column(db.String(500))
    delai_livraison = db.Column(db.String(500))
    garantie = db.Column(db.String(500))
    attn = db.Column(db.String(400))
    numero = db.Column(db.String(50), unique=True, nullable=False)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client.id"),
        nullable=False
    )

    date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    total = db.Column(db.Float, default=0)

    client = db.relationship(
        "Client",
        backref=db.backref("proformas", lazy=True)
    )

    lignes = db.relationship(
        "LigneProforma",
        backref="proforma",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<Proforma {self.numero}>"


class LigneProforma(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    proforma_id = db.Column(
        db.Integer,
        db.ForeignKey("proforma.id"),
        nullable=False
    )

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=True
    )

    conditionnement = db.Column(db.String(50))
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)
    sous_total = db.Column(db.Float, nullable=False)
    produit = db.relationship("Produit")

    def __repr__(self):
        return f"<LigneProforma {self.produit.nom_produit}>"


class BonCommande(db.Model):
    __tablename__ = "bon_commande"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_commande = db.Column(db.DateTime, nullable=True)
    total = db.Column(db.Numeric(12,2), default=0)

    status = db.Column(
        Enum(
            "brouillon",
            "confirmee",
            "livraison_partielle",
            "livree",
            "facturee",
            "annulee",
            name="status_commande"
        ),
        default="brouillon",
        nullable=False
    )

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client.id", name="fk_bon_commande_client_id"),
        nullable=False
    )
    
    # AJOUT DES CHAMPS VENDEUR ET COMPAGNIE
    vendeur_id = db.Column(
        db.Integer,
        db.ForeignKey("vendeur.id", name="fk_bon_commande_vendeur_id"),
        nullable=False,
        default=1
    )
    
    compagnie_id = db.Column(
        db.Integer,
        db.ForeignKey("vendeur_compagnie.id", name="fk_bon_commande_compagnie_id"),
        nullable=False,
        default=1
    )

    client = db.relationship(
        "Client",
        back_populates="bons_commande"
    )
    
    # AJOUT DES RELATIONS
    vendeur = db.relationship(
        "Vendeur",
        backref="bons_commande",
        lazy=True
    )
    
    compagnie = db.relationship(
        "VendeurCompagnie",
        backref="bons_commande",
        lazy=True
    )

    lignes = db.relationship(
        "LigneBonCommande",
        back_populates="bon",
        cascade="all, delete-orphan"
    )

    livraisons = db.relationship(
        "BonLivraison",
        back_populates="commande"
    )

    @property
    def quantite_totale(self):
        """Quantité totale commandée"""
        if not self.lignes:
            return 0
        return sum(ligne.quantite for ligne in self.lignes)
    
    @property
    def quantite_totale_livree(self):
        """Quantité totale déjà livrée"""
        if not self.lignes:
            return 0
        return sum(ligne.quantite_livree for ligne in self.lignes)
    
    @property
    def pourcentage_livre(self):
        """Pourcentage de livraison"""
        if self.quantite_totale == 0:
            return 0
        return (self.quantite_totale_livree / self.quantite_totale) * 100


class LigneBonCommande(db.Model):
    __tablename__ = "ligne_bon_commande"

    id = db.Column(db.Integer, primary_key=True)

    bon_id = db.Column(
        db.Integer,
        db.ForeignKey("bon_commande.id"),
        nullable=False
    )

    compagnie_id = db.Column(
        db.Integer,
        db.ForeignKey("vendeur_compagnie.id", name="fk_ligne_bon_commande_compagnie_id"),  # Nom explicite
        nullable=False
    )

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=False
    )

    type_conditionnement = db.Column(
        db.Enum(
            TypeConditionnement,
            values_callable=lambda x: [e.value for e in x],
            name="typeconditionnement"
        ),
        nullable=False
    )

    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Numeric(10,2), nullable=False)
    sous_total = db.Column(db.Numeric(12,2), nullable=False)

    # relation avec les livraisons
    livraisons = db.relationship(
        "LigneBonLivraison",
        back_populates="ligne_commande",
        cascade="all, delete-orphan"
    )

    @property
    def quantite_livree(self):
        return sum(l.quantite for l in self.livraisons)

    @property
    def reste_a_livrer(self):
        return self.quantite - self.quantite_livree

    bon = db.relationship(
        "BonCommande",
        back_populates="lignes"
    )

    produit = db.relationship(
        "Produit",
        back_populates="lignes_bon_commande"
    )



# bon de livraison

class BonLivraison(db.Model):
    __tablename__ = "bon_livraison"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    nota_bene = db.Column(db.Text)

    status = db.Column(
        Enum(
            "brouillon",
            "confirmee",
            "partielle",
            "livree",
            name="status_livraison"
        ),
        default="brouillon",
        nullable=False
    )

    # client
    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client.id"),
        nullable=False
    )

    client = db.relationship(
        "Client",
        back_populates="bons_livraison"
    )

    # lien avec bon de commande
    commande_id = db.Column(
        db.Integer,
        db.ForeignKey("bon_commande.id")
    )

    commande = db.relationship(
        "BonCommande",
        back_populates="livraisons"
    )

    # parent pour livraison partielle
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("bon_livraison.id")
    )

    lignes = db.relationship(
        "LigneBonLivraison",
        back_populates="bon",
        cascade="all, delete-orphan"
    )
    

# Ajouter dans LigneBonLivraison
class LigneBonLivraison(db.Model):
    __tablename__ = "ligne_bon_livraison"

    id = db.Column(db.Integer, primary_key=True)

    bon_id = db.Column(
        db.Integer,
        db.ForeignKey("bon_livraison.id"),
        nullable=False
    )

    # lien vers la ligne de commande
    ligne_commande_id = db.Column(
        db.Integer,
        db.ForeignKey("ligne_bon_commande.id"),
        nullable=False
    )

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=False
    )

    quantite = db.Column(db.Integer, nullable=False)

    numero_serie = db.Column(db.String(120))
    
    # 🔥 NOUVEAU : Lien vers le stock (lot) utilisé
    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stock.id", name='fk_ligne_bon_livraison_stock'),
        nullable=True  # Peut être null si pas de gestion de lot
    )

    bon = db.relationship(
        "BonLivraison",
        back_populates="lignes"
    )

    produit = db.relationship(
        "Produit",
        back_populates="lignes_bon_livraison"
    )

    ligne_commande = db.relationship(
        "LigneBonCommande",
        back_populates="livraisons"
    )
    
    # 🔥 NOUVEAU : Relation avec le stock
    stock = db.relationship(
        "Stock",
        backref="lignes_bon_livraison"
    )

# bon de livraison


# models.py - Ajoutez ces classes à vos modèles existants

class CertificatReparation(db.Model):
    """Modèle pour le certificat de réparation"""
    __tablename__ = "certificat_reparation"
    
    id = db.Column(db.Integer, primary_key=True)
    numero_certificat = db.Column(db.String(50), unique=True, nullable=False, index=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_reparation = db.Column(db.Date, nullable=False)
    observations = db.Column(db.Text)
    technicien = db.Column(db.String(100))
    
    # Clés étrangères
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # Relations
    client = db.relationship('Client', backref='certificats_reparation')
    reparations = db.relationship('ReparationDetail', back_populates='certificat', 
                                  cascade='all, delete-orphan', lazy='joined')


class ReparationDetail(db.Model):
    """Modèle pour les détails des réparations (liaison produit-certificat)"""
    __tablename__ = "reparation_detail"
    
    id = db.Column(db.Integer, primary_key=True)
    taches_effectuees = db.Column(db.Text, nullable=False)
    cout_reparation = db.Column(db.Float, default=0.0)
    garantie_mois = db.Column(db.Integer, default=3)
    numero_serie = db.Column(db.String(100), nullable=False)
    
    # Clés étrangères
    certificat_id = db.Column(db.Integer, db.ForeignKey('certificat_reparation.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    
    # Relations
    certificat = db.relationship('CertificatReparation', back_populates='reparations')
    produit = db.relationship('Produit', backref='reparations')
    
    def __repr__(self):
        return f"<ReparationDetail {self.produit.nom_produit}>"


class Compagnie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    telephone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    adresse = db.Column(db.String(255))
    ville = db.Column(db.String(100))
    numero_rcc = db.Column(db.String(50))
    logo = db.Column(db.String(255)) 



class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    username = db.Column(db.String(100))
    action = db.Column(db.String(20))
    table_name = db.Column(db.String(100))
    record_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



# with app.app_context():
#     db.create_all()
#     Transaction.query.filter(
#     ~Transaction.details.any()
#     ).delete(synchronize_session=False)

#     db.session.commit()

#     exit()  

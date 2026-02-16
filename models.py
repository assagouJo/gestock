from app import db, app
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from decimal import Decimal
import enum


class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(64), index=True, nullable=False)
  email = db.Column(db.String(120), unique=True, nullable=False)
  password_hash = db.Column(db.String(256))
  role = db.Column(db.String(20), nullable=False, default='operateur')
  joined_at = db.Column(db.DateTime(), default = datetime.now(timezone.utc), index = True)
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
    id = db.Column(db.Integer, primary_key=True)
    nom_client = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(30))
    adresse_email = db.Column(db.String(255))
    ville = db.Column(db.String(100))
    numero_rcc = db.Column(db.String(50))

    def __repr__(self):
        return f"<Client {self.name}>"
    

class Produit(db.Model):
  
  id = db.Column(db.Integer, primary_key=True)
  nom_produit = db.Column(db.String(128), nullable=False,index=True)
  code_produit = db.Column(db.String(256), nullable=False, unique=True)
  description = db.Column(db.String(256), nullable=False)
  image = db.Column(db.String(255), nullable=True)
  stocks = db.relationship("Stock", backref="produit", lazy=True)

  def __repr__(self):
      return f"<Produit {self.nom_produit}>"
  
  @property
  def stock_total(self):
      return sum(s.quantite for s in self.stocks)

class TypeConditionnement(enum.Enum):
    CARTON = "carton"
    PAQUET = "paquet"
    UNITE = "unite"


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=False
    )
    
    numero_lot = db.Column(db.String(120), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=0)
    seuil_alerte = db.Column(db.Integer, default=5)
    date_creation = db.Column(db.DateTime(), default = datetime.now(timezone.utc), index = True)

    type_conditionnement = db.Column(
    db.Enum(
        TypeConditionnement,
        values_callable=lambda x: [e.value for e in x],
        name="typeconditionnement"
    ),
    nullable=False  # a remplacer par False apres render ok
    )

    magasin_id = db.Column(db.Integer, db.ForeignKey("magasin.id"), nullable=False)


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
        return f"<Stock produit_id={self.produit_id} lot={self.numero_lot} ({self.quantite})>"
    
    __table_args__ = (
    db.UniqueConstraint("produit_id", "numero_lot", "magasin_id", "type_conditionnement", name="uix_produit_lot_magasin_conditionnement"),
)
    

class Magasin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), unique=True, nullable=False)
    stocks = db.relationship("Stock", backref="magasin", lazy=True)



class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date_vente = db.Column(db.DateTime(), default = datetime.now(timezone.utc), index = True)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    # 🔽 AJOUTS PAIEMENT
    montant_paye = db.Column(db.Numeric(10, 2), default=0)
    reste_a_payer = db.Column(db.Numeric(10, 2), nullable=False)

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
    ventes = db.relationship("Vente", backref="vendeur", lazy=True)

    def __repr__(self):
        return f"<Vendeur {self.nom}>"




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

    date_paiement = db.Column(db.DateTime(), default = datetime.now(timezone.utc))

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
        default=lambda: datetime.now(timezone.utc),
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


class Proforma(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    numero = db.Column(db.String(50), unique=True, nullable=False)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("client.id"),
        nullable=False
    )

    date = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    total = db.Column(db.Float, default=0)

    statut = db.Column(
        db.String(20),
        default="PROFORMA"
    )

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
        nullable=False
    )

    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)
    sous_total = db.Column(db.Float, nullable=False)

    produit = db.relationship("Produit")

    def __repr__(self):
        return f"<LigneProforma {self.produit.nom_produit}>"



class Compagnie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    telephone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    adresse = db.Column(db.String(255))
    ville = db.Column(db.String(100))
    numero_rcc = db.Column(db.String(50))
    logo = db.Column(db.String(255)) 




with app.app_context():
    db.create_all()
    # Transaction.query.filter(
    # ~Transaction.details.any()
    # ).delete(synchronize_session=False)

    # db.session.commit()

    # exit()  

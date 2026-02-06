from app import db, app
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from decimal import Decimal


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
  stock = db.Column(db.Integer, default=0)


  def __repr__(self):
      return f"<Produit {self.nom_produit}>"


class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date_vente = db.Column(db.DateTime(), default = datetime.now(timezone.utc), index = True)
    total = db.Column(db.Numeric(10, 2), default=0)

    client = db.relationship('Client', backref='ventes')
    lignes = db.relationship('LigneVente', backref='vente', lazy=True)


class LigneVente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vente_id = db.Column(db.Integer, db.ForeignKey('vente.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)
    sous_total = db.Column(db.Numeric(10, 2), nullable=False)

    produit = db.relationship('Produit')



class Paiement(db.Model):
    __tablename__ = "paiement"

    id = db.Column(db.Integer, primary_key=True)

    facture_id = db.Column(
        db.Integer,
        db.ForeignKey("facture.id"),
        nullable=False
    )


    montant = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    mode_paiement = db.Column(db.String(30))



class Facture(db.Model):
    __tablename__ = "facture"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    type_facture = db.Column(db.String(15), nullable=False)

    vente_id = db.Column(db.Integer, db.ForeignKey("vente.id"), nullable=False)
    vente = db.relationship("Vente", backref=db.backref("facture", uselist=False))

    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=True)
    client = db.relationship("Client")

    total = db.Column(db.Numeric(10, 2), default=0)
    total_paye = db.Column(db.Numeric(10, 2), default=0)
    statut = db.Column(db.String(20), default="BROUILLON")

    # ✅ RELATION MANQUANTE
    lignes = db.relationship(
        "LigneFacture",
        back_populates="facture",
        cascade="all, delete-orphan"
    )






class LigneFacture(db.Model):
    __tablename__ = "ligne_facture"

    id = db.Column(db.Integer, primary_key=True)

    facture_id = db.Column(
        db.Integer,
        db.ForeignKey("facture.id"),
        nullable=False
    )

    facture = db.relationship(
        "Facture",
        back_populates="lignes"
    )

    produit_id = db.Column(
        db.Integer,
        db.ForeignKey("produit.id"),
        nullable=False
    )
    produit = db.relationship("Produit")

    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)

    @property
    def sous_total(self):
        return self.quantite * self.prix_unitaire





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

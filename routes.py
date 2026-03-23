from app import app, db, login_manager
from datetime import datetime, timezone
from flask import request, render_template, flash, redirect, url_for, get_flashed_messages, abort, make_response, current_app, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Client, Produit, Compagnie, Vente, LigneVente, Log, Stock, Paiement, Facture, Proforma, LigneProforma, Magasin, Vendeur, VendeurCompagnie, TypeConditionnement, BonCommande, LigneBonCommande, Achat, LigneAchat, Fournisseur, BonLivraison, LigneBonLivraison, KitProforma,LigneKitProforma, BlocKit, CertificatReparation, ReparationDetail
from forms import LoginForm, ClientForm, MagasinForm, LogFilterForm, ProduitForm, UserForm, ChangePasswordForm, CompagnieForm, ProformaForm, FournisseurForm, CertificatReparationForm, ReparationDetailForm, RechercheProduitForm
from functools import wraps
from werkzeug.utils import secure_filename
import os
from werkzeug.utils import secure_filename
import uuid
from cloudinary.uploader import upload
from decimal import Decimal
from sqlalchemy import func, exists
from sqlalchemy.exc import SQLAlchemyError
from helper import generate_code_proforma, generate_numero_facture, generate_code_produit, generate_code_bon_commande, generate_code_bon_livraison
from werkzeug.security import generate_password_hash
import cloudinary.uploader
from cloudinary.uploader import upload
from weasyprint import HTML
from sqlalchemy.orm import joinedload
import pandas as pd
from flask import send_file
import io
from num2words import num2words
import time



def generer_numero_certificat():
    """Génère un numéro de certificat automatique format: CERT-YYYY-XXXX"""
    annee = datetime.now().year
    # Compter le nombre de certificats créés cette année
    count = CertificatReparation.query.filter(
        CertificatReparation.date_creation >= datetime(annee, 1, 1),
        CertificatReparation.date_creation <= datetime(annee, 12, 31)
    ).count()
    
    # Numéro séquentiel avec 4 chiffres
    numero = f"CERT-{annee}-{count + 1:04d}"
    return numero


def seed_compagnies():

    compagnies = ["Fuji", "I-Medical"]

    for nom in compagnies:

        existe = VendeurCompagnie.query.filter_by(nom=nom).first()

        if not existe:
            nouvelle = VendeurCompagnie(nom=nom)
            db.session.add(nouvelle)

    db.session.commit()

@app.template_filter('money')
def montant_format(valeur):
    return f"{valeur:,.0f}".replace(",", " ").replace(".", ",")


@app.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def utility_processor():
    def is_active(prefix):
        return request.endpoint and prefix in request.endpoint
    return dict(is_active=is_active)


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Veuillez vous connecter.", "warning")
                return redirect(url_for("login"))
            if current_user.role not in roles:
                flash("Vous n'avez pas la permission d'effectuer cette action.","danger")
                return redirect(request.referrer)
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role in ["admin","superadmin"]:
            return redirect(url_for("dashboard"))
        elif current_user.role == "finance":
            return redirect(url_for("nouvelle_vente"))
        else:
            return redirect(url_for("nouveau_achat"))        

    form = LoginForm(csrf_enabled=False)

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)

            if user.must_change_password:
                return redirect(url_for('force_change_password'))

            # 🔥 REDIRECTION SELON LE RÔLE
            if user.role in ["admin","superadmin"]:
                return redirect(url_for("dashboard"))
            elif current_user.role == "finance":
                return redirect(url_for("nouvelle_vente"))
            else:
                return redirect(url_for("nouveau_achat")) 

        flash("Identifiants incorrects", "danger")

    return render_template('login.html', form=form)



@app.route('/force-change-password', methods=['GET', 'POST'])
@login_required
def force_change_password():

    # Sécurité : si déjà changé
    if not current_user.must_change_password:
        return redirect(url_for('dashboard'))

    form = ChangePasswordForm()

    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        current_user.must_change_password = False
        db.session.commit()

        flash("Mot de passe modifié avec succès", "success")
        return redirect(url_for('dashboard'))
    
    print(form.errors)

    return render_template('force_change_password.html', form=form)



@app.route('/gestion_materiel/user/reset-password', methods=['POST'])
@login_required
def reset_user_password():

    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(request.referrer)

    user_id = request.form.get('user_id')
    user = User.query.get_or_404(user_id)

    default_password = "123456"  
    user.set_password(default_password)
    user.must_change_password = True

    db.session.commit()

    flash("Mot de passe réinitialisé avec succès", "success")

    return redirect(request.referrer)



@app.route('/gestion_materiel/user', methods=['GET', 'POST'])
@login_required
def creer_user():    
    form = UserForm()
    user = User.query.order_by(User.username).all()
    if form.validate_on_submit():
        user = User(
            username = form.username.data,
            email = form.email.data,
            role = form.role.data
        )

        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash('Utilisateur cree avec succes', 'success')
        return redirect(url_for('creer_user'))
    
    return render_template('user.html', form=form, user=user)



@app.route('/gestion_materiel/user/edit/<int:id>', methods=['POST'])
@login_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm()

    
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()
        flash("Utilisateur modifié avec succès", "success")

    return redirect(url_for('user'))



@app.route('/gestion_materiel/user/delete', methods=['POST'])
@login_required
def delete_users():
    ids = request.form.getlist('user_ids')

    if not ids:
        flash("Aucun produit sélectionné", "warning")
        return redirect(url_for('user'))

    User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    flash(f"{len(ids)} utilisateur(s) supprimé(s)", "success")
    return redirect(url_for('user'))



@app.route("/dashboard")
@login_required
def dashboard():

    from collections import defaultdict
    from calendar import month_name

    ventes = Vente.query.all()
    achats = Achat.query.all()
    vendeurs = Vendeur.query.all()
    clients = Client.query.all()

    # =========================
    # 🔹 VENTES & ACHATS PAR MOIS
    # =========================
    ventes_mois = defaultdict(float)
    achats_mois = defaultdict(float)

    for v in ventes:
        if v.date_vente:
            mois = month_name[v.date_vente.month]
            ventes_mois[mois] += float(v.total or 0)

    for a in achats:
        if a.date_achat:
            mois = month_name[a.date_achat.month]
            achats_mois[mois] += float(a.total_ttc or 0)

    # 🔥 Fusion des mois pour éviter pertes
    mois_uniques = sorted(
        set(list(ventes_mois.keys()) + list(achats_mois.keys()))
    )

    labels = mois_uniques
    ventes_data = [ventes_mois[m] for m in labels]
    achats_data = [achats_mois[m] for m in labels]

    # =========================
    # 🔹 DETTES CLIENTS
    # =========================
    clients_labels = []
    dettes_data = []

    for client in clients:
        total_reste = sum(v.reste_a_payer or 0 for v in client.ventes)
        clients_labels.append(client.nom_client)
        dettes_data.append(float(total_reste))

    # =========================
    # 🔹 VENTES PAR VENDEUR
    # =========================
    vendeur_labels = []
    vendeur_data = []

    for vendeur in vendeurs:
        total_vendeur = sum(v.total or 0 for v in vendeur.ventes)
        vendeur_labels.append(vendeur.nom)
        vendeur_data.append(float(total_vendeur))

    return render_template(
        "dashboard.html",
        labels=labels,
        ventes_data=ventes_data,
        achats_data=achats_data,
        clients_labels=clients_labels,
        dettes_data=dettes_data,
        vendeur_labels=vendeur_labels,
        vendeur_data=vendeur_data
    )


@app.route('/gestion_materiel/produit', methods=['GET', 'POST'])
@login_required
def produit():
    form = ProduitForm()
    produits = Produit.query.order_by(Produit.nom_produit).all()
    
    if form.validate_on_submit():
        try:
            # ✅ Vérifier si le produit existe déjà
            exist_produit = Produit.query.filter(
                Produit.nom_produit == form.nom_produit.data,
                Produit.marque == form.marque.data,
                Produit.model == form.model.data
            ).first()

            if exist_produit:
                flash(f"Ce produit existe déjà avec le code {exist_produit.code_produit}", "danger")
                return redirect(url_for("produit"))

            # ✅ Gestion de l'image
            image_url = None
            file = form.image.data
            
            if file and file.filename:
                try:
                    # Upload vers Cloudinary
                    result = upload(
                        file,
                        folder="gestock/produits",
                        resource_type="auto"
                    )
                    image_url = result["secure_url"]
                except Exception as e:
                    flash(f"Erreur lors de l'upload de l'image: {str(e)}", "warning")
                    # Continuer sans image

            # ✅ Création du produit
            nouveau_produit = Produit(
                nom_produit=form.nom_produit.data.strip(),
                marque=form.marque.data.strip() if form.marque.data else None,
                model=form.model.data.strip() if form.model.data else None,
                origine=form.origine.data.strip() if form.origine.data else None,
                description=form.description.data.strip() if form.description.data else None,
                code_produit=generate_code_produit(),
                image=image_url
            )
            
            db.session.add(nouveau_produit)
            db.session.commit()

            flash(f"✅ Produit {nouveau_produit.nom_produit} ajouté avec succès", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur: {str(e)}", "danger")
        
        return redirect(url_for("produit"))
    
    return render_template('produit.html', form=form, produits=produits)
    


@app.route('/gestion_materiel/produit/edit/<int:id>', methods=['POST'])
@login_required
def edit_produit(id):
    produit = Produit.query.get_or_404(id)
    
    try:
        # Récupération et nettoyage des données
        nom_produit = request.form.get('nom_produit', '').strip()
        description = request.form.get('description', '').strip()
        marque = request.form.get('marque', '').strip()
        model = request.form.get('model', '').strip()
        origine = request.form.get('origine', '').strip()
        
        # Validation
        if not nom_produit:
            flash("Le nom du produit est obligatoire", "danger")
            return redirect(url_for('produit'))
        
        # Vérifier si un autre produit avec le même nom existe (sauf celui-ci)
        existing = Produit.query.filter(
            Produit.nom_produit == nom_produit,
            Produit.id != id
        ).first()
        
        if existing:
            flash(f"Un produit avec le nom '{nom_produit}' existe déjà", "danger")
            return redirect(url_for('produit'))
        
        # Mise à jour
        produit.nom_produit = nom_produit
        produit.description = description if description else None
        produit.marque = marque if marque else None
        produit.model = model if model else None
        produit.origine = origine if origine else None
        
        # Gestion de l'image
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Vérifier le type de fichier
                allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                
                if ext in allowed:
                    # Supprimer l'ancienne image
                    if produit.image:
                        try:
                            delete_cloudinary_image(produit.image)
                        except Exception as e:
                            print(f"Erreur suppression: {e}")
                    
                    # Upload nouvelle image
                    result = upload(
                        file,
                        folder="gestock/produits",
                        public_id=f"produit_{id}_{int(time.time())}"
                    )
                    produit.image = result["secure_url"]
                    flash("Image mise à jour", "success")
                else:
                    flash("Format d'image non supporté", "warning")
        
        db.session.commit()
        flash(f"✅ Produit '{produit.nom_produit}' modifié avec succès", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur: {str(e)}", "danger")
        print(f"Erreur edit_produit: {e}")
    
    return redirect(url_for('produit'))


def delete_cloudinary_image(image_url):
    if not image_url:
        return

    try:
        # https://res.cloudinary.com/.../upload/v123/gestock/produits/xxx.jpg
        public_id = image_url.split("/upload/")[1].rsplit(".", 1)[0]
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print("Cloudinary delete error:", e)




@app.route('/gestion_materiel/produit/delete', methods=['POST'])
@login_required
def delete_produits():

    ids = request.form.getlist('produit_ids')

    if not ids:
        flash("Aucun produit sélectionné", "warning")
        return redirect(url_for('produit'))

    produits = Produit.query.filter(Produit.id.in_(ids)).all()

    produits_bloques = []
    produits_supprimes = 0

    for p in produits:

        # 🔒 2️⃣ Produit déjà vendu (via Stock → LigneVente)
        vente_existante = (
            LigneVente.query
            .join(Stock)
            .filter(Stock.produit_id == p.id)
            .first()
        )

        if vente_existante:
            produits_bloques.append(f"{p.nom_produit} (déjà vendu)")
            continue

        # ✅ Suppression autorisée
        if p.image:
            delete_cloudinary_image(p.image)

        db.session.delete(p)
        produits_supprimes += 1

    db.session.commit()

    # ⛔ Message blocage
    if produits_bloques:
        flash(
            "Impossible de supprimer : " + ", ".join(produits_bloques),
            "danger"
        )

    # ✅ Message succès
    if produits_supprimes:
        flash(
            f"{produits_supprimes} produit(s) supprimé(s) avec succès",
            "success"
        )

    return redirect(url_for('produit'))



@app.route('/gestion_materiel/client', methods=['GET', 'POST'])
@login_required
def client():
  form = ClientForm(csrf_enabled=False)
  clients = Client.query.order_by(Client.nom_client).all()
  
  if form.validate_on_submit():
     nouveau_client = Client(
      nom_client = form.nom_client.data,
      telephone = form.telephone.data,
      adresse = form.adresse.data,      
     )
     db.session.add(nouveau_client)
     db.session.commit()

     flash("Client ajouter avec succes", "success")
     return redirect(url_for("client"))
  return render_template('client.html', form=form, clients=clients)


@app.route('/gestion_materiel/client/edit/<int:id>', methods=['POST'])
@login_required
def edit_client(id):
    client = Client.query.get_or_404(id)
    form = ClientForm()

    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        flash("Client modifié avec succès", "success")

    return redirect(url_for('client'))



@app.route('/gestion_materiel/client/delete', methods=['POST'])
@login_required
def delete_clients():

    ids = request.form.getlist('client_ids')

    if not ids:
        flash("Aucun client sélectionné", "warning")
        return redirect(url_for('client'))

    clients = Client.query.filter(Client.id.in_(ids)).all()

    clients_bloques = []
    clients_supprimes = 0

    for c in clients:

        # 🔒 Vérifier s’il a des ventes
        if c.ventes:
            clients_bloques.append(c.nom_client)
            continue

        db.session.delete(c)
        clients_supprimes += 1

    db.session.commit()

    if clients_bloques:
        flash(
            "Impossible de supprimer (clients liés à des ventes) : " +
            ", ".join(clients_bloques),
            "danger"
        )

    if clients_supprimes:
        flash(f"{clients_supprimes} client(s) supprimé(s)", "success")

    return redirect(url_for('client'))

# fournisseur

@app.route('/gestion_materiel/fournisseur', methods=['GET', 'POST'])
@login_required
def fournisseur():
  form = FournisseurForm(csrf_enabled=False)
  fournisseurs = Fournisseur.query.order_by(Fournisseur.nom_fournisseur).all()
  
  if form.validate_on_submit():
     nouveau_fournisseur = Fournisseur(
      nom_fournisseur = form.nom_fournisseur.data,
      telephone = form.telephone.data,
      adresse = form.adresse.data, 
     )
     db.session.add(nouveau_fournisseur)
     db.session.commit()

     flash("Fournisseur ajouter avec succes", "success")
     return redirect(url_for("fournisseur"))
  return render_template('Fournisseur.html', form=form, fournisseurs=fournisseurs)


@app.route('/gestion_materiel/fournisseur/edit/<int:id>', methods=['POST'])
@login_required
def edit_fournisseur(id):
    fournisseur = Fournisseur.query.get_or_404(id)
    form = FournisseurForm()

    if form.validate_on_submit():
        form.populate_obj(fournisseur)
        db.session.commit()
        flash("Client modifié avec succès", "success")

    return redirect(url_for('fournisseur'))



@app.route('/gestion_materiel/fournisseur/delete', methods=['POST'])
@login_required
def delete_fournisseurs():

    ids = request.form.getlist('fournisseur_ids')

    if not ids:
        flash("Aucun fournisseur sélectionné", "warning")
        return redirect(url_for('fournisseur'))

    fournisseurs = Fournisseur.query.filter(Fournisseur.id.in_(ids)).all()

    fournisseurs_bloques = []
    fournisseurs_supprimes = 0

    for f in fournisseurs:

        # 🔒 Vérifier s’il a des ventes
        if f.achats:
            fournisseurs_bloques.append(f.nom_fournisseur)
            continue

        db.session.delete(f)
        fournisseurs_supprimes += 1

    db.session.commit()

    if fournisseurs_bloques:
        flash(
            "Impossible de supprimer (clients liés à des ventes) : " +
            ", ".join(fournisseurs_bloques),
            "danger"
        )

    if fournisseurs_supprimes:
        flash(f"{fournisseurs_supprimes} client(s) supprimé(s)", "success")

    return redirect(url_for('fournisseur'))


# fornisseur


@app.route("/stock", methods=["GET"])
@login_required
def etat_stock():
    produits_all = Produit.query.order_by(Produit.nom_produit).all()
    magasins = Magasin.query.order_by(Magasin.nom).all()

    stocks = (
        Stock.query
        .join(Produit)
        .filter(Stock.quantite > 0) 
        .all()
    )    

    return render_template(
        "ajout_stock.html",   # ta page unique
        stocks=stocks,
        produits_all=produits_all,
        magasins=magasins
    )


@app.route("/stock/edit/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def edit_stock(id):

    stock = Stock.query.get_or_404(id)

    try:
        # 📥 Récupération des données (une seule ligne en mode modification)
        produit_id = request.form.getlist("produit_id[]")[0]
        magasin_id = request.form.getlist("magasin_id[]")[0]
        quantite = request.form.getlist("quantite[]")[0]
        type_cond = request.form.getlist("type_conditionnement[]")[0]

        # 🔎 Vérification données obligatoires
        if not produit_id or not magasin_id or not quantite or not type_cond:
            flash("Données invalides ❌", "danger")
            return redirect(url_for("etat_stock"))

        # 🔢 Conversion types
        produit_id = int(produit_id)
        magasin_id = int(magasin_id)
        quantite = int(quantite)

        if quantite < 0:
            flash("Quantité invalide ❌", "danger")
            return redirect(url_for("etat_stock"))

        try:
            type_conditionnement = TypeConditionnement(type_cond)
        except ValueError:
            flash("Conditionnement invalide ❌", "danger")
            return redirect(url_for("etat_stock"))

        # 🛠 Mise à jour
        stock.produit_id = produit_id
        stock.magasin_id = magasin_id
        stock.quantite = quantite
        stock.type_conditionnement = type_conditionnement

        db.session.commit()

        flash("Stock modifié avec succès ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la modification ❌ : {str(e)}", "danger")

    return redirect(url_for("etat_stock"))



@app.route("/delete/lot", methods=["POST"])
@login_required
@role_required("admin")
def delete_lot():
    stock_ids = request.form.getlist("stock_ids[]")

    if not stock_ids:
        flash("Aucun produit sélectionné", "warning")
        return redirect(url_for("etat_stock"))

    stocks = Stock.query.filter(Stock.id.in_(stock_ids)).all()

    stocks_bloques = []

    for stock in stocks:
        if stock.lignes:   # 🔥 relation backref
            stocks_bloques.append(stock.numero_lot)
        else:
            db.session.delete(stock)

    if stocks_bloques:
        flash(
            f"Suppression partielle ❌ — Lots liés à des ventes : {', '.join(stocks_bloques)}",
            "danger"
        )
    else:
        flash("Stocks supprimés avec succès 🗑️", "success")

    db.session.commit()
    return redirect(url_for("etat_stock"))




@app.route("/stock/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_stock():

    if request.method == "GET":
        return redirect(url_for("etat_stock"))

    produits = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    magasins = request.form.getlist("magasin_id[]")
    nouveaux_magasins = request.form.getlist("nouveau_magasin[]")
    types = request.form.getlist("type_conditionnement[]")

    if not produits or not quantites:
        flash("Aucune donnée reçue ❌", "danger")
        return redirect(url_for("etat_stock"))

    try:
        for produit_id, quantite, magasin_id, nouveau_nom, type_cond in zip(
            produits, quantites, magasins, nouveaux_magasins, types
        ):

            if not produit_id or not quantite or not type_cond:
                continue

            try:
                produit_id = int(produit_id)
                quantite = int(quantite)
            except ValueError:
                continue

            if quantite <= 0:
                continue

            # 🎯 Gestion du magasin
            nouveau_nom = nouveau_nom.strip() if nouveau_nom else ""

            if nouveau_nom:
                magasin = Magasin.query.filter(
                    Magasin.nom.ilike(nouveau_nom)
                ).first()

                if not magasin:
                    magasin = Magasin(nom=nouveau_nom)
                    db.session.add(magasin)
                    db.session.flush()

                magasin_id = magasin.id
            else:
                try:
                    magasin_id = int(magasin_id)
                except (ValueError, TypeError):
                    continue

            # 🎯 Conversion string → Enum
            try:
                type_conditionnement = TypeConditionnement(type_cond)
            except ValueError:
                continue

            produit = Produit.query.get(produit_id)
            if not produit:
                continue

            numero_lot = produit.code_produit

            # 🔎 Vérifier si stock existe déjà
            stock_existant = Stock.query.filter_by(
                produit_id=produit_id,
                magasin_id=magasin_id,
                type_conditionnement=type_conditionnement
            ).first()

            if stock_existant:
                stock_existant.quantite += quantite
            else:
                nouveau_stock = Stock(
                    produit_id=produit_id,
                    numero_lot=numero_lot, 
                    quantite=quantite,
                    magasin_id=magasin_id,
                    type_conditionnement=type_conditionnement
                )
                db.session.add(nouveau_stock)

        db.session.commit()
        flash("Stock enregistré avec succès ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'enregistrement ❌ : {str(e)}", "danger")

    return redirect(url_for("etat_stock"))



@app.route('/vente/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_vente():

    seed_compagnies()
    # =========================
    # 🔹 DONNÉES POUR AFFICHAGE
    # =========================
    clients = Client.query.order_by(Client.nom_client).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()
    vendeurs = Vendeur.query.order_by(Vendeur.nom).all()
    compagnies = VendeurCompagnie.query.order_by(VendeurCompagnie.nom).all()

    stocks = (
        Stock.query
        .options(joinedload(Stock.produit))
        .order_by(Stock.id.desc())
        .all()
    )

    ventes = (
        Vente.query
        .options(
            joinedload(Vente.client),
            joinedload(Vente.vendeur),
            joinedload(Vente.compagnie),
            joinedload(Vente.lignes)
                .joinedload(LigneVente.stock)
                .joinedload(Stock.produit)
        )
        .order_by(Vente.id.desc())
        .all()
    )

    # =========================
    # 🔹 ENREGISTREMENT VENTE
    # =========================
    if request.method == 'POST':

        client_id = request.form.get('client_id')
        vendeur_id = request.form.get('vendeur_id')
        compagnie_id = request.form.get('compagnie_id')
        date_vente_str = request.form.get("date_vente")

        stock_ids = request.form.getlist('stock_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')

        # 🔎 Validation de base
        if not client_id or not vendeur_id or not compagnie_id or not stock_ids:
            flash("Données invalides", "danger")
            return redirect(url_for('nouvelle_vente'))

        try:

            vendeur = Vendeur.query.get(int(vendeur_id))
            compagnie = VendeurCompagnie.query.get(int(compagnie_id))

            if not vendeur:
                raise ValueError("Vendeur invalide")

            if not compagnie:
                raise ValueError("Compagnie invalide")

            # =========================
            # 🔹 1️⃣ CRÉATION VENTE
            # =========================
            vente = Vente(
                client_id=int(client_id),
                vendeur_id=vendeur.id,
                compagnie_id=compagnie.id,
                date_vente=datetime.fromisoformat(date_vente_str),
                total=Decimal("0.00"),
                montant_paye=Decimal("0.00"),
                reste_a_payer=Decimal("0.00"),
                statut_paiement="impaye"
            )

            db.session.add(vente)
            db.session.flush()  # 🔥 obtenir vente.id

            total_vente = Decimal("0.00")

            # =========================
            # 🔹 2️⃣ LIGNES DE VENTE
            # =========================
            for stock_id, qte, pu in zip(stock_ids, quantites, prix_unitaires):

                stock = (
                    db.session.query(Stock)
                    .filter_by(id=int(stock_id))
                    .with_for_update()
                    .first()
                )

                if not stock:
                    raise ValueError("Lot invalide")

                qte = int(qte)
                pu = Decimal(pu)

                if qte <= 0:
                    raise ValueError("Quantité invalide")

                if qte > stock.quantite:
                    raise ValueError(
                        f"Stock insuffisant pour le lot {stock.numero_lot}"
                    )

                # 🔹 Décrémentation stock
                stock.retirer(qte)

                sous_total = qte * pu
                total_vente += sous_total

                ligne = LigneVente(
                    vente_id=vente.id,
                    stock_id=stock.id,
                    quantite=qte,
                    prix_unitaire=pu
                )

                db.session.add(ligne)

            # =========================
            # 🔹 3️⃣ FINALISATION
            # =========================
            vente.total = total_vente
            vente.reste_a_payer = total_vente

            facture = Facture(
                vente_id=vente.id,
                numero="FAC-" + generate_numero_facture(vente.id),
                date_facture=datetime.now(timezone.utc),
                total=vente.total,
                montant_paye=vente.montant_paye,
                reste_a_payer=vente.reste_a_payer,
                statut=vente.statut_paiement
            )

            db.session.add(facture)

            db.session.commit()

            flash("Vente enregistrée avec succès ✅", "success")
            return redirect(url_for('nouvelle_vente'))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for('nouvelle_vente'))

    # =========================
    # 🔹 AFFICHAGE PAGE
    # =========================
    return render_template(
        'liste_vente.html',
        clients=clients,
        produits=produits,
        vendeurs=vendeurs,
        compagnies=compagnies,
        ventes=ventes,
        stocks=stocks,
        now=datetime.now()
    )


@app.route("/ventes/supprimer", methods=["POST"])
@login_required
def supprimer_ventes():

    vente_ids = request.form.getlist("vente_ids")

    if not vente_ids:
        flash("Aucune vente sélectionnée", "warning")
        return redirect(url_for("nouvelle_vente"))

    ventes_refusees = []
    ventes_supprimees = 0

    try:
        ventes = Vente.query.filter(Vente.id.in_(vente_ids)).all()

        for vente in ventes:

            # 🔒 INTERDICTION ABSOLUE
            if vente.montant_paye > 0 or vente.statut_paiement != "impaye":
                ventes_refusees.append(str(vente.id))
                continue

            # 🔁 Réintégrer le stock (vente jamais payée)
            for ligne in vente.lignes:
                if ligne.stock:
                    ligne.stock.ajouter(ligne.quantite)

            db.session.delete(vente)
            ventes_supprimees += 1

        db.session.commit()

        if ventes_refusees:
            flash(
                "Suppression refusée ❌ pour les ventes avec paiement : "
                + ", ".join(ventes_refusees),
                "danger"
            )

        if ventes_supprimees:
            flash(
                f"{ventes_supprimees} vente(s) supprimée(s) avec succès",
                "success"
            )

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("nouvelle_vente"))


@app.route("/vente/<int:vente_id>/edit", methods=["GET"])
@login_required
def modifier_vente(vente_id):
    vente = (
        Vente.query
        .options(
            db.joinedload(Vente.lignes)
              .joinedload(LigneVente.stock)
              .joinedload(Stock.produit),
            db.joinedload(Vente.client)
        )
        .get_or_404(vente_id)
    )

    if vente.montant_paye > 0:
        flash(
            "Cette vente a déjà reçu un paiement et ne peut plus être modifiée.",
            "danger"
        )
        return redirect(url_for("nouvelle_vente"))
    

    clients = Client.query.order_by(Client.nom_client).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()

    return render_template(
        "modifier_vente.html",
        vente=vente,
        clients=clients,
        produits=produits
    )


@app.route("/achat/nouveau", methods=["GET"])
def nouveau_achat():
    fournisseurs = Fournisseur.query.order_by(Fournisseur.nom_fournisseur).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()
    magasins = Magasin.query.order_by(Magasin.nom).all()

    achats = Achat.query.order_by(Achat.date_achat.desc()).all()

    return render_template(
        "achat_form.html",
        fournisseurs=fournisseurs,
        produits=produits,
        magasins=magasins,
        achats=achats,
        now=datetime.now()
    )


@app.route("/achat/nouveau", methods=["POST"])
def ajouter_achat():

    fournisseur_id = request.form.get("fournisseur_id")
    magasin_id = request.form.get("magasin_id")
    taxe_douane = float(request.form.get("taxe_douane") or 0)

    produits = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    prix = request.form.getlist("prix_unitaire[]")
    types = request.form.getlist("type_conditionnement[]")

    achat = Achat(
        fournisseur_id=fournisseur_id,
        magasin_id=magasin_id,
        taxe_douane=taxe_douane
    )

    db.session.add(achat)

    for produit_id, quantite, prix_unitaire, type_conditionnement in zip(
        produits, quantites, prix, types
    ):

        if not produit_id or not quantite:
            continue

        quantite = int(quantite)
        prix_unitaire = float(prix_unitaire)

        ligne = LigneAchat(
            achat=achat,
            produit_id=produit_id,
            quantite=quantite,
            prix_unitaire=prix_unitaire,
            total_ligne=quantite * prix_unitaire,
            type_conditionnement=type_conditionnement
        )

        db.session.add(ligne)

        # 🔥 Mise à jour Stock
        stock = Stock.query.filter_by(
            produit_id=produit_id,
            magasin_id=magasin_id,
            type_conditionnement=type_conditionnement
        ).first()

        if stock:
            stock.ajouter(quantite)
        else:
            stock = Stock(
                produit_id=produit_id,
                magasin_id=magasin_id,
                quantite=quantite,
                type_conditionnement=type_conditionnement
            )
            db.session.add(stock)

    # 🔥 Calcul total global
    achat.calculer_totaux()

    db.session.commit()

    flash("Achat enregistré avec succès", "success")
    return redirect(url_for("nouveau_achat"))


@app.route("/bon-livraison/nouveau/<int:commande_id>")
@login_required
def nouveau_bon_livraison(commande_id):

    commande = BonCommande.query.get_or_404(commande_id)

    return render_template(
        "bon_livraison_nouveau.html",
        commande=commande
    )


@app.route("/bon-livraison/create", methods=["POST"])
@login_required
def create_bon_livraison():

    commande_id = request.form.get("commande_id")
    commande = BonCommande.query.get_or_404(commande_id)

    # -----------------------
    # Quantité commandée
    # -----------------------

    quantite_commande = {}

    for ligne in commande.lignes:
        quantite_commande[ligne.produit_id] = \
            quantite_commande.get(ligne.produit_id, 0) + ligne.quantite

    # -----------------------
    # Quantité déjà livrée
    # -----------------------

    quantite_livree = {}

    livraisons = BonLivraison.query.filter_by(
        commande_id=commande.id
    ).all()

    for bl in livraisons:
        for ligne in bl.lignes:
            quantite_livree[ligne.produit_id] = \
                quantite_livree.get(ligne.produit_id, 0) + ligne.quantite

    # -----------------------
    # Données formulaire
    # -----------------------

    lignes_commande_ids = request.form.getlist("ligne_commande_id[]")
    produits_ids = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    numeros_series = request.form.getlist("numero_serie[]")

    # -----------------------
    # Vérifier dépassement
    # -----------------------

    for pid, qte in zip(produits_ids, quantites):

        pid = int(pid)
        qte = int(qte or 0)

        deja_livre = quantite_livree.get(pid, 0)
        commande_qte = quantite_commande.get(pid, 0)

        if deja_livre + qte > commande_qte:

            flash(
                "❌ Vous ne pouvez pas livrer plus que la quantité commandée",
                "danger"
            )

            return redirect(
                url_for("nouveau_bon_livraison", commande_id=commande.id)
            )

    # -----------------------
    # Générer numéro BL
    # -----------------------

    numero = generate_code_bon_livraison(
        commande,
        produits_ids,
        quantites
    )

    # -----------------------
    # Création BL
    # -----------------------

    bon = BonLivraison(
        numero=numero,
        client_id=commande.client_id,
        commande_id=commande.id
    )

    db.session.add(bon)
    db.session.flush()

    lignes_creees = 0

    # -----------------------
    # Ajouter lignes BL
    # -----------------------

    for ligne_commande_id, pid, qte, ns in zip(
        lignes_commande_ids,
        produits_ids,
        quantites,
        numeros_series
    ):

        qte = int(qte or 0)

        if qte == 0:
            continue

        ligne_commande = LigneBonCommande.query.get(int(ligne_commande_id))

        if not ligne_commande:
            continue

        ligne = LigneBonLivraison(
            bon_id=bon.id,
            produit_id=int(pid),
            quantite=qte,
            ligne_commande_id=ligne_commande.id,
            numero_serie=ns
        )

        db.session.add(ligne)

        lignes_creees += 1

        quantite_livree[int(pid)] = \
            quantite_livree.get(int(pid), 0) + qte

    # -----------------------
    # Empêcher BL vide
    # -----------------------

    if lignes_creees == 0:

        db.session.rollback()

        flash("⚠ Aucun produit à livrer", "warning")

        return redirect(
            url_for("nouveau_bon_livraison", commande_id=commande.id)
        )

    # -----------------------
    # Statut BL
    # -----------------------

    bl_complet = True

    for pid, qte in quantite_commande.items():

        if quantite_livree.get(pid, 0) < qte:
            bl_complet = False
            break

    if bl_complet:
        bon.status = "livree"
    else:
        bon.status = "partielle"

    # -----------------------
    # Statut commande
    # -----------------------

    commande_complete = True

    for pid, qte in quantite_commande.items():

        if quantite_livree.get(pid, 0) < qte:
            commande_complete = False
            break

    if commande_complete:
        commande.status = "livree"
    else:
        commande.status = "livraison_partielle"

    db.session.commit()

    flash("Bon de livraison créé avec succès", "success")

    return redirect(
        url_for("detail_bon_livraison", id=bon.id)
    )


@app.route("/bon-livraison/delete", methods=["POST"])
@login_required
def delete_bon_livraisons():

    ids = request.form.getlist("bons_ids[]")

    if not ids:
        flash("Veuillez sélectionner au moins un bon", "warning")
        return redirect(url_for("liste_bons_livraison"))

    commandes_a_verifier = set()

    for id in ids:

        bon = BonLivraison.query.get(id)

        if bon:

            commandes_a_verifier.add(bon.commande_id)

            # supprimer lignes
            LigneBonLivraison.query.filter_by(
                bon_id=bon.id
            ).delete()

            # supprimer BL
            db.session.delete(bon)

    db.session.commit()

    # -----------------------------
    # Recalcul du statut commande
    # -----------------------------

    for commande_id in commandes_a_verifier:

        commande = BonCommande.query.get(commande_id)

        if not commande:
            continue

        quantite_commande = {
            l.produit_id: l.quantite
            for l in commande.lignes
        }

        quantite_livree = {}

        for bl in commande.livraisons:
            for ligne in bl.lignes:
                quantite_livree[ligne.produit_id] = \
                    quantite_livree.get(ligne.produit_id, 0) + ligne.quantite

        if not quantite_livree:
            commande.status = "confirmee"

        else:
            complete = True

            for pid, qte in quantite_commande.items():

                if quantite_livree.get(pid, 0) < qte:
                    complete = False
                    break

            if complete:
                commande.status = "livree"
            else:
                commande.status = "livraison_partielle"

    db.session.commit()

    flash("Bons de livraison supprimés avec succès", "success")

    return redirect(url_for("liste_bons_livraison"))


@app.route("/bon-livraison/<int:id>")
@login_required
def detail_bon_livraison(id):

    bon = BonLivraison.query.get_or_404(id)

    return render_template(
        "bon_livraison_detail.html",
        bon=bon
    )


@app.route("/bon-livraison")
@login_required
def liste_bons_livraison():

    status = request.args.get("status")

    query = BonLivraison.query

    if status:
        query = query.filter_by(status=status)

    bons = query.order_by(
        BonLivraison.date_creation.desc()
    ).all()

    return render_template(
        "bon_livraison_liste.html",
        bons=bons,
        status=status
    )


@app.route("/bon-livraison/partiel/<int:commande_id>")
@login_required
def livraison_partielle(commande_id):

    commande = BonCommande.query.get_or_404(commande_id)

    return render_template(
        "bon_livraison_partiel.html",
        commande=commande
    )


@app.route("/bon-livraison/<int:id>/pdf")
def bon_livraison_pdf(id):

    compagnie = Compagnie.query.first()
    bon = BonLivraison.query.get_or_404(id)

    html = render_template(
        "bon_livraison_detail.html",   # 👈 même fichier
        compagnie=compagnie,
        bon=bon,
        pdf_mode=True 
    )

    pdf = HTML(string=html, base_url=request.root_url).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = \
        f"inline; filename=bon_livraison_{bon.id}.pdf"

    return response



from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError


@app.route("/bon-livraison/edit/<int:id>", methods=["GET", "POST"])
def modifier_bon_livraison(id):

    bon = BonLivraison.query.get_or_404(id)

    if request.method == "POST":

        try:

            bon.client_id = request.form.get("client_id")
            bon.nota_bene = request.form.get("nota_bene")

            # modifier la date
            date_str = request.form.get("date_creation")
            if date_str:
                bon.date_creation = datetime.strptime(date_str, "%Y-%m-%d")

            # supprimer les anciennes lignes
            LigneBonLivraison.query.filter_by(bon_id=bon.id).delete()

            produits_ids = request.form.getlist("produit_id[]")
            lignes_commande_ids = request.form.getlist("ligne_commande_id[]")
            quantites = request.form.getlist("quantite[]")
            numeros_series = request.form.getlist("numero_serie[]")

            for pid, ligne_commande_id, qte, ns in zip(
                produits_ids,
                lignes_commande_ids,
                quantites,
                numeros_series
            ):

                qte = int(qte or 0)

                if qte == 0:
                    continue

                ligne = LigneBonLivraison(
                    bon_id=bon.id,
                    produit_id=int(pid),
                    quantite=qte,
                    ligne_commande_id=int(ligne_commande_id),
                    numero_serie=ns
                )

                db.session.add(ligne)

            db.session.commit()

            flash("Bon de livraison modifié avec succès", "success")

            return redirect(url_for("detail_bon_livraison", id=bon.id))

        except SQLAlchemyError:

            db.session.rollback()

            flash("Erreur lors de la modification", "danger")

    clients = Client.query.all()
    produits = Produit.query.all()

    return render_template(
        "modifier_bon_livraison.html",
        bon=bon,
        clients=clients,
        produits=produits
    )




@app.route("/certificat-installation/<int:id>")
def certificat_installation(id):

    bon = BonLivraison.query.get_or_404(id)
    compagnie = Compagnie.query.first()

    # transformer BL en CI
    numero_ci = bon.numero.replace("BL", "CI")

    return render_template(
        "certificat_installation.html",
        bon=bon,
        numero_ci=numero_ci,
        compagnie=compagnie
    )


@app.route("/certificat-installation/pdf/<int:id>")
def certificat_installation_pdf(id):

    bon = BonLivraison.query.get_or_404(id)
    compagnie = Compagnie.query.first()

    numero_ci = bon.numero.replace("BL", "CI")

    html = render_template(
        "certificat_installation.html",
        bon=bon,
        compagnie=compagnie,
        numero_ci=numero_ci,
        pdf_mode=True
    )

    pdf = HTML(string=html, base_url=request.root_url).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=CI_{bon.numero}.pdf"

    return response


@app.route("/vendeur/ajouter", methods=["POST"])
@login_required
def ajouter_vendeur():

    nom = request.form.get("nom")
    telephone = request.form.get("telephone")

    if not nom or not telephone:
        flash("Tous les champs sont obligatoires", "danger")
        return redirect(url_for("liste_vendeurs"))

    vendeur_existant = Vendeur.query.filter_by(nom=nom.strip()).first()
    if vendeur_existant:
        flash("Ce vendeur existe déjà", "warning")
        return redirect(url_for("liste_vendeurs"))

    try:
        vendeur = Vendeur(
            nom=nom.strip(),
            telephone=telephone.strip()
        )

        db.session.add(vendeur)
        db.session.commit()

        flash("Vendeur ajouté avec succès ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("liste_vendeurs"))



@app.route("/gestion_materiel/vendeurs")
@login_required
def liste_vendeurs():

    vendeurs = (
        Vendeur.query
        .order_by(Vendeur.nom.asc())
        .all()
    )

    return render_template(
        "liste_vendeurs.html",
        vendeurs=vendeurs
    )


@app.route("/vendeur/supprimer/<int:vendeur_id>", methods=["POST"])
@login_required
def supprimer_vendeur(vendeur_id):

    vendeur = Vendeur.query.get_or_404(vendeur_id)

    # 🔒 Empêcher suppression si ventes existantes
    if vendeur.ventes:
        flash("Impossible de supprimer : vendeur lié à des ventes", "danger")
        return redirect(url_for("liste_vendeurs"))

    try:
        db.session.delete(vendeur)
        db.session.commit()
        flash("Vendeur supprimé avec succès", "success")
    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("liste_vendeurs"))



@app.route("/paiement/<int:paiement_id>/reverser", methods=["POST"])
@login_required
def reverser_paiement(paiement_id):

    paiement = Paiement.query.get_or_404(paiement_id)
    vente = paiement.vente

    # 🔒 Déjà annulé
    if paiement.annule:
        flash("Ce paiement est déjà annulé", "warning")
        return redirect(url_for("paiement_vente", vente_id=vente.id))

    try:
        montant_inverse = -paiement.montant

        # 1️⃣ Paiement inverse
        paiement_inverse = Paiement(
            vente=vente,
            montant=montant_inverse,
            mode="reversion",
            date_paiement=datetime.now(timezone.utc)
        )

        # 2️⃣ Marquer l’ancien paiement annulé
        paiement.annule = True

        # 3️⃣ Mettre à jour la vente
        vente.montant_paye += montant_inverse
        vente.reste_a_payer = vente.total - vente.montant_paye

        if vente.montant_paye <= 0:
            vente.statut_paiement = "impaye"
            vente.montant_paye = Decimal("0.00")
        elif vente.reste_a_payer > 0:
            vente.statut_paiement = "partiel"
        else:
            vente.statut_paiement = "paye"

        db.session.add(paiement_inverse)
        db.session.commit()

        flash("Paiement reversé avec succès 🔄", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("paiement_vente", vente_id=vente.id))

@app.route("/vente/<int:vente_id>/paiement", methods=["GET"])
@login_required
def paiement_vente(vente_id):

    vente = (
        Vente.query
        .options(joinedload(Vente.paiements))
        .get_or_404(vente_id)
    )

    return render_template(
        "paiement.html",
        vente=vente
    )



@app.route("/paiement/ajouter/<int:vente_id>", methods=["POST"])
@login_required
def ajouter_paiement(vente_id):

    vente = Vente.query.get_or_404(vente_id)

    # 🔒 Sécurité : vente déjà soldée
    if vente.statut_paiement == "paye":
        flash("Cette vente est déjà totalement payée", "warning")
        return redirect(url_for("paiement_vente", vente_id=vente.id))

    try:
        # 📥 Données formulaire
        montant = Decimal(request.form.get("montant"))
        mode = request.form.get("mode")
        reference = request.form.get("reference_paiement")

        # 🚨 Validations
        if montant <= 0:
            raise ValueError("Montant invalide")

        if montant > vente.reste_a_payer:
            raise ValueError("Le montant dépasse le reste à payer")
        
        # 🚨 Validation référence si nécessaire
        if mode in ["cheque", "virement"] and not reference:
            raise ValueError("Veuillez entrer le numéro de référence")


        # =========================
        # 🧾 1️⃣ CRÉATION DU PAIEMENT
        # =========================
        paiement = Paiement(
            vente_id=vente.id,
            montant=montant,
            mode=mode,
            reference_paiement=reference if mode in ["cheque", "virement"] else None,
            date_paiement=datetime.now(timezone.utc)
        )

        db.session.add(paiement)

        # =========================
        # 🔁 2️⃣ MISE À JOUR DE LA VENTE
        # =========================
        vente.montant_paye += montant
        vente.reste_a_payer = vente.total - vente.montant_paye

        if vente.reste_a_payer == 0:
            vente.statut_paiement = "paye"
        else:
            vente.statut_paiement = "partiel"

        # =========================
        # 🧾 3️⃣ SYNCHRONISATION FACTURE
        # =========================
        facture = vente.facture
        if facture:
            facture.montant_paye = vente.montant_paye
            facture.reste_a_payer = vente.reste_a_payer
            facture.statut = vente.statut_paiement

        db.session.commit()

        flash("Paiement enregistré avec succès 💰", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("paiement_vente", vente_id=vente.id))


@app.route("/facture/<int:vente_id>")
@login_required
def voir_facture(vente_id):

    facture = Facture.query.filter_by(vente_id=vente_id).first_or_404()
    compagnie = Compagnie.query.first()
    

    return render_template(
        "facture.html",
        facture=facture,
        compagnie=compagnie
    )


@app.route("/factures")
@login_required
def liste_factures():

    factures = (
        Facture.query
        .join(Vente)
        .order_by(Facture.date_facture.desc())
        .all()
    )

    return render_template(
        "liste_factures.html",
        factures=factures
    )


@app.route("/proformas")
@login_required
def liste_proformas():

    proformas = Proforma.query.order_by(Proforma.id.desc()).all()

    return render_template(
        "liste_proforma.html",
        proformas=proformas
    )


@app.route("/proforma/nouveau")
@login_required
def nouvelle_proforma():

    clients = Client.query.all()
    produits = Produit.query.all()
    conditionnements = TypeConditionnement

    return render_template(
        "nouvelle_proforma.html",
        clients=clients,
        produits=produits,
        conditionnements=conditionnements
    )



@app.route("/proforma/create", methods=["POST"])
@login_required
def create_proforma():

    client_id = request.form.get("client_id")
    condition_paiement = request.form.get("condition_paiement")
    delai_livraison = request.form.get("delai_livraison")
    garantie = request.form.get("garantie")
    attn = request.form.get("attn")

    if not client_id:
        flash("Veuillez choisir un client")
        return redirect(url_for("nouvelle_proforma"))
    
    conditionnement = request.form.getlist("conditionnement[]")

    numero = f"PRO-{datetime.now().strftime('%Y%m%d%H%M%S')}"


    proforma = Proforma(
        numero=numero,
        client_id=client_id,
        condition_paiement=condition_paiement,
        delai_livraison=delai_livraison,
        garantie=garantie,
        attn=attn
    )

    db.session.add(proforma)
    db.session.flush()

    produits = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    prix = request.form.getlist("prix[]")

    total = 0

    for i in range(len(produits)):

        produit_id = produits[i]
        quantite = int(quantites[i])
        prix_unitaire = float(prix[i])

        sous_total = quantite * prix_unitaire
        total += sous_total

        ligne = LigneProforma(
            proforma_id=proforma.id,
            produit_id=produit_id,
            conditionnement=conditionnement[i],   # AJOUT ICI
            quantite=quantite,
            prix_unitaire=prix_unitaire,
            sous_total=sous_total
        )

        db.session.add(ligne)

    proforma.total = total

    db.session.commit()

    return redirect(url_for("details_proforma", proforma_id=proforma.id))
    

@app.route("/proforma/<int:proforma_id>")
def details_proforma(proforma_id):

    proforma = Proforma.query.get_or_404(proforma_id)
    return render_template(
        "details_proforma.html",
        proforma=proforma
    )
    



@app.route("/proforma/<int:proforma_id>/pdf")
@login_required
def proforma_pdf(proforma_id):

    proforma = Proforma.query.get_or_404(proforma_id)

    compagnie = Compagnie.query.first()

    # récupérer tous les produits
    produits = Produit.query.all()

    # dictionnaire id -> produit (nécessaire pour les kits)
    produits_id_map = {p.id: p for p in produits}

    # total en lettres
    total_lettre = num2words(proforma.total, lang="fr").capitalize()

    html = render_template(
        "proforma_pdf.html",
        proforma=proforma,
        compagnie=compagnie,
        attn=proforma.attn,
        total_lettre=total_lettre,
        produits_id_map=produits_id_map
    )

    pdf = HTML(
        string=html,
        base_url=request.root_url
    ).write_pdf()

    response = make_response(pdf)

    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = f"inline; filename=proforma_{proforma.numero}.pdf"

    return response


@app.route("/kit-proforma/nouveau")
@login_required
def nouveau_kit_proforma():

    clients = Client.query.all()
    produits = Produit.query.all()

    return render_template(
        "nouveau_kit.html",
        clients=clients,
        produits=produits
    )



# Route pour modifier un kit
@app.route('/modifier-kit-proforma/<int:kit_id>', methods=['GET', 'POST'])
def modifier_kit_proforma(kit_id):
    kit = KitProforma.query.get_or_404(kit_id)
    
    if request.method == 'POST':
        try:
            # Mise à jour des informations de base du kit
            kit.client_id = request.form.get('client_id')
            kit.attn = request.form.get('attn')
            kit.date = datetime.strptime(request.form.get('date_proforma'), '%Y-%m-%d').date()
            kit.condition_paiement = request.form.get('condition_paiement')
            kit.delai_livraison = request.form.get('delai_livraison')
            kit.garantie = request.form.get('garantie')
            kit.prix_global = float(request.form.get('prix_global', 0))
            
            # SUPPRIMER toutes les lignes existantes
            for ligne in kit.lignes:
                db.session.delete(ligne)
            
            # SUPPRIMER tous les blocs existants
            for bloc in kit.blocs:
                db.session.delete(bloc)
            
            # IMPORTANT: Récupérer l'ordre des blocs depuis le formulaire
            # On cherche tous les champs bloc_titre_XXX pour identifier l'ordre
            bloc_ids_ordonnes = []
            
            # Méthode 1: Parcourir tous les champs du formulaire
            for field in request.form.keys():
                if field.startswith('bloc_titre_'):
                    # Extraire l'ID du bloc (new_XXX ou chiffre)
                    bloc_id = field.replace('bloc_titre_', '')
                    if bloc_id not in bloc_ids_ordonnes:
                        bloc_ids_ordonnes.append(bloc_id)
            
            # Méthode 2: Si vous avez un champ caché avec l'ordre, utilisez-le
            # ordre_blocs = request.form.getlist('ordre_blocs[]')
            
            # Traiter chaque bloc dans l'ordre
            for bloc_id in bloc_ids_ordonnes:
                # Récupérer le titre du bloc
                bloc_titre = request.form.get(f'bloc_titre_{bloc_id}', '')
                
                # Récupérer les listes pour ce bloc
                produits = request.form.getlist(f'produit_{bloc_id}[]')
                quantites = request.form.getlist(f'quantite_{bloc_id}[]')
                types = request.form.getlist(f'type_{bloc_id}[]')
                
                # Vérifier si ce bloc a au moins un produit valide
                a_produits_valides = False
                produits_valides = []
                quantites_valides = []
                types_valides = []
                
                for i in range(len(produits)):
                    if produits[i] and quantites[i]:
                        a_produits_valides = True
                        produits_valides.append(produits[i])
                        quantites_valides.append(quantites[i])
                        types_valides.append(types[i] if i < len(types) else 'secondaire')
                
                if not a_produits_valides:
                    continue  # Ignorer les blocs vides
                
                # Créer un nouveau bloc
                nouveau_bloc = BlocKit(
                    kit_id=kit.id,
                    nom=bloc_titre or f"Bloc"
                )
                db.session.add(nouveau_bloc)
                db.session.flush()  # Pour obtenir l'ID
                
                # Créer les lignes pour ce bloc en préservant l'ordre des produits
                for i in range(len(produits_valides)):
                    # Déterminer si c'est un produit principal
                    est_principal = (types_valides[i] == 'principal')
                    
                    ligne = LigneKitProforma(
                        kit_id=kit.id,
                        bloc_id=nouveau_bloc.id,
                        produit_id=int(produits_valides[i]),
                        quantite=int(quantites_valides[i])
                    )
                    db.session.add(ligne)
            
            # Traiter les produits hors bloc
            produits_hors_bloc = request.form.getlist('produit_hors_bloc[]')
            quantites_hors_bloc = request.form.getlist('quantite_hors_bloc[]')
            
            for i in range(len(produits_hors_bloc)):
                if produits_hors_bloc[i] and quantites_hors_bloc[i]:
                    ligne = LigneKitProforma(
                        kit_id=kit.id,
                        bloc_id=None,
                        produit_id=int(produits_hors_bloc[i]),
                        quantite=int(quantites_hors_bloc[i])
                    )
                    db.session.add(ligne)
            
            db.session.commit()
            flash('Kit modifié avec succès', 'success')
            return redirect(url_for('list_kit_proforma'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'danger')
            print(f"Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # GET request
    clients = Client.query.all()
    produits = Produit.query.all()
    
    return render_template('modifier_kit_proforma.html', 
                         kit=kit, 
                         clients=clients, 
                         produits=produits)
# Route pour supprimer un kit
@app.route('/supprimer-kit-proforma/<int:kit_id>')
def supprimer_kit_proforma(kit_id):
    kit = KitProforma.query.get_or_404(kit_id)
    
    try:
        # Supprimer d'abord les lignes associées
        for ligne in kit.lignes:
            db.session.delete(ligne)
        
        # Supprimer le kit
        db.session.delete(kit)
        db.session.commit()
        
        flash('Kit supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('list_kit_proforma'))



@app.route("/kit-proforma/create", methods=["POST"])
@login_required
def create_kit_proforma():
    try:
        client_id = request.form.get("client_id")
        prix_global = request.form.get("prix_global")
        attn = request.form.get("attn")
        condition_paiement = request.form.get("condition_paiement")
        delai_livraison = request.form.get("delai_livraison")
        garantie = request.form.get("garantie")

        numero = f"{datetime.now().strftime('%Y%m%M%S')}"

        # Création du kit
        kit = KitProforma(
            numero=numero,
            client_id=client_id,
            prix_global=prix_global,
            attn=attn,
            condition_paiement=condition_paiement,
            delai_livraison=delai_livraison,
            garantie=garantie
        )
        db.session.add(kit)
        db.session.flush()

        # Récupérer le nombre de blocs
        bloc_indices = set()
        for key in request.form.keys():
            if key.startswith('produit_principal_'):
                bloc_indices.add(int(key.split('_')[2]))
        
        # Pour chaque bloc
        for i in sorted(bloc_indices):
            # Récupérer le produit principal et sa quantité
            produit_principal_id = request.form.get(f"produit_principal_{i}")
            quantite_principale = request.form.get(f"quantite_principale_{i}", 1)
            
            if produit_principal_id and produit_principal_id.strip():
                # Créer un nom de bloc basé sur le produit principal
                produit = Produit.query.get(int(produit_principal_id))
                nom_bloc = produit.nom_produit if produit else f"Bloc {i+1}"
                
                # Créer le bloc
                bloc = BlocKit(
                    kit_id=kit.id,
                    nom=nom_bloc
                )
                db.session.add(bloc)
                db.session.flush()
                
                # Ajouter la ligne pour le produit principal
                ligne_principale = LigneKitProforma(
                    kit_id=kit.id,
                    bloc_id=bloc.id,
                    produit_id=int(produit_principal_id),
                    quantite=int(quantite_principale) if quantite_principale else 1
                )
                db.session.add(ligne_principale)
                
                # Récupérer les produits secondaires
                produits_secondaires = request.form.getlist(f"produit_secondaire_{i}[]")
                quantites_secondaires = request.form.getlist(f"quantite_secondaire_{i}[]")
                
                # Ajouter les produits secondaires
                for j, produit_id in enumerate(produits_secondaires):
                    if produit_id and produit_id.strip():
                        quantite = quantites_secondaires[j] if j < len(quantites_secondaires) else 1
                        ligne_secondaire = LigneKitProforma(
                            kit_id=kit.id,
                            bloc_id=bloc.id,
                            produit_id=int(produit_id),
                            quantite=int(quantite) if quantite else 1
                        )
                        db.session.add(ligne_secondaire)

        db.session.commit()
        flash(f"Kit proforma {kit.numero} créé avec succès!", "success")
        return redirect(url_for("details_kit_proforma", kit_id=kit.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la création du kit: {str(e)}", "danger")
        return redirect(url_for("nouveau_kit_proforma"))


@app.route("/kit-proforma")
@login_required
def list_kit_proforma():

    kits = KitProforma.query.order_by(KitProforma.date.desc()).all()

    return render_template(
        "list_kit.html",
        kits=kits
    )


@app.route("/kit-proforma/<int:kit_id>")
@login_required
def details_kit_proforma(kit_id):

    kit = KitProforma.query.get_or_404(kit_id)

    return render_template(
        "details_kit.html",
        kit=kit
    )


@app.route("/kit-proforma/<int:kit_id>/pdf")
@login_required
def kit_proforma_pdf(kit_id):
    # Charger le kit avec toutes ses relations
    kit = KitProforma.query.options(
        db.joinedload(KitProforma.client),
        db.joinedload(KitProforma.blocs)
            .joinedload(BlocKit.lignes)
            .joinedload(LigneKitProforma.produit),
        db.joinedload(KitProforma.lignes)
            .joinedload(LigneKitProforma.produit)
    ).get_or_404(kit_id)
    
    compagnie = Compagnie.query.first()
    
    # Vérifier si le prix_global existe
    prix = kit.prix_global if kit.prix_global else 0
    
    # Convertir en lettres
    try:
        from num2words import num2words
        total_lettre = num2words(prix, lang='fr').capitalize() + " francs CFA"
    except:
        total_lettre = str(prix) + " francs CFA"
    
    # ===== DÉBOGAGE DES IMAGES =====
    # Ajoutez ce bloc ici pour voir les URLs des images
    print("\n=== DÉBOGAGE DES IMAGES CLOUDINARY ===")
    for bloc in kit.blocs:
        if bloc.lignes and len(bloc.lignes) > 0:
            produit = bloc.lignes[0].produit
            if produit:
                print(f"Bloc: {bloc.nom}")
                print(f"  Produit: {produit.nom_produit}")
                print(f"  Image URL: {produit.image if produit.image else 'AUCUNE IMAGE'}")
                
                # Vérifier si l'URL commence bien par http
                if produit.image:
                    if produit.image.startswith('http'):
                        print(f"  ✅ URL valide (commence par http)")
                    else:
                        print(f"  ⚠️ URL peut-être invalide: {produit.image[:50]}...")
    
    # Aussi pour les produits hors bloc
    if kit.lignes:
        for ligne in kit.lignes:
            if ligne.produit and ligne.produit.image and not ligne.bloc_id:
                print(f"Produit hors bloc: {ligne.produit.nom_produit}")
                print(f"  Image URL: {ligne.produit.image}")
    print("===============================\n")
    
    # Réorganiser les lignes de chaque bloc
    for bloc in kit.blocs:
        if bloc.lignes and len(bloc.lignes) > 1:
            lignes_liste = list(bloc.lignes)
            
            produit_principal = None
            autres_produits = []
            
            for ligne in lignes_liste:
                if ligne.produit and ligne.produit.nom_produit == bloc.nom:
                    produit_principal = ligne
                else:
                    autres_produits.append(ligne)
            
            if not produit_principal and lignes_liste:
                produit_principal = lignes_liste[0]
                autres_produits = lignes_liste[1:]
            
            if produit_principal:
                nouvelles_lignes = [produit_principal] + autres_produits
                bloc.lignes = nouvelles_lignes
    
    html = render_template(
        "kit_proforma_pdf.html",
        kit=kit,
        compagnie=compagnie,
        total_lettre=total_lettre
    )
    
    # Générer le PDF
    pdf = HTML(
        string=html,
        base_url=request.root_url
    ).write_pdf()
    
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=kit_proforma_{kit.numero}.pdf"
    
    return response

@app.route("/bon-commande")
@login_required
def liste_bons_commandes():

    bons = BonCommande.query.order_by(
        BonCommande.date_creation.desc()
    ).all()

    return render_template(
        "bon_commande_liste.html",
        bons=bons
    )


@app.route("/bon-commande/nouveau")
@login_required
def nouveau_bon_commande():

    clients = Client.query.order_by(Client.nom_client).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()

    return render_template(
        "bon_commande_nouveau.html",
        clients=clients,
        produits=produits,
        TypeConditionnement=TypeConditionnement
    )


@app.route("/bon-commande/create", methods=["POST"])
@login_required
def create_bon_commande():

    client_id = request.form.get("client_id")

    bon = BonCommande(
        numero="TEMP",
        client_id=client_id,
        status="confirmee"
    )

    db.session.add(bon)
    db.session.flush()

    bon.numero = generate_code_bon_commande(bon.id)

    total = 0

    produits_ids = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    prix = request.form.getlist("prix_unitaire[]")
    conditionnements = request.form.getlist("type_conditionnement[]")

    for pid, qte, pu, cond in zip(produits_ids, quantites, prix, conditionnements):

        if not pid or not qte or not pu:
            continue

        qte = int(qte)
        pu = float(pu)

        sous_total = qte * pu
        total += sous_total

        ligne = LigneBonCommande(
            bon_id=bon.id,
            produit_id=int(pid),
            quantite=qte,
            prix_unitaire=pu,
            sous_total=sous_total,
            type_conditionnement=TypeConditionnement(cond)
        )

        db.session.add(ligne)

    bon.total = total

    db.session.commit()

    flash("Bon de commande créé", "success")

    return redirect(url_for("details_bon_commande", bon_id=bon.id))


@app.route("/bon-commande/<int:bon_id>")
@login_required
def details_bon_commande(bon_id):

    bon = BonCommande.query.get_or_404(bon_id)

    return render_template(
        "details_bon_commande.html",
        bon=bon
    )


@app.route("/bon-commande/<int:bon_id>/pdf")
@login_required
def bon_commande_pdf(bon_id):

    bon = BonCommande.query.get_or_404(bon_id)
    compagnie = Compagnie.query.first()

    html = render_template(
        "bon_commande_pdf.html",
        bon=bon,
        compagnie=compagnie
    )

    pdf = HTML(
        string=html,
        base_url=request.root_url
    ).write_pdf()

    response = make_response(pdf)

    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = f"inline; filename=bon_commande_{bon.id}.pdf"

    return response



@app.route('/gestion_materiel/compagnie', methods=['GET', 'POST'])
@login_required
def compagnie():
    form = CompagnieForm()
    compagnie = Compagnie.query.first()

    if form.validate_on_submit():
        if not compagnie:
            compagnie = Compagnie()

        form.populate_obj(compagnie)

        if form.logo.data:
            upload = cloudinary.uploader.upload(
                form.logo.data,
                folder="logos"
            )
            compagnie.logo = upload["secure_url"]

        db.session.add(compagnie)
        db.session.commit()

        flash("Informations enregistrées avec succès", "success")
        return redirect(url_for('compagnie'))

    # Pré-remplissage
    if compagnie:
        form.nom.data = compagnie.nom
        form.telephone.data = compagnie.telephone
        form.email.data = compagnie.email
        form.adresse.data = compagnie.adresse
        form.ville.data = compagnie.ville
        form.numero_rcc.data = compagnie.numero_rcc

    return render_template(
        'compagnie.html',
        form=form,
        compagnie=compagnie
    )


@app.route("/rapport/stock")
@login_required
def rapport_stock():

    produit_id = request.args.get("produit_id", type=int)
    magasin_id = request.args.get("magasin_id", type=int)

    query = Stock.query

    if produit_id:
        query = query.filter(Stock.produit_id == produit_id)

    if magasin_id:
        query = query.filter(Stock.magasin_id == magasin_id)

    stocks = query.all()

    produits = Produit.query.all()
    magasins = Magasin.query.all()

    return render_template(
        "rapport_stock.html",
        stocks=stocks,
        produits=produits,
        magasins=magasins
    )



from sqlalchemy import and_

@app.route("/rapport/client")
@login_required
def rapport_client():

    client_id = request.args.get("client_id", type=int)
    statut = request.args.get("statut")

    clients = Client.query.order_by(Client.nom_client).all()

    # ===============================
    # CAS 1 : CLIENT SPECIFIQUE
    # ===============================
    if client_id:

        ventes = Vente.query.options(
            joinedload(Vente.paiements)
        ).filter(Vente.client_id == client_id)\
         .order_by(Vente.date_vente.desc())\
         .all()

        if statut == "solde":
            ventes = [v for v in ventes if v.reste_a_payer == 0]
        elif statut == "non_solde":
            ventes = [v for v in ventes if v.reste_a_payer > 0]

        vente_ids = [v.id for v in ventes]

        paiements = Paiement.query.filter(
            Paiement.vente_id.in_(vente_ids)
        ).order_by(Paiement.date_paiement.desc()).all() if vente_ids else []

        total_ventes = sum(v.total for v in ventes)
        total_paiements = sum(p.montant for p in paiements)
        reste_global = total_ventes - total_paiements

        return render_template(
            "rapport_client.html",
            clients=clients,
            ventes=ventes,
            paiements=paiements,
            total_ventes=total_ventes,
            total_paiements=total_paiements,
            reste_global=reste_global,
            client_id=client_id,
            statut=statut,
            rapport_par_client=None
        )

    # ===============================
    # CAS 2 : TOUS LES CLIENTS
    # ===============================
    rapport_par_client = []

    for client in clients:

        ventes = Vente.query.options(
            joinedload(Vente.paiements)
        ).filter(Vente.client_id == client.id).all()

        if statut == "solde":
            ventes = [v for v in ventes if v.reste_a_payer == 0]
        elif statut == "non_solde":
            ventes = [v for v in ventes if v.reste_a_payer > 0]

        if not ventes:
            continue

        vente_ids = [v.id for v in ventes]

        paiements = Paiement.query.filter(
            Paiement.vente_id.in_(vente_ids)
        ).all()

        total_ventes = sum(v.total for v in ventes)
        total_paiements = sum(p.montant for p in paiements)
        reste = total_ventes - total_paiements

        rapport_par_client.append({
            "client": client,
            "ventes": ventes,
            "paiements": paiements,
            "total_ventes": total_ventes,
            "total_paiements": total_paiements,
            "reste": reste
        })

    return render_template(
        "rapport_client.html",
        clients=clients,
        rapport_par_client=rapport_par_client,
        client_id=None,
        statut=statut
    )




@app.route("/rapport/vendeur")
@login_required
def rapport_vendeur():

    vendeur_id = request.args.get("vendeur_id", type=int)

    vendeurs = Vendeur.query.all()

    ventes = []
    total = 0

    if vendeur_id:
        ventes = Vente.query.filter_by(vendeur_id=vendeur_id)\
                            .order_by(Vente.date_vente.desc())\
                            .all()

        total = sum(v.total for v in ventes)

    return render_template(
        "rapport_vendeur.html",
        vendeurs=vendeurs,
        ventes=ventes,
        total=total
    )




@app.route("/rapport/client/pdf")
@login_required
def rapport_client_pdf():

    client_id = request.args.get("client_id", type=int)
    statut = request.args.get("statut")

    # ==================================================
    # CAS 1 : CLIENT SPÉCIFIQUE
    # ==================================================
    if client_id:

        client = Client.query.get_or_404(client_id)

        ventes = Vente.query.options(
            joinedload(Vente.paiements)
        ).filter(
            Vente.client_id == client_id
        ).all()


        # Filtre statut
        if statut == "solde":
            ventes = [v for v in ventes if v.reste_a_payer == 0]
        elif statut == "non_solde":
            ventes = [v for v in ventes if v.reste_a_payer > 0]

        vente_ids = [v.id for v in ventes]

        paiements = []
        if vente_ids:
            paiements = Paiement.query.filter(
                Paiement.vente_id.in_(vente_ids),
                Paiement.annule == False   # on ignore paiements annulés
            ).all()

        total = sum(v.total for v in ventes) if ventes else 0
        total_paye = sum(p.montant for p in paiements) if paiements else 0
        reste = total - total_paye

        html = render_template(
            "rapport_client_pdf.html",
            client=client,
            ventes=ventes,
            paiements=paiements,
            total=total,
            total_paye=total_paye,
            reste=reste,
            statut=statut,
            date_rapport=datetime.now()
        )

        pdf = HTML(
            string=html,
            base_url=current_app.root_path
        ).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = \
            f"inline; filename=rapport_client_{client.id}.pdf"

        return response

    # ==================================================
    # CAS 2 : TOUS LES CLIENTS
    # ==================================================

    clients = Client.query.order_by(Client.nom_client).all()
    rapport_par_client = []

    for client in clients:

        ventes = Vente.query.options(
            joinedload(Vente.paiements)
        ).filter(
            Vente.client_id == client.id
        ).all()

        if statut == "solde":
            ventes = [v for v in ventes if v.reste_a_payer == 0]
        elif statut == "non_solde":
            ventes = [v for v in ventes if v.reste_a_payer > 0]

        if not ventes:
            continue

        vente_ids = [v.id for v in ventes]

        paiements = Paiement.query.filter(
            Paiement.vente_id.in_(vente_ids),
            Paiement.annule == False
        ).all() if vente_ids else []

        total = sum(v.total for v in ventes)
        total_paye = sum(p.montant for p in paiements)
        reste = total - total_paye

        rapport_par_client.append({
            "client": client,
            "ventes": ventes,
            "paiements": paiements,
            "total": total,
            "total_paye": total_paye,
            "reste": reste
        })

    html = render_template(
        "rapport_client_pdf_all.html",
        rapport_par_client=rapport_par_client,
        statut=statut,
        date_rapport=datetime.now()
    )

    pdf = HTML(
        string=html,
        base_url=current_app.root_path
    ).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = \
        "inline; filename=rapport_tous_clients.pdf"

    return response


@app.route("/etat/propositions")
@login_required
def etat_propositions():

    ventes = Vente.query.options(
        joinedload(Vente.client),
        joinedload(Vente.paiements)
    ).order_by(
        Vente.client_id,
        Vente.date_vente.desc()
    ).all()

    etat = {}

    for v in ventes:
        client = v.client

        if client.id not in etat:
            etat[client.id] = {
                "client": client,
                "factures": [],
                "total_reste": 0
            }

        etat[client.id]["factures"].append(v)
        etat[client.id]["total_reste"] += v.reste_a_payer or 0

    return render_template(
        "etat_propositions.html",
        etat=etat.values()
    )


@app.route("/etat/propositions/pdf")
@login_required
def etat_propositions_pdf():

    ventes = Vente.query.options(
        joinedload(Vente.client),
        joinedload(Vente.paiements)
    ).order_by(
        Vente.client_id,
        Vente.date_vente.desc()
    ).all()

    etat = {}

    for v in ventes:
        client = v.client

        if client.id not in etat:
            etat[client.id] = {
                "client": client,
                "factures": [],
                "total_reste": 0
            }

        etat[client.id]["factures"].append(v)
        etat[client.id]["total_reste"] += v.reste_a_payer or 0

    html = render_template(
        "etat_propositions_pdf.html",
        etat=etat.values(),
        now=datetime.now()
    )

    pdf = HTML(string=html, base_url=request.base_url).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=etat_propositions.pdf"

    return response


@app.route("/etat/stock/pdf")
@login_required
def etat_stock_pdf():

    stocks = Stock.query.options(
        joinedload(Stock.produit),
        joinedload(Stock.magasin)
    ).all()

    html = render_template(
        "etat_stock_pdf.html",
        stocks=stocks,
        now=datetime.now()
    )

    pdf = HTML(string=html, base_url=request.base_url).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=etat_stock.pdf"

    return response


@app.route("/etat/stock/excel")
@login_required
def etat_stock_excel():

    stocks = Stock.query.options(
        joinedload(Stock.produit),
        joinedload(Stock.magasin)
    ).all()

    data = []

    for s in stocks:

        if s.quantite == 0:
            statut = "Rupture"
        elif s.quantite < s.seuil_alerte:
            statut = "Stock Faible"
        else:
            statut = "Disponible"

        data.append({
            "Code Produit": s.produit.code_produit,
            "Magasin": s.magasin.nom,
            "Produit": s.produit.nom_produit,
            "Conditionnement": s.type_conditionnement.value,
            "Quantité": float(s.quantite),
            "Seuil Alerte": float(s.seuil_alerte),
            "Statut": statut
        })

    df = pd.DataFrame(data)

    # 🔹 Génération fichier Excel
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Etat Stock", index=False)

    output.seek(0)

    return send_file(
        output,
        download_name="etat_stock.xlsx",
        as_attachment=True
    )


@app.route('/gestion_materiel/magasin', methods=['GET', 'POST'])
def magasin():
    form = MagasinForm()

    if form.validate_on_submit():
        nouveau = Magasin(nom=form.nom.data)
        db.session.add(nouveau)
        db.session.commit()
        return redirect(url_for('magasin'))

    magasins = Magasin.query.all()
    return render_template("magasin.html", magasins=magasins, form=form)


@app.route('/gestion_materiel/magasin/edit/<int:id>', methods=['POST'])
def edit_magasin(id):
    magasin = Magasin.query.get_or_404(id)
    form = MagasinForm()

    if form.validate_on_submit():
        magasin.nom = form.nom.data
        db.session.commit()

    return redirect(url_for('magasin'))


@app.route('/gestion_materiel/magasin/delete', methods=['POST'])
def delete_magasins():
    ids = request.form.getlist('magasin_ids')

    for id in ids:
        magasin = Magasin.query.get(id)
        if magasin:
            db.session.delete(magasin)

    db.session.commit()
    return redirect(url_for('magasin'))


@app.route('/logs', methods=['GET', 'POST'])
def logs():

    form = LogFilterForm()
    logs = None

    # Remplir dynamiquement les utilisateurs
    utilisateurs = User.query.all()
    form.utilisateur.choices = [("", "Tous les utilisateurs")] + [
        (str(u.id), u.username) for u in utilisateurs
    ]

    if form.validate_on_submit():

        date_debut = datetime.combine(form.date_debut.data, datetime.min.time())
        date_fin = datetime.combine(form.date_fin.data, datetime.max.time())

        query = Log.query.filter(
            Log.created_at.between(date_debut, date_fin)
        )

        # Si utilisateur sélectionné
        if form.utilisateur.data:
            query = query.filter(Log.user_id == int(form.utilisateur.data))

        logs = query.order_by(Log.created_at.desc()).all()

    return render_template("logs.html", form=form, logs=logs)


@app.route('/certificats')
def liste_certificats():
    """Liste tous les certificats de réparation"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Récupérer tous les certificats
    certificats = CertificatReparation.query.order_by(
        CertificatReparation.date_creation.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Calculer les statistiques
    from sqlalchemy import func
    total_montant = db.session.query(func.sum(ReparationDetail.cout_reparation)).scalar() or 0
    
    # Nombre de certificats ce mois
    from datetime import datetime
    now = datetime.now()
    debut_mois = datetime(now.year, now.month, 1)
    certificats_mois = CertificatReparation.query.filter(
        CertificatReparation.date_creation >= debut_mois
    ).count()
    
    # Nombre total de produits réparés
    total_produits = ReparationDetail.query.count()
    
    return render_template('certificats_liste.html', 
                         certificats=certificats,
                         total_montant=total_montant,
                         certificats_mois=certificats_mois,
                         total_produits=total_produits,
                         per_page=per_page)


@app.route('/certificats/creer', methods=['GET', 'POST'])
def creer_certificat():
    """Créer un nouveau certificat de réparation"""
    form = CertificatReparationForm()
    
    # Générer automatiquement le numéro de certificat
    if request.method == 'GET':
        form.numero_certificat.data = generer_numero_certificat()
    
    # Remplir la liste des clients
    form.client_id.choices = [(0, 'Choisir un client')] + [
        (c.id, f"{c.nom_client} - {c.telephone}") for c in Client.query.order_by(Client.nom_client).all()
    ]
    
    # Remplir la liste des produits
    produits = Produit.query.order_by(Produit.marque, Produit.model, Produit.nom_produit).all()
    produits_choices = [(0, 'Choisir un produit')] + [
        (p.id, f"{p.marque} {p.model} - {p.nom_produit}") for p in produits
    ]
    
    # IMPORTANT: Initialiser les choix pour TOUS les formulaires de réparation existants
    if form.reparations:
        for reparation_form in form.reparations:
            reparation_form.produit_id.choices = produits_choices
    
    if request.method == 'POST':
        print("=== DÉBUT SOUMISSION POST ===")
        print("Form data:", request.form)
        print("Form validation:", form.validate_on_submit())
        print("Form errors:", form.errors)
        
        if form.validate_on_submit():
            try:
                # Créer le certificat
                certificat = CertificatReparation(
                    numero_certificat=form.numero_certificat.data,
                    date_reparation=form.date_reparation.data,
                    client_id=form.client_id.data,
                    observations=form.observations.data,
                    technicien=form.technicien.data
                )
                
                db.session.add(certificat)
                db.session.flush()
                
                # Ajouter les détails de réparation
                for i, reparation_form in enumerate(form.reparations.data):
                    if reparation_form.get('produit_id') and reparation_form.get('taches_effectuees'):
                        reparation = ReparationDetail(
                            certificat_id=certificat.id,
                            produit_id=reparation_form['produit_id'],
                            numero_serie=reparation_form['numero_serie'],
                            taches_effectuees=reparation_form['taches_effectuees'],
                            cout_reparation=reparation_form.get('cout_reparation', 0.0),
                            garantie_mois=reparation_form.get('garantie_mois', 3)
                        )
                        db.session.add(reparation)
                
                db.session.commit()
                flash(f'Certificat {certificat.numero_certificat} créé avec succès!', 'success')
                return redirect(url_for('voir_certificat', id=certificat.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la création: {str(e)}', 'danger')
                print(f"Erreur: {e}")
        else:
            print("Erreurs de validation:", form.errors)
            # Afficher les erreurs pour déboguer
            for field, errors in form.errors.items():
                print(f"Field {field}: {errors}")
            flash('Veuillez corriger les erreurs dans le formulaire', 'danger')
    
    return render_template('certificats_creer.html', 
                         form=form, 
                         produits=produits,
                         produits_choices=produits_choices)

@app.route('/certificats/<int:id>')
def voir_certificat(id):
    """Voir un certificat spécifique"""
    certificat = CertificatReparation.query.get_or_404(id)
    return render_template('certificats_voir.html', certificat=certificat)


@app.route('/certificats/<int:id>/modifier', methods=['GET', 'POST'])
def modifier_certificat(id):
    """Modifier un certificat existant"""
    certificat = CertificatReparation.query.get_or_404(id)
    
    # Passer l'ID du certificat au formulaire
    form = CertificatReparationForm(obj=certificat, certificat_id=id)
    
    # Remplir la liste des clients
    form.client_id.choices = [(0, 'Choisir un client')] + [
        (c.id, f"{c.nom_client} - {c.telephone}") for c in Client.query.order_by(Client.nom_client).all()
    ]
    
    # Remplir la liste des produits
    produits = Produit.query.order_by(Produit.marque, Produit.model, Produit.nom_produit).all()
    produits_choices = [(0, 'Choisir un produit')] + [
        (p.id, f"{p.marque} {p.model} - {p.nom_produit}") for p in produits
    ]
    
    if request.method == 'GET':
        # Initialiser les formulaires de réparation
        form.reparations = []
        for reparation in certificat.reparations:
            reparation_form = ReparationDetailForm()
            reparation_form.produit_id.choices = produits_choices
            reparation_form.produit_id.data = reparation.produit_id
            reparation_form.numero_serie.data = reparation.numero_serie
            reparation_form.taches_effectuees.data = reparation.taches_effectuees
            reparation_form.cout_reparation.data = reparation.cout_reparation
            reparation_form.garantie_mois.data = reparation.garantie_mois
            reparation_form.id.data = reparation.id
            form.reparations.append(reparation_form)
        
        # Ajouter un formulaire vide si aucun produit
        if len(form.reparations) == 0:
            empty_form = ReparationDetailForm()
            empty_form.produit_id.choices = produits_choices
            form.reparations.append(empty_form)
    
    if request.method == 'POST':
        print("=== MODIFICATION POST ===")
        print("Form data:", request.form)
        
        # Remplir les choix des produits avant validation
        for reparation_form in form.reparations:
            reparation_form.produit_id.choices = produits_choices
        
        if form.validate_on_submit():
            try:
                # Mettre à jour le certificat
                certificat.numero_certificat = form.numero_certificat.data
                certificat.date_reparation = form.date_reparation.data
                certificat.client_id = form.client_id.data
                certificat.observations = form.observations.data
                certificat.technicien = form.technicien.data
                
                # Supprimer les anciennes réparations
                for reparation in certificat.reparations:
                    db.session.delete(reparation)
                
                # Ajouter les nouvelles réparations
                for reparation_form in form.reparations:
                    if reparation_form.produit_id.data and reparation_form.produit_id.data != 0:
                        if reparation_form.taches_effectuees.data and reparation_form.taches_effectuees.data.strip():
                            new_reparation = ReparationDetail(
                                certificat_id=certificat.id,
                                produit_id=reparation_form.produit_id.data,
                                numero_serie=reparation_form.numero_serie.data,
                                taches_effectuees=reparation_form.taches_effectuees.data,
                                cout_reparation=reparation_form.cout_reparation.data or 0.0,
                                garantie_mois=reparation_form.garantie_mois.data or 3
                            )
                            db.session.add(new_reparation)
                
                db.session.commit()
                flash('Certificat modifié avec succès!', 'success')
                return redirect(url_for('voir_certificat', id=certificat.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la modification: {str(e)}', 'danger')
                print(f"Erreur: {e}")
        else:
            print("Erreurs de validation:", form.errors)
            for field, errors in form.errors.items():
                print(f"Field {field}: {errors}")
            flash('Veuillez corriger les erreurs dans le formulaire', 'danger')
    
    return render_template('certificats_modifier.html', 
                         form=form, 
                         certificat=certificat,
                         produits=produits,
                         produits_choices=produits_choices)


@app.route('/certificats/<int:id>/supprimer', methods=['POST'])
def supprimer_certificat(id):
    """Supprimer un certificat"""
    certificat = CertificatReparation.query.get_or_404(id)
    
    try:
        db.session.delete(certificat)
        db.session.commit()
        flash(f'Certificat {certificat.numero_certificat} supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('liste_certificats'))


@app.route('/certificats/<int:id>/pdf')
def generer_pdf_certificat(id):
    """Générer le PDF du certificat"""
    certificat = CertificatReparation.query.get_or_404(id)
    
    try:
        # Générer le HTML
        rendered_html = render_template('certificats_pdf.html', certificat=certificat)
        
        # Créer le PDF
        pdf = HTML(string=rendered_html).write_pdf()
        
        # Retourner le PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=certificat_{certificat.numero_certificat}.pdf'
        return response
        
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {str(e)}', 'danger')
        return redirect(url_for('voir_certificat', id=certificat.id))


@app.route('/api/produits/recherche')
def api_recherche_produits():
    """API pour rechercher des produits via AJAX"""
    term = request.args.get('term', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if term:
        produits = Produit.query.filter(
            db.or_(
                Produit.code_produit.ilike(f'%{term}%'),
                Produit.nom_produit.ilike(f'%{term}%'),
                Produit.model.ilike(f'%{term}%'),
                Produit.marque.ilike(f'%{term}%')
            )
        ).limit(limit).all()
    else:
        produits = Produit.query.limit(limit).all()
    
    results = [{
        'id': p.id,
        'code_produit': p.code_produit,
        'nom_produit': p.nom_produit,
        'model': p.model or '',
        'marque': p.marque or '',
        'description': p.description or ''
    } for p in produits]
    
    return jsonify(results)


@app.route('/api/clients/recherche')
def api_recherche_clients():
    """API pour rechercher des clients via AJAX"""
    term = request.args.get('term', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if term:
        clients = Client.query.filter(
            db.or_(
                Client.nom_client.ilike(f'%{term}%'),
                Client.telephone.ilike(f'%{term}%'),
                Client.adresse.ilike(f'%{term}%')
            )
        ).limit(limit).all()
    else:
        clients = Client.query.limit(limit).all()
    
    results = [{
        'id': c.id,
        'nom_client': c.nom_client,
        'telephone': c.telephone or '',
        'adresse': c.adresse,
        'attn': c.attn or ''
    } for c in clients]
    
    return jsonify(results)


@app.route('/certificats/recherche')
def recherche_certificats():
    """Page de recherche avancée des certificats"""
    search_term = request.args.get('q', '')
    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')
    
    query = CertificatReparation.query
    
    if search_term:
        query = query.filter(
            db.or_(
                CertificatReparation.numero_certificat.ilike(f'%{search_term}%'),
                CertificatReparation.technicien.ilike(f'%{search_term}%')
            )
        )
    
    if date_debut:
        query = query.filter(CertificatReparation.date_reparation >= datetime.strptime(date_debut, '%Y-%m-%d'))
    
    if date_fin:
        query = query.filter(CertificatReparation.date_reparation <= datetime.strptime(date_fin, '%Y-%m-%d'))
    
    certificats = query.order_by(CertificatReparation.date_creation.desc()).all()
    
    return render_template('certificats_recherche.html', 
                         certificats=certificats, 
                         search_term=search_term,
                         date_debut=date_debut,
                         date_fin=date_fin)


@app.route('/gestion_materiel/user')
@login_required
def user():
    return render_template('user.html')


@app.route('/logout')
@login_required
def logout():
  logout_user()
  flash("utilisateur déconnecté", "success")
  return redirect(url_for('login'))
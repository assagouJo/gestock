from app import app, db, login_manager
from flask import request, render_template, flash, redirect, url_for, get_flashed_messages, abort
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Client, Produit, LigneFacture, Paiement, Facture, Compagnie, Vente, LigneVente, Stock
from forms import LoginForm, ClientForm, ProduitForm, UserForm, ChangePasswordForm, CompagnieForm, VenteForm, StockForm
from functools import wraps
from werkzeug.utils import secure_filename
import os
from werkzeug.utils import secure_filename
import uuid
from cloudinary.uploader import upload
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from helper import generate_code_produit, generate_numero_facture
from werkzeug.security import generate_password_hash
from werkzeug.security import generate_password_hash
import cloudinary.uploader
from cloudinary.uploader import upload



@app.route("/create-admin")
def create_admin():
    # éviter doublon
    user = User.query.filter_by(username="admin").first()
    if user:
        return "Admin already exists"

    user = User(
        username="admin",
        email="admin@gestock.com",
        password_hash=generate_password_hash("admin123"),
        role="admin"
    )
    db.session.add(user)
    db.session.commit()
    return "Admin created"




@app.template_filter('money')
def money(value):
    if value is None:
        return "0"
    return "{:,.2f}".format(value).replace(",", " ").replace(".", ",")


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
    def is_active(endpoint):
        return request.endpoint == endpoint
    return dict(is_active=is_active)


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("entree_stock"))

    form = LoginForm(csrf_enabled=False)

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)

            if user.must_change_password:
                return redirect(url_for('force_change_password'))

            # 🔥 REDIRECTION SELON LE RÔLE
            if user.role == "admin":
                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("entree_stock"))

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

    default_password = "password@123"  
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



@app.route('/dashboard')
@login_required
@role_required("admin")
def dashboard():
     # TOTAL VENTES

    return render_template("dashboard.html")


@app.route('/gestion_materiel/produit', methods=['GET', 'POST'])
@login_required
def produit():
    form = ProduitForm(csrf_enabled=False)
    produits = Produit.query.order_by(Produit.nom_produit).all()
    
    if form.validate_on_submit():
        file = form.image.data
        image_url = None
        if file and file.filename:
            result = upload(
                file,
                folder="gestock/produits"
            )
            image_url = result["secure_url"]

        nouveau_produit = Produit(
        nom_produit = form.nom_produit.data,
        description=form.description.data,
        code_produit=generate_code_produit(),
        image = image_url
        )
        db.session.add(nouveau_produit)
        db.session.commit()

        print("ID:", nouveau_produit.id)
        print("Nom:", nouveau_produit.nom_produit)
        print("Code:", nouveau_produit.code_produit)


        flash("Produit ajouter avec succes", "success")
        return redirect(url_for("produit"))
    
    return render_template('produit.html', form=form, produits=produits)
    





@app.route('/gestion_materiel/produit/edit/<int:id>', methods=['POST'])
@login_required
@role_required("admin")
def edit_produit(id):
    produit = Produit.query.get_or_404(id)
    form = ProduitForm()

    if form.validate_on_submit():
        # champs texte / stock
        produit.nom_produit = form.nom_produit.data
        produit.description = form.description.data
        produit.stock = form.stock.data

        file = form.image.data

        # 🔄 NOUVELLE IMAGE ?
        if file and file.filename:
            # supprimer l’ancienne image Cloudinary
            delete_cloudinary_image(produit.image)

            # upload nouvelle image
            result = upload(
                file,
                folder="gestock/produits"
            )
            produit.image = result["secure_url"]

        db.session.commit()
        flash("Produit modifié avec succès", "success")

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


from sqlalchemy import exists

@app.route('/gestion_materiel/produit/delete', methods=['POST'])
@login_required
@role_required("admin")
def delete_produits():
    ids = request.form.getlist('produit_ids')

    if not ids:
        flash("Aucun produit sélectionné", "warning")
        return redirect(url_for('produit'))

    produits = Produit.query.filter(Produit.id.in_(ids)).all()
    produits_bloques = []

    for p in produits:
        # 🔒 Stock non nul
        if p.stock > 0:
            produits_bloques.append(f"{p.nom_produit} (stock non nul)")
            continue

        # 🔒 Produit déjà utilisé dans une vente
        vente_existante = db.session.query(
            exists().where(LigneVente.produit_id == p.id)
        ).scalar()

        if vente_existante:
            produits_bloques.append(f"{p.nom_produit} (déjà vendu)")

    # ⛔ BLOQUER AVANT DELETE
    if produits_bloques:
        flash(
            "Impossible de supprimer : " + ", ".join(produits_bloques),
            "danger"
        )
        return redirect(url_for('produit'))

    # ✅ Suppression sécurisée (produits jamais vendus)
    for p in produits:
        delete_cloudinary_image(p.image)
        db.session.delete(p)

    db.session.commit()

    flash(f"{len(produits)} produit(s) supprimé(s) avec succès", "success")
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
      adresse_email = form.adresse_email.data,
      ville = form.ville.data,
      numero_rcc = form.numero_rcc.data        
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

    Client.query.filter(Client.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    flash(f"{len(ids)} client(s) supprimé(s)", "success")
    return redirect(url_for('client'))



@app.route("/stock", methods=["GET"])
@login_required
def etat_stock():
    produits_all = Produit.query.order_by(Produit.nom_produit).all()

    stocks = (
        Stock.query
        .join(Produit)
        .order_by(Stock.numero_lot)
        .all()
    )

    return render_template(
        "ajout_stock.html",   # ta page unique
        stocks=stocks,
        produits_all=produits_all
    )


@app.route("/delete/lot", methods=["POST"])
def delete_lot():
    stock_ids = request.form.getlist("stock_ids[]")

    if not stock_ids:
        flash("Aucun produit sélectionné", "warning")
        return redirect(url_for("etat_stock"))

    # Supprimer TOUS les stocks liés aux produits
    Stock.query.filter(
        Stock.id.in_(stock_ids)
    ).delete(synchronize_session=False)

    db.session.commit()

    flash("Stock supprimé avec succès 🗑️", "success")
    return redirect(url_for("etat_stock"))


@app.route("/stock/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_stock():

    # 🔒 Sécurité : si quelqu’un accède en GET
    if request.method == "GET":
        return redirect(url_for("etat_stock"))

    # 📥 Récupération des données du formulaire
    lots = request.form.getlist("numero_lot[]")
    produits = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")

    # 🧪 Debug (tu peux enlever après)
    print("LOTS :", lots)
    print("PRODUITS :", produits)
    print("QUANTITES :", quantites)

    # 🚨 Validation minimale
    if not lots or not produits or not quantites:
        flash("Aucune donnée reçue ❌", "danger")
        return redirect(url_for("etat_stock"))

    # 🔄 Traitement ligne par ligne
    for lot, produit_id, quantite in zip(lots, produits, quantites):

        # ⛔ Ignorer les lignes incomplètes
        if not lot or not produit_id or not quantite:
            continue

        lot = lot.strip()

        # ⛔ Ignorer les lots vides après trim
        if lot == "":
            continue

        try:
            produit_id = int(produit_id)
            quantite = int(quantite)
        except ValueError:
            continue

        # ⛔ Quantité invalide
        if quantite <= 0:
            continue

        # 🔍 Chercher si le lot existe déjà pour ce produit
        stock = Stock.query.filter_by(
            produit_id=produit_id,
            numero_lot=lot
        ).first()

        if stock:
            # ➕ Ajouter à un lot existant
            stock.ajouter(quantite)
        else:
            # ➕ Créer un nouveau lot
            stock = Stock(
                produit_id=produit_id,
                numero_lot=lot,
                quantite=quantite
            )
            db.session.add(stock)

    # 💾 Sauvegarde
    db.session.commit()

    flash("Stock enregistré avec succès ✅", "success")
    return redirect(url_for("etat_stock"))






@app.route('/vente/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_vente():
    # 🔹 Compatibilité SQLite / PostgreSQL
    # engine = db.engine.name
    # if engine == "sqlite":
    #     produits_agg = func.group_concat(Produit.nom_produit, ', ')
    # else:
    #     produits_agg = func.string_agg(Produit.nom_produit, ', ')

    # 🔹 Données affichage
    clients = Client.query.order_by(Client.nom_client).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()

    ventes = (
    Vente.query
    .options(
        db.joinedload(Vente.client),
        db.joinedload(Vente.lignes).joinedload(LigneVente.produit)
    )
    .order_by(Vente.id.desc())
    .all()
)

    # 🔹 ENREGISTREMENT VENTE
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')

        if not client_id or not produits_ids:
            flash("Données invalides", "danger")
            return redirect(url_for('nouvelle_vente'))

        try:
            vente = Vente(client_id=int(client_id))
            db.session.add(vente)
            db.session.flush()  # récupère vente.id

            total_vente = 0

            for pid, qte, pu in zip(produits_ids, quantites, prix_unitaires):
                produit = Produit.query.get_or_404(int(pid))
                qte = int(qte)
                pu = Decimal(pu)

                # 🔹 Récupération des stocks (FIFO + verrou)
                stocks = (
                    db.session.query(Stock)
                    .filter_by(produit_id=produit.id)
                    .with_for_update()
                    .order_by(Stock.date_creation.asc())
                    .all()
                )

                stock_total = sum(s.quantite for s in stocks)

                if stock_total < qte:
                    raise ValueError(
                        f"Stock insuffisant pour {produit.nom_produit}"
                    )

                # 🔹 Décrémentation FIFO
                quantite_a_retirer = qte
                for stock in stocks:
                    if quantite_a_retirer <= 0:
                        break

                    if stock.quantite >= quantite_a_retirer:
                        stock.retirer(quantite_a_retirer)
                        quantite_a_retirer = 0
                    else:
                        quantite_a_retirer -= stock.quantite
                        stock.retirer(stock.quantite)

                sous_total = qte * pu
                total_vente += sous_total

                ligne = LigneVente(
                    vente_id=vente.id,
                    produit_id=produit.id,
                    quantite=qte,
                    prix_unitaire=pu,
                    sous_total=sous_total
                )
                db.session.add(ligne)

            vente.total = total_vente
            db.session.commit()

            flash("Vente enregistrée avec succès", "success")
            return redirect(url_for('nouvelle_vente'))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for('nouvelle_vente'))

    # 🔹 AFFICHAGE
    return render_template(
        'liste_vente.html',
        clients=clients,
        produits=produits,
        ventes=ventes
    )


@app.route('/vente/supprimer', methods=['POST'])
@login_required
def supprimer_ventes():
    vente_ids = request.form.getlist('vente_ids')

    if not vente_ids:
        flash("Aucune vente sélectionnée", "warning")
        return redirect(url_for('nouvelle_vente'))

    try:
        for vente_id in vente_ids:
            vente = Vente.query.get(int(vente_id))
            if not vente:
                continue

            lignes = LigneVente.query.filter_by(vente_id=vente.id).all()

            # 🔁 Restaurer le stock
            for ligne in lignes:
                stocks = (
                    db.session.query(Stock)
                    .filter_by(produit_id=ligne.produit_id)
                    .with_for_update()
                    .order_by(Stock.date_creation.desc())
                    .all()
                )

                if not stocks:
                    raise ValueError("Lot introuvable pour restauration du stock")

                # On remet tout dans le dernier lot
                stocks[0].ajouter(ligne.quantite)

            # 🔥 Supprimer lignes + vente
            LigneVente.query.filter_by(vente_id=vente.id).delete()
            db.session.delete(vente)

        db.session.commit()
        flash("Vente(s) supprimée(s) avec succès", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")

    return redirect(url_for('nouvelle_vente'))




@app.route('/facture/generer/<int:vente_id>')
@login_required
def generer_facture(vente_id):

    vente = Vente.query.get_or_404(vente_id)

    # 🔒 éviter doublon
    if vente.facture:
        return redirect(url_for('voir_facture', facture_id=vente.facture.id))

    numero = generate_numero_facture(vente_id)

    facture = Facture(
        numero=numero,
        type_facture="FACTURE",
        vente_id=vente.id,
        client_id=vente.client_id,
        total=vente.total,
        statut="VALIDEE"
    )

    db.session.add(facture)
    db.session.commit()

    return redirect(url_for('voir_facture'))





@app.route('/facture/<int:facture_id>', methods=['GET', 'POST'])
def voir_facture(facture_id):
    compagnie = Compagnie.query.first()
    facture = Facture.query.get_or_404(facture_id)
    facture.statut
    db.session.commit()

    return render_template('facture.html', facture=facture, compagnie=compagnie)


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
            filename = secure_filename(form.logo.data.filename)
            form.logo.data.save(
                os.path.join(app.config['UPLOAD_FOLDER'], filename)
            )
            compagnie.logo = filename

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



@app.route('/rapport')
@login_required
def rapport():
    return render_template('rapport.html')



# @app.route("/stock")
# def voir_stock():
#     produits = Produit.query.order_by(Produit.nom_produit).all()
#     return render_template("stock.html", produits=produits)


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
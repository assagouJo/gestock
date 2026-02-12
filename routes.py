from app import app, db, login_manager
from datetime import datetime, timezone
from flask import request, render_template, flash, redirect, url_for, get_flashed_messages, abort, make_response
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Client, Produit, Compagnie, Vente, LigneVente, Stock, Paiement, Facture, Proforma, LigneProforma, Magasin
from forms import LoginForm, ClientForm, ProduitForm, UserForm, ChangePasswordForm, CompagnieForm, ProformaForm
from functools import wraps
from werkzeug.utils import secure_filename
import os
from werkzeug.utils import secure_filename
import uuid
from cloudinary.uploader import upload
from decimal import Decimal
from sqlalchemy import func, exists
from sqlalchemy.exc import SQLAlchemyError
from helper import generate_code_produit, generate_numero_facture
from werkzeug.security import generate_password_hash
import cloudinary.uploader
from cloudinary.uploader import upload
from weasyprint import HTML


def creer_magasins_defaut():
    magasins_defaut = ["Imedical", "Lavilla", "Gonzague"]

    for nom in magasins_defaut:
        existe = Magasin.query.filter_by(nom=nom).first()
        if not existe:
            db.session.add(Magasin(nom=nom))

    db.session.commit()

with app.app_context():
    creer_magasins_defaut()


@app.template_filter('money')
def montant_format(valeur):
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")



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
        if current_user.role == "admin":
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("etat_stock"))

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
                return redirect(url_for("etat_stock"))

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



@app.route('/dashboard')
@login_required
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

        # 🔒 1️⃣ Stock non nul
        if p.stock_total > 0:
            produits_bloques.append(f"{p.nom_produit} (stock non nul)")
            continue

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




@app.route("/stock", methods=["GET"])
@login_required
def etat_stock():
    produits_all = Produit.query.order_by(Produit.nom_produit).all()
    magasins = Magasin.query.order_by(Magasin.nom).all()

    stocks = (
        Stock.query
        .join(Produit)
        .filter(Stock.quantite > 0) 
        .order_by(Stock.numero_lot)
        .all()
    )    

    return render_template(
        "ajout_stock.html",   # ta page unique
        stocks=stocks,
        produits_all=produits_all,
        magasins=magasins
    )


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

    # 📥 Récupération des données
    lots = request.form.getlist("numero_lot[]")
    produits = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    magasins = request.form.getlist("magasin_id[]")  # ✅ AJOUT

    # 🚨 Validation minimale
    if not lots or not produits or not quantites or not magasins:
        flash("Aucune donnée reçue ❌", "danger")
        return redirect(url_for("etat_stock"))

    for lot, produit_id, quantite, magasin_id in zip(lots, produits, quantites, magasins):

        if not lot or not produit_id or not quantite or not magasin_id:
            continue

        lot = lot.strip()
        if lot == "":
            continue

        try:
            produit_id = int(produit_id)
            quantite = int(quantite)
            magasin_id = int(magasin_id)
        except ValueError:
            continue

        if quantite <= 0:
            continue

        # 🔍 Vérification complète
        stock = Stock.query.filter_by(
            produit_id=produit_id,
            numero_lot=lot,
            magasin_id=magasin_id   # ✅ IMPORTANT
        ).first()

        if stock:
            stock.quantite += quantite
        else:
            stock = Stock(
                produit_id=produit_id,
                numero_lot=lot,
                quantite=quantite,
                magasin_id=magasin_id
            )
            db.session.add(stock)

    db.session.commit()

    flash("Stock enregistré avec succès ✅", "success")
    return redirect(url_for("etat_stock"))


from sqlalchemy.orm import joinedload


@app.route('/vente/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_vente():

    # =========================
    # 🔹 DONNÉES POUR AFFICHAGE
    # =========================
    clients = Client.query.order_by(Client.nom_client).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()

    ventes = (
        Vente.query
        .options(
            joinedload(Vente.client),
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
        stock_ids = request.form.getlist('stock_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')

        if not client_id or not stock_ids:
            flash("Données invalides", "danger")
            return redirect(url_for('nouvelle_vente'))

        try:
            # =========================
            # 🔹 1️⃣ CRÉATION VENTE (INIT)
            # =========================
            vente = Vente(
                client_id=int(client_id),
                date_vente=datetime.now(timezone.utc),
                total=Decimal("0.00"),
                montant_paye=Decimal("0.00"),
                reste_a_payer=Decimal("0.00"),
                statut_paiement="impaye"
            )

            db.session.add(vente)
            db.session.flush()  # 🔥 permet d’avoir vente.id

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
            # 🔹 3️⃣ FINALISATION VENTE
            # =========================
            vente.total = total_vente
            vente.reste_a_payer = total_vente

            facture = Facture(
                vente_id=vente.id,
                numero="FAC-"+ generate_numero_facture(vente.id),
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
        ventes=ventes
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

        # 🚨 Validations
        if montant <= 0:
            raise ValueError("Montant invalide")

        if montant > vente.reste_a_payer:
            raise ValueError("Le montant dépasse le reste à payer")

        # =========================
        # 🧾 1️⃣ CRÉATION DU PAIEMENT
        # =========================
        paiement = Paiement(
            vente_id=vente.id,
            montant=montant,
            mode=mode,
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
    
    print("LOGO =", compagnie.telephone)

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


@app.route("/proforma/nouvelle", methods=["GET", "POST"])
@login_required
def nouvelle_proforma():

    form = ProformaForm()

    # 🔹 Clients depuis la base
    clients = Client.query.order_by(Client.nom_client).all()
    form.client_id.choices = [(c.id, c.nom_client) for c in clients]

    # 🔹 Produits depuis la base
    produits = Produit.query.order_by(Produit.nom_produit).all()

    if form.validate_on_submit():

        proforma = Proforma(
            numero="PF-"+generate_code_produit(),
            client_id=form.client_id.data
        )

        db.session.add(proforma)
        db.session.flush()  # pour récupérer proforma.id

        total = 0

        produits_ids = request.form.getlist("produit_id[]")
        quantites = request.form.getlist("quantite[]")
        prix = request.form.getlist("prix[]")

        for pid, qte, pu in zip(produits_ids, quantites, prix):
            qte = int(qte)
            pu = float(pu)
            sous_total = qte * pu
            total += sous_total

            ligne = LigneProforma(
                proforma_id=proforma.id,
                produit_id=pid,
                quantite=qte,
                prix_unitaire=pu,
                sous_total=sous_total
            )
            db.session.add(ligne)

        proforma.total = total
        db.session.commit()

        flash("Proforma créée avec succès", "success")
        return redirect(url_for("voir_proforma", proforma_id=proforma.id))

    return render_template(
        "proforma_form.html",
        form=form,
        produits=produits
    )


@app.route("/proforma/<int:proforma_id>")
@login_required
def voir_proforma(proforma_id):

    proforma = Proforma.query.get_or_404(proforma_id)
    compagnie = Compagnie.query.first()  # pour logo / infos

    return render_template(
        "proforma.html",
        proforma=proforma,
        compagnie=compagnie
    )



@app.route("/proforma/<int:proforma_id>/pdf")
@login_required
def proforma_pdf(proforma_id):

    proforma = Proforma.query.get_or_404(proforma_id)
    compagnie = Compagnie.query.first()

    html = render_template(
        "proforma_pdf.html",
        proforma=proforma,
        compagnie=compagnie
    )

    pdf = HTML(string=html, base_url=request.root_url).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename=proforma_{proforma.numero}.pdf"

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



@app.route('/rapport')
@login_required
def rapport():
    return render_template('rapport.html')



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
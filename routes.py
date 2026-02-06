from app import app, db, login_manager
from flask import request, render_template, flash, redirect, url_for, get_flashed_messages, abort
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Client, Produit, LigneFacture, Paiement, Facture, Compagnie, Vente, LigneVente
from forms import LoginForm, ClientForm, ProduitForm, UserForm, ChangePasswordForm, CompagnieForm, EntreeStockForm, VenteForm
from functools import wraps
from werkzeug.utils import secure_filename
import os
from werkzeug.utils import secure_filename
import uuid
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from helper import generate_code_produit, generate_numero_facture
from werkzeug.security import generate_password_hash
from werkzeug.security import generate_password_hash



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
        filename = None
        if file:
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        nouveau_produit = Produit(
        nom_produit = form.nom_produit.data,
        description=form.description.data,
        code_produit=generate_code_produit(),
        stock=form.stock.data,
        image = filename
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
        form.populate_obj(produit)
        file = form.image.data
        if file:
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            produit.image = filename
        db.session.commit()
        flash("Produit modifié avec succès", "success")

    return redirect(url_for('produit'))



@app.route('/gestion_materiel/produit/delete', methods=['POST'])
@login_required
def delete_produits():
    ids = request.form.getlist('produit_ids')

    if not ids:
        flash("Aucun produit sélectionné", "warning")
        return redirect(url_for('produit'))

    Produit.query.filter(Produit.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    flash(f"{len(ids)} produit(s) supprimé(s)", "success")
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




@app.route('/vente/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_vente():
    engine = db.engine.name

    if engine == "sqlite":
        produits_agg = func.group_concat(Produit.nom_produit, ', ')
    else:
        produits_agg = func.string_agg(Produit.nom_produit, ', ')

    clients = Client.query.order_by(Client.nom_client).all()
    produits = Produit.query.order_by(Produit.nom_produit).all()
    ventes = (
    db.session.query(
        Vente.id,
        Vente.date_vente,
        Client.nom_client,
        Vente.total,
        produits_agg.label('produits')
    )
    .join(Client, Vente.client_id == Client.id)
    .join(LigneVente, LigneVente.vente_id == Vente.id)
    .join(Produit, LigneVente.produit_id == Produit.id)
    .group_by(Vente.id, Vente.date_vente, Client.nom_client, Vente.total)
    .order_by(Vente.id.desc())
    .all()
)  # 👈 AJOUT

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')
        prix_unitaires = request.form.getlist('prix_unitaire[]')

        if not client_id or not produits_ids:
            flash("Données invalides", "danger")
            return redirect(url_for('nouvelle_vente'))

        vente = Vente(client_id=int(client_id))
        db.session.add(vente)
        db.session.flush()

        total_vente = 0

        for pid, qte, pu in zip(produits_ids, quantites, prix_unitaires):
            produit = Produit.query.get(int(pid))
            qte = int(qte)
            pu = float(pu)

            if produit.stock < qte:
                db.session.rollback()
                flash(f"Stock insuffisant pour {produit.nom_produit}", "danger")
                return redirect(url_for('nouvelle_vente'))

            sous_total = qte * pu
            total_vente += sous_total
            produit.stock -= qte

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

    return render_template(
        'liste_vente.html',
        clients=clients,
        produits=produits,
        ventes=ventes   # 👈 AJOUT
    )



@app.route('/entree/stock', methods=['GET','POST'])
@login_required
@role_required("admin", "operateur")
def entree_stock():
    produits = Produit.query.order_by(Produit.nom_produit).all()

    if request.method == 'POST':
        produits_ids = request.form.getlist('produit_id[]')
        quantites = request.form.getlist('quantite[]')

        for pid, qte in zip(produits_ids, quantites):
            produit = Produit.query.get(int(pid))
            if produit:
                produit.stock += int(qte)

        db.session.commit()
        flash("Stock mis à jour avec succès", "success")
        # return redirect(url_for('ajout_stock'))

    # 👇 GET : affichage de la page
    return render_template("ajout_stock.html", produits=produits)



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
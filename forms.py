from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, EmailField, IntegerField, TextAreaField, DecimalField, DateField, FieldList,  TextAreaField, DateField, FloatField, IntegerField, FieldList, FormField, HiddenField
from wtforms.validators import DataRequired, Email, Optional, EqualTo, NumberRange, Length,ValidationError
from flask_wtf.file import FileField, FileAllowed
from models import CertificatReparation



class LoginForm(FlaskForm):
  username = StringField('Nom Utilisateur', validators=[DataRequired()])
  password = PasswordField('Mot de Passe', validators=[DataRequired()])
  remember = BooleanField('Se Souvenir de Moi')
  submit = SubmitField('Se connecter')


class UserForm(FlaskForm):
  username = StringField('Nom Utilisateur', validators=[DataRequired()])
  email = EmailField('Email', validators=[DataRequired(), Email()])
  password = PasswordField('Mot de Passe', validators=[Optional()])
  role = SelectField(
    'Role',
    choices=[
        ('superadmin', 'SuperAdmin'),
      ('admin', 'Admin'),
      ('support', 'Support'),
      ('operateur', 'Operateur'),
      ('finance', 'Finance')
    ],
    validators=[DataRequired()]
  )
  submit = SubmitField('Register')


class ChangePasswordForm(FlaskForm):
  password = PasswordField(
      "Nouveau mot de passe",
      validators=[
          DataRequired()
      ]
  )

  confirm = PasswordField(
      "Confirmer le mot de passe",
      validators=[
          DataRequired(),
          EqualTo('password', message="Les mots de passe ne correspondent pas")
      ]
  )

  submit = SubmitField("Valider")


class ClientForm(FlaskForm):
    nom_client = StringField("Nom client", validators=[DataRequired()])
    telephone = StringField("Telephone")
    adresse = StringField("Adresse")
    attn = StringField("ATTN")
    submit = SubmitField("Enregistrer")


class FournisseurForm(FlaskForm):
    nom_fournisseur = StringField("Nom client", validators=[DataRequired()])
    telephone = StringField("Telephone")
    adresse = StringField("Adresse")
    submit = SubmitField("Enregistrer")


class ProduitForm(FlaskForm):
    marque = StringField('Marque')
    model = StringField('Model')
    origine = StringField('Origine')
    nom_produit = StringField('Nom produit', validators=[DataRequired()])

    image = FileField(
            "Image du produit",
            validators=[
                FileAllowed(
                    ['jpg', 'jpeg', 'png', 'webp'],
                    'Images uniquement (jpg, jpeg, png, webp)'
                )
            ]
        )
    
    description = TextAreaField(
            "Description"
    )

    submit = SubmitField('Enregistrer')


class VenteForm(FlaskForm):
    client_id = SelectField(
        "Client",
        coerce=int,
        validators=[DataRequired()]
    )

    produit_id = SelectField(
        "Produit",
        coerce=int,
        validators=[DataRequired()]
    )

    quantite = IntegerField(
        "Quantité",
        validators=[DataRequired(), NumberRange(min=1)]
    )

    prix_unitaire = DecimalField(
        "Prix unitaire",
        validators=[DataRequired(), NumberRange(min=0)]
    )

    submit = SubmitField("Valider")




class CompagnieForm(FlaskForm):
    nom = StringField(
        "Nom de la compagnie",
        validators=[DataRequired()]
    )

    telephone = StringField(
        "Téléphone",
        validators=[Optional()]
    )

    email = StringField(
        "Email",
        validators=[Optional(), Email()]
    )

    adresse = StringField(
        "Adresse",
        validators=[Optional()]
    )

    ville = StringField(
        "Ville",
        validators=[Optional()]
    )

    numero_rcc = StringField(
        "RCCM",
        validators=[Optional()]
    )

    logo = FileField(
        "Logo de la compagnie",
        validators=[
           FileAllowed(
              
                    ['jpg', 'jpeg', 'png', 'webp'],
                    'Images uniquement (jpg, jpeg, png, webp)'
                )
            ]
    )


class StockForm(FlaskForm):
    
    produit_id = SelectField(
        "Produit",
        coerce=int,
        validators=[DataRequired()]
    )

    numero_lot = StringField(
        "Numéro de lot",
        validators=[
            DataRequired(),
            Length(min=1, max=120)
        ]
    )

    quantite = IntegerField(
        "Quantité",
        validators=[
            DataRequired(),
            NumberRange(min=0, message="La quantité ne peut pas être négative")
        ],
        default=0
    )

    submit = SubmitField("Enregistrer")



class ProformaForm(FlaskForm):
    client_id = SelectField(
        "Client",
        coerce=int,
        validators=[DataRequired()]
    )
    submit = SubmitField("Créer la proforma")



class MagasinForm(FlaskForm):
    nom = StringField("Nom du magasin", validators=[DataRequired()])
    submit = SubmitField("Enregistrer")


class LogFilterForm(FlaskForm):
    date_debut = DateField("Date début", validators=[DataRequired()])
    date_fin = DateField("Date fin", validators=[DataRequired()])
    utilisateur = SelectField("Utilisateur", choices=[], validate_choice=False)
    submit = SubmitField("Afficher")



# forms.py
class ReparationDetailForm(FlaskForm):
    """Formulaire pour un détail de réparation"""
    class Meta:
        csrf = True
    
    produit_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    numero_serie = StringField('Numéro de série', 
                              validators=[DataRequired(), Length(min=1, max=100)],
                              render_kw={"placeholder": "Ex: SN-2024-001"})
    taches_effectuees = TextAreaField('Tâches effectuées', 
                                     validators=[DataRequired(), Length(min=5)],
                                     render_kw={"rows": 3})
    cout_reparation = FloatField('Coût de réparation (€)', default=0.0, validators=[Optional()])
    garantie_mois = IntegerField('Garantie (mois)', default=3, validators=[Optional()])
    id = HiddenField()
    
    def __init__(self, *args, **kwargs):
        super(ReparationDetailForm, self).__init__(*args, **kwargs)
        # Initialiser les choix à une liste vide par défaut
        self.produit_id.choices = [(0, 'Chargement...')]


# forms.py
# forms.py
class CertificatReparationForm(FlaskForm):
    """Formulaire principal du certificat"""
    numero_certificat = StringField('Numéro de certificat', 
                                   validators=[Optional()],
                                   render_kw={"readonly": True})
    date_reparation = DateField('Date de réparation', 
                               validators=[DataRequired()], 
                               format='%Y-%m-%d')
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    observations = TextAreaField('Observations générales', validators=[Optional()])
    technicien = StringField('Technicien', validators=[Optional(), Length(max=100)])
    
    reparations = FieldList(FormField(ReparationDetailForm), min_entries=1)
    
    def __init__(self, *args, **kwargs):
        # Récupérer l'ID du certificat pour la modification
        self.certificat_id = kwargs.pop('certificat_id', None)
        super(CertificatReparationForm, self).__init__(*args, **kwargs)
    
    def validate_numero_certificat(self, field):
        """Vérifier que le numéro de certificat n'existe pas déjà"""
        # Ne pas valider si c'est une modification (le champ est en readonly)
        if field.render_kw and field.render_kw.get('readonly'):
            return
        
        if not field.data:
            return
        
        # Importer ici pour éviter l'import circulaire
        from models import CertificatReparation
        
        # Exclure le certificat actuel si c'est une modification
        if self.certificat_id:
            certificat = CertificatReparation.query.filter(
                CertificatReparation.numero_certificat == field.data,
                CertificatReparation.id != self.certificat_id
            ).first()
        else:
            certificat = CertificatReparation.query.filter_by(numero_certificat=field.data).first()
        
        if certificat:
            raise ValidationError('Ce numéro de certificat existe déjà')

class RechercheProduitForm(FlaskForm):
    """Formulaire de recherche de produit"""
    search = StringField('Rechercher', validators=[Optional()])
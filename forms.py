from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, EmailField, IntegerField, TextAreaField, DecimalField, DateField
from wtforms.validators import DataRequired, Email, Optional, EqualTo, NumberRange, Length
from flask_wtf.file import FileField, FileAllowed


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
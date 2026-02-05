from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, EmailField, IntegerField, TextAreaField, DecimalField
from wtforms.validators import DataRequired, Email, Optional, EqualTo, NumberRange
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
      ('admin', 'Admin'),
      ('support', 'Support'),
      ('operateur', 'Operateur')
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
    telephone = StringField("Telephone", validators=[DataRequired()])
    adresse_email = StringField("Adresse")
    ville = StringField("Ville", validators=[DataRequired()])
    numero_rcc = StringField("RCC")
    submit = SubmitField("Enregistrer")


class ProduitForm(FlaskForm):
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
            "Description",
            validators=[DataRequired()]
        )
    nom_produit = StringField('Nom produit', validators=[DataRequired()])
    stock = IntegerField(
        "Stock initial",
        default=0,
        validators=[
            NumberRange(min=0)
        ]
    )
    submit = SubmitField('Enregistrer')


class EntreeStockForm(FlaskForm):

    produit_id = SelectField(
        "Produit",
        coerce=int,
        validators=[DataRequired()]
    )

    quantite = IntegerField(
        "Quantité",
        validators=[DataRequired(), NumberRange(min=1)]
    )

    submit = SubmitField("Valider")



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
        validators=[Optional()]
    )

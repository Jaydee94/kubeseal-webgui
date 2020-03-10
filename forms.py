from flask_wtf import FlaskForm  
from wtforms import TextField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField  
from wtforms import validators, ValidationError  
  
class KubesealForm(FlaskForm):  
   cleartextSecret = TextField("Klartext-Secret ",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])  
   secretName = TextField("Secret-Name")
   secretNamespace = TextField("Secret-Namespace")
   submit = SubmitField("Verschlüsseln")

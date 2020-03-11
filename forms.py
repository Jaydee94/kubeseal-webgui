from flask_wtf import FlaskForm  
from wtforms import TextField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField  
from wtforms import validators, ValidationError  
  
class KubesealForm(FlaskForm):  
   cleartextSecret = TextField("Klartext-Secret ",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])  
   secretName = TextField("Secret-Name",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])
   secretNamespace = TextField("Secret-Namespace",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])
   submit = SubmitField("Verschlüsseln")
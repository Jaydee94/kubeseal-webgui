from flask_wtf import FlaskForm  
from wtforms import TextField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField  
from wtforms import validators, ValidationError  
  
class ContactForm(FlaskForm):  
   name = TextField("Candidate Name ",[validators.Required("Please enter your name.")])  
   Gender = RadioField('Gender', choices = [('M','Male'),('F','Female')])  
   Address = TextAreaField("Address")  
     
   email = TextField("Email",[validators.Required("Please enter your email address."),  
   validators.Email("Please enter your email address.")])  
     
   Age = IntegerField("Age")  
   language = SelectField('Programming Languages', choices = [('java', 'Java'),('py', 'Python')])  
  
   submit = SubmitField("Submit")  

from flask import Flask, render_template, flash, request
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
  
#class KubesealForm(FlaskForm):  
#   cleartextSecret = TextField("Klartext-Secret ",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])  
#   secretName = TextField("Secret-Name",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])
#   secretNamespace = TextField("Secret-Namespace",[validators.Required("Bitte geben Sie das Secret im Klartext ein.")])
#   submit = SubmitField("Verschlüsseln")

class KubesealForm(Form):
    name = TextField('Name:', validators=[validators.required()])
    
    @app.route("/", methods=['GET', 'POST'])
    def hello():
        form = ReusableForm(request.form)
        
        print form.errors
        if request.method == 'POST':
        name=request.form['name']
        print name
        
        if form.validate():
        # Save the comment here.
            flash('Hello ' + name)
        else:
            flash('Error: All the form fields are required. ')
        
        return render_template('main.html', form=form)
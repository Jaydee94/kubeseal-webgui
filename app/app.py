from flask import Flask, render_template
from flask_wtf import FlaskForm 
from wtforms import TextField
from wtforms.validators import InputRequired
from flask_bootstrap import Bootstrap
from flask import Flask
from flask_assets import Environment, Bundle
from kubeseal import Kubeseal
from os import urandom
import sys
import subprocess

app = Flask(__name__)
Bootstrap(app)

assets = Environment(app)
less = Bundle('output.css', filters='cssmin', output='screen.css')
assets.register('css_all', less)
app.config['SECRET_KEY'] = urandom(24)
  
# Defining the form
class KubesealForm(FlaskForm):
    cleartextSecret = TextField('Klartext-Secret:', validators=[InputRequired()])
    secretName = TextField('Secret-Name:', validators=[InputRequired()])
    secretNamespace = TextField('Secret-Namespace:', validators=[InputRequired()])            

# Main Page
@app.route("/", methods=['GET', 'POST'])
def run_kubeseal():
    form = KubesealForm()
    if form.validate_on_submit():
        cltSecret = form.cleartextSecret.data
        sName = form.secretName.data
        sNamespace = form.secretNamespace.data
        sealedSecret = Kubeseal.kubectlCMD(cltSecret,sNamespace,sName)
        sys.stdout.write('Created Sealed-Secret %s for namespace %s\n'%(sName,sNamespace))
        return render_template('output.html', sealedSecret=sealedSecret[0])

    return render_template('main.html', form=form)

# Main Method 
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug = True)
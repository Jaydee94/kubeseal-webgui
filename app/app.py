from flask import Flask, render_template
from flask_wtf import FlaskForm
from wtforms import TextField, TextAreaField
from wtforms.validators import InputRequired
from flask_bootstrap import Bootstrap
from flask_assets import Environment, Bundle
from kubeseal import Kubeseal
from os import urandom
import jinja2
import sys
import logging

# Configure logging settings
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger("kubseal-webgui")
flasklogger = logging.getLogger('werkzeug')
flasklogger.setLevel(logging.ERROR)

# Initialize flask app including bootstrap
app = Flask(__name__)
Bootstrap(app)
assets = Environment(app)
less = Bundle('output.css', filters='cssmin', output='screen.css')
assets.register('css_all', less)
app.config['SECRET_KEY'] = urandom(24)


# Defining the kubeseal-form
class KubesealForm(FlaskForm):
    cleartextSecret = TextAreaField('Cleartext secret:', validators=[InputRequired()])
    secretName = TextField('Secret name:', validators=[InputRequired()])
    secretNamespace = TextField('Secret namespace:', validators=[InputRequired()])


# Main Page
@app.route("/", methods=['GET', 'POST'])
def run_kubeseal():
    """Runs the kubeseal command and generates the flask form"""
    form = KubesealForm()
    # Actions after clicking the submit-button
    if form.validate_on_submit():
        cltSecret = form.cleartextSecret.data
        sName = form.secretName.data
        sNamespace = form.secretNamespace.data
        sealedSecret = Kubeseal.kubectlCMD(cltSecret, sNamespace, sName)
        log.info('Created SealedSecret [%s] for Namespace[%s]', sName, sNamespace)

        # Load data from YAML into Python dictionary
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('./templates'),
                                 trim_blocks=True, lstrip_blocks=True, autoescape=True)

        template = env.get_template('sealed-secret.yaml')

        kubernetesObject = template.render(sealedsecretName=sName,
                                           sealedsecretNamespace=sNamespace,
                                           encryptedSecret=sealedSecret[0])
                                           
        return render_template('output.html', sealedSecret=sealedSecret[0],
                               kubernetesObject=kubernetesObject)

    return render_template('main.html', form=form)

# Main Method
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)

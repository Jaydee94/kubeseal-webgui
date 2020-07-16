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
import json_log_formatter

# Setup JSON handler for logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler(stream=sys.stdout)
json_handler.setFormatter(formatter)

# Configure logging settings
log = logging.getLogger("kubseal-webgui")
log.addHandler(json_handler)
log.setLevel(logging.INFO)

# Set flask werkzeug logger to ERROR
flasklogger = logging.getLogger('werkzeug')
flasklogger.addHandler(json_handler)
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
    encryptedDataKeyName = TextField('EncryptedData key name:', validators=[InputRequired()])


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
        sEncryptedDataKeyName = form.encryptedDataKeyName.data
        sealedSecret = Kubeseal.kubectlCMD(cltSecret, sNamespace, sName)
        log.info('Created SealedSecret [%s] for namespace [%s] with encrypted data key name: [%s].', sName, sNamespace,sEncryptedDataKeyName)

        # Load data from YAML into Python dictionary
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('./templates'),
                                 trim_blocks=True, lstrip_blocks=True, autoescape=True)

        template = env.get_template('sealed-secret.yaml')

        kubernetesObject = template.render(sealedsecretName=sName,
                                           sealedsecretNamespace=sNamespace,
                                           encryptedSecret=sealedSecret[0],
                                           secretKeyName=sEncryptedDataKeyName)

        return render_template('output.html', sealedSecret=sealedSecret[0],
                               kubernetesObject=kubernetesObject)

    return render_template('main.html', form=form)

# Main Method
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)

from flask import Flask, render_template
from flask_wtf import FlaskForm 
from wtforms import TextField
from wtforms.validators import InputRequired
from flask_bootstrap import Bootstrap
from kubeseal import Kubeseal
from environmentvars import environmentVariables
from htmlhelper import HTMLHelper
import sys
import subprocess

app = Flask(__name__)
Bootstrap(app)
app.config['SECRET_KEY'] = 'SjdnUends821Jsdlkvxh391ksdODnejdDw'


# Defining the form
class KubsealForm(FlaskForm):
    cleartextSecret = TextField('Klartext-Secret:', validators=[InputRequired()])
    secretName = TextField('Secret-Name:', validators=[InputRequired()])
    secretNamespace = TextField('Secret-Namespace:', validators=[InputRequired()])            

# Main Page
@app.route("/", methods=['GET', 'POST'])
def run_kubeseal():
    form = KubsealForm()

    if form.validate_on_submit():
        html = HTMLHelper()
        cltSecret = form.cleartextSecret.data
        sName = form.secretName.data
        sNamespace = form.secretNamespace.data

        output = html.getHeaderForm()
        output += '<h2> {}'.format(cltSecret)
        output += html.getSubmitForm()

        return output

    return render_template('main.html', form=form)

# Main Method 
if __name__ == '__main__':

    requiredEnvironmentVariables = ['SEALED_SECRETS_CONTROLLER_NAME',
                                    'SEALED_SECRETS_CONTROLLER_NAMESPACE',
                                    'KUBERNETES_LOGIN_TOKEN']
    env = environmentVariables()

    if env.checkRequiredEnvironmentVariables(requiredEnvironmentVariables) == True:
        test = subprocess.Popen(["kubectl"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, errors = test.communicate()
        output
        app.run(debug = True)
    else:
        sys.exit('Stopping program because of missing environment variables.')

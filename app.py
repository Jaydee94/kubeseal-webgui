from flask import Flask, render_template, flash, request
from wtforms import TextField, TextAreaField, validators, StringField, SubmitField
from flask_wtf import FlaskForm
from kubeseal import kubeseal
from environmentvars import environmentVariables
import sys

DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'SjdnUends821Jsdlkvxh391ksdODnejdDw'

class KubsealForm(FlaskForm):
    cleartextSecret = TextField('Klartext-Secret:', validators=[validators.required()])
    secretName = TextField('Secret-Name:', validators=[validators.required()])
    secretNamespace = TextField('Secret-Namespace:', validators=[validators.required()])

@app.route("/", methods=['GET', 'POST'])
def run_kubeseal():
    form = KubsealForm(request.form)

    return render_template('main.html', form=form)

  
@app.route('/output',methods = ['GET', 'POST'])

def method_Handler():
    if request.method == 'POST':
        return kubeseal_output()
    else:
        return invalid_method_page()

def kubeseal_output():
    ks = kubeseal('controller', 'namespace')
#    Todo: Output the finally Sealed-Secret
    output = ks.getControllername()
    return render_template('output.html', output=output) 

def invalid_method_page():
    return render_template('invalid_method.html')
  
if __name__ == '__main__':

    requiredEnvironmentVariables = ['SEALED_SECRETS_CONTROLLER_NAME',
                                    'SEALED_SECRETS_CONTROLLER_NAMESPACE',
                                    'KUBERNETES_LOGIN_TOKEN']

    if environmentVariables().checkRequiredEnvironmentVariables(requiredEnvironmentVariables) == True:
        app.run(debug = True)
    else:
        sys.exit('Stopping program because of missing environment variables.')
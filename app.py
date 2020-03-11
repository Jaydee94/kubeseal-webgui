from flask import Flask, render_template, request, flash  
from forms import KubesealForm
from kubeseal import kubeseal
from environmentvars import environmentVariables
import sys

app = Flask(__name__)  
app.secret_key = 'IOBHOqdsbsdaojub'  
  
@app.route('/', methods = ['GET', 'POST'])  
def kubeseal_input():  
   form = KubesealForm()  
   if form.validate() == False:  
      flash('All fields are required.')  
   return render_template('main.html', form = form)  
  
  
  
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
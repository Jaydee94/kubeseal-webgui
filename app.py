from flask import Flask, render_template, request, flash  
from forms import KubesealForm
from kubeseal import kubeseal
app = Flask(__name__)  
app.secret_key = '0iewhdpeowubdeoibw'  
  
@app.route('/', methods = ['GET', 'POST'])  
def kubeseal_input():  
   form = KubesealForm()  
   if form.validate() == False:  
      flash('All fields are required.')  
   return render_template('contact.html', form = form)  
  
  
  
@app.route('/output',methods = ['GET','POST'])  
def kubeseal_output():
    ks = kubeseal('controller', 'namespace')
    output = ks.getControllername
    return render_template('output.html',output=output) 
  
if __name__ == '__main__':  
   app.run(debug = True)  

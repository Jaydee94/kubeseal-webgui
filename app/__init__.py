from flask import Flask
from flask_restful import Api, Resource, reqparse
from os import urandom
import subprocess

class KubesealService(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('secret')
        parser.add_argument('namespace')
        parser.add_argument('secrets', action='append')
        
        args = parser.parse_args()
        response_data = {'namespace': args['namespace'], 'secret': args['secret'], 'sealedSecrets': ['kauder', 'welsch']}

        return response_data

def run_kubeseal(cleartextSecrets, secretNamespace, secretName):
    sealedSecrets = []
    for cleartextSecret in cleartextSecrets:
        runKubesealCommand = "echo -n '%s' | /kubeseal-webgui/kubeseal --raw --from-file=/dev/stdin --namespace %s --name %s --cert /kubeseal-webgui/cert/kubeseal-cert.pem" % (cleartextSecret, secretNamespace, secretName)
        kubesealSubprocess = subprocess.Popen([runKubesealCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = kubesealSubprocess.communicate()

        if error:
            raise RuntimeError(f"Error in run_kubeseal: {error}")

        sealedSecret = output.decode('utf-8').split('\n')
        sealedSecrets.append(sealedSecret)
    return sealedSecrets

def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = urandom(24)

    api = Api(app)
    api.add_resource(KubesealService, '/secrets')

    return app
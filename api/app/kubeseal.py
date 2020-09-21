from flask import Flask
from flask import got_request_exception
from flask_restful import Api, Resource, reqparse, abort
import logging
import subprocess

LOGGER = logging.getLogger(__name__)

class KubesealEndpoint(Resource):
    def get(self):
        return "Use POST HTTP request to seal secret."

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('secret')
        parser.add_argument('namespace')
        parser.add_argument('secrets', action='append')
        args = parser.parse_args()

        try: 
            response = run_kubeseal(args['secrets'], args['namespace'], args['secret'])
        except RuntimeError as error:
            abort(500)
        except ValueError as error:
            abort(500)
        return response

def run_kubeseal(cleartextSecrets, secretNamespace, secretName):
    if secretNamespace == None or secretNamespace == "":
        error_message = "secretNamespace was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    if secretName == None or secretName == "":
        error_message = "secretNamespace was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    sealedSecrets = []
    for cleartextSecret in cleartextSecrets:
        sealedSecret = run_kubeseal_command(cleartextSecret, secretNamespace, secretName)
        sealedSecrets.append(sealedSecret)
    return sealedSecrets

def run_kubeseal_command(cleartextSecret, secretNamespace, secretName):
    runKubesealCommand = f"echo -n '{cleartextSecret}' | /kubeseal-webgui/kubeseal --raw --from-file=/dev/stdin --namespace {secretNamespace} --name {secretName} --cert /kubeseal-webgui/cert/kubeseal-cert.pem"
    kubesealSubprocess = subprocess.Popen([runKubesealCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = kubesealSubprocess.communicate()

    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    sealedSecret = output.decode('utf-8').split('\n')
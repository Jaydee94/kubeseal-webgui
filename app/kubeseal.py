from flask import Flask
from flask import got_request_exception
from flask_restful import Api, Resource, reqparse, abort
import logging
import subprocess

kubeseal_logger = logging.getLogger("kubeseal-webgui")

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
            kubeseal_logger.error(error)
            abort(500)
        except ValueError as error:
            kubeseal_logger.error(error)
            abort(500)
        return response

def run_kubeseal(cleartextSecrets, secretNamespace, secretName):
    if secretNamespace == None or secretNamespace == "":
        raise ValueError("secretNamespace was not given")

    if secretName == None or secretName == "":
        raise ValueError("secretNamespace was not given")

    sealedSecrets = []
    for cleartextSecret in cleartextSecrets:
        sealedSecret = run_kubeseal_command(cleartextSecret, secretNamespace, secretName)
        sealedSecrets.append(sealedSecret)
    return sealedSecrets

def run_kubeseal_command(cleartextSecret, secretNamespace, secretName):
    runKubesealCommand = "echo -n '%s' | /kubeseal-webgui/kubeseal --raw --from-file=/dev/stdin --namespace %s --name %s --cert /kubeseal-webgui/cert/kubeseal-cert.pem" % (cleartextSecret, secretNamespace, secretName)
    kubesealSubprocess = subprocess.Popen([runKubesealCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = kubesealSubprocess.communicate()

    if error:
        raise RuntimeError(f"Error in run_kubeseal: {error}")

    sealedSecret = output.decode('utf-8').split('\n')
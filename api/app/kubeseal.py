from flask import Flask, request
from flask import got_request_exception
from flask_restful import Api, Resource, reqparse, abort

import logging
import subprocess
import json
import base64

LOGGER = logging.getLogger("kubeseal-webgui")

class KubesealEndpoint(Resource):
    def get(self):
        return "Use POST HTTP request to seal secret."

    def post(self):
        if request.json is None:
            raise RuntimeError("JSON Body was empty. Seal Request is required.")
        sealing_request = request.json
        LOGGER.info(sealing_request['secrets'])

        try: 
            response = run_kubeseal(sealing_request['secrets'], sealing_request['namespace'], sealing_request['secret'])
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
        error_message = "secretName was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    # TODO assure that cleartextSecretTuple is list of dict

    sealedSecrets = []
    for cleartextSecretTuple in cleartextSecrets:
        sealedSecret = run_kubeseal_command(cleartextSecretTuple, secretNamespace, secretName)
        sealedSecrets.append(sealedSecret)
    return sealedSecrets

def run_kubeseal_command(cleartextSecretTuple, secretNamespace, secretName):
    LOGGER.info(f"Sealing secret '{secretName}.{cleartextSecretTuple['key']}' for namespace '{secretNamespace}'.")
    cleartextSecret = cleartextSecretTuple['value']
    decodedSecret = base64.decodestring(cleartextSecret) 

    runKubesealCommand = f"echo -n '{decodedSecret}' | /kubeseal-webgui/kubeseal --raw --from-file=/dev/stdin --namespace {secretNamespace} --name {secretName} --cert /kubeseal-webgui/cert/kubeseal-cert.pem"
    kubesealSubprocess = subprocess.Popen([runKubesealCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = kubesealSubprocess.communicate()

    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    sealedSecret = "".join(output.decode('utf-8').split('\n'))
    return { "key": cleartextSecretTuple['key'], "value": sealedSecret }
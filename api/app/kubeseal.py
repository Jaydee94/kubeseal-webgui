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

def run_kubeseal(cleartext_secrets, secret_namespace, secret_name):
    if secret_namespace is None or secret_namespace == "":
        error_message = "secret_namespace was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    if secret_name is None or secret_name == "":
        error_message = "secret_name was not given"
        LOGGER.error(error_message)
        raise ValueError(error_message)

    # TODO assure that cleartext_secrets is list of dictionaries

    sealed_secrets = []
    for cleartext_secret_tuple in cleartext_secrets:
        sealed_secret = run_kubeseal_command(cleartext_secret_tuple, secret_namespace, secret_name)
        sealed_secrets.append(sealed_secret)
    return sealed_secrets

def run_kubeseal_command(cleartext_secret_tuple, secret_namespace, secret_name):
    LOGGER.info(f"Sealing secret '{secret_name}.{cleartext_secret_tuple['key']}' for namespace '{secret_namespace}'.")
    cleartext_secret = decode_base64_string(cleartext_secret_tuple['value'])
    exec_kubeseal_command = f"echo -n '{cleartext_secret}' | /kubeseal-webgui/kubeseal --raw --from-file=/dev/stdin --namespace {secret_namespace} --name {secret_name} --cert /kubeseal-webgui/cert/kubeseal-cert.pem"
    kubeseal_subprocess = subprocess.Popen([exec_kubeseal_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = kubeseal_subprocess.communicate()

    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    sealed_secret = "".join(output.decode('utf-8').split('\n'))
    return {"key": cleartext_secret_tuple['key'], "value": sealed_secret}

def decode_base64_string(base64_string_message):
    base64_bytes = base64_string_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode('ascii')

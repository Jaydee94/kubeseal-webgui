from os import environ
import sys

class environmentVariables:

    def checkRequiredEnvironmentVariables(self, variables):
        passed = True
        for env in variables:
            if env in environ:
                continue
            else:
                sys.stdout.write('Environment variable %s not set!\n'%(env))
                passed = False
        return passed

    @staticmethod
    def getSealedSecretsControllerName():
        return environ.get('SEALED_SECRETS_CONTROLLER_NAME')

    @staticmethod
    def getSealedSecretsControllerNamespace():
        return environ.get('SEALED_SECRETS_CONTROLLER_NAMESPACE')
    @staticmethod
    def getKubernetesLoginToken():
        return environ.get('KUBERNETES_LOGIN_TOKEN')        

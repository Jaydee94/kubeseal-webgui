from os import environ

class environmentVariables:

    def getSealedSecretsControllerName():
        return environ.get('SEALED_SECRETS_CONTROLLER_NAME')

    def getSealedSecretsControllerNamespace():
        return environ.get('SEALED_SECRETS_CONTROLLER_NAMESPACE')

    def getKubernetesLoginToken():
        return environ.get('KUBERNETES_LOGIN_TOKEN')        

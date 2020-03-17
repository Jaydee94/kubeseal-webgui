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
    def getKubesealCert():
        return environ.get('KUBESEAL_CERT')        

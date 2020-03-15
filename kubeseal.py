from os import environ
import subprocess
from environmentvars import environmentVariables

env = environmentVariables()
class Kubeseal:
      
  @staticmethod
  def getSealedSecretsControllerNamespace():
    return env.getSealedSecretsControllerNamespace()
  
  @staticmethod
  def getSealedSecretsControllerName():
    return env.getSealedSecretsControllerName()

  def kubectlCMD():
    test = subprocess.Popen(["echo -n foo | kubeseal --raw --from-file=/dev/stdin --namespace bar --name mysecret --controller-name sealed-secrets --controller-namespace sealed-secrets"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, errors = test.communicate()
    return output.decode('utf-8').split('\n')
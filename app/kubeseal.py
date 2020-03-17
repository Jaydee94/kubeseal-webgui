from os import environ
import subprocess
from environmentvars import environmentVariables

env = environmentVariables()
class Kubeseal:

  @staticmethod
  def kubectlCMD(clearSecret, secretNamespace, secretName):
    command = "echo -n %s | kubeseal --raw --from-file=/dev/stdin --namespace %s --name %s --cert /app/kubeseal-cert.pem" % (clearSecret, secretNamespace, secretName)
    test = subprocess.Popen([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, errors = test.communicate()
    return output.decode('utf-8').split('\n')
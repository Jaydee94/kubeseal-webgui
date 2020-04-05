from os import environ
import subprocess
class Kubeseal:

  @staticmethod
  def kubectlCMD(clearSecret, secretNamespace, secretName):
    command = "echo -n %s | /kubeseal-webgui/kubeseal --raw --from-file=/dev/stdin --namespace %s --name %s --cert /app/cert/kubeseal-cert.pem" % (clearSecret, secretNamespace, secretName)
    test = subprocess.Popen([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, errors = test.communicate()
    if errors:
      print(errors[0])
    return output.decode('utf-8').split('\n')

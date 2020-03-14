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

  def list_files():
    test = process = subprocess.run('kubectl', shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    out = test.stdout
    return  print(out)
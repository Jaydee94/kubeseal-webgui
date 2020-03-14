from os import environ
from environmentvars import environmentVariables

env = environmentVariables()

class kubeseal:
  def __init__(self, controllername, controllernamespace):
    self.controllername = controllername
    self.controllernamespace = controllernamespace


  def getControllername(self):
    return self.controllername

  def getControllernamespace(self):
    return self.controllernamespace

  @staticmethod
  def getSealedSecretsControllerNamespace():
    return env.getSealedSecretsControllerNamespace()
  
  @staticmethod
  def getSealedSecretsControllerName():
    return env.getSealedSecretsControllerName()
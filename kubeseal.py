class kubeseal:
  def __init__(self, controllername, controllernamespace):
    self.controllername = controllername
    self.controllernamespace = controllernamespace

  def getControllername(self):
    return str(self.controllername)
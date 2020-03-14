class HTMLHelper():
    headerForm = '''
    <div align="center">
    <h1> Your Sealed-Secret is: </h1>
    <br> <br>
    '''

    submitForm = '''
    <br><br><br><br>
    <form action="/" method="get">
    <input type="submit" value="Neues Secret Verschlüsseln">
    </form>
    </div>
    '''
    def getHeaderForm(self):
        return self.headerForm

    def getSubmitForm(self):
        return self.submitForm
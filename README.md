# Web-Gui for Bitnami Sealed-Secrets

This is a python based webapp for using Bitnami-Sealed-Secrets in a web-gui.

## Usage
Mount the public certificate of your sealed secrets controller to /app/cert/ in the docker container.

### Get Public-Cert from sealed-secrets controller. (Login to yout kubernetes cluster first)
`kubeseal --fetch-cert --controller-name <your-sealed-secrets-controller> --controller-namespace <sealed-secrets-controller-namespace> >kubeseal-cert.pem

# Web-Gui for Bitnami Sealed-Secrets

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Imageversion](https://img.shields.io/badge/Imageversion-1.0.0-orange)](https://hub.docker.com/repository/docker/kubesealwebgui/kubeseal-webgui)

## Description

This is a python based webapp for using Bitnami-Sealed-Secrets in a web-gui.

This app uses the kubseal binary of the original project: <https://github.com/bitnami-labs/sealed-secrets>

## Demo

![Farmers Market Finder Demo](demo/kubseal-demo-1.0.0.gif)

## Usage

Mount the public certificate of your sealed secrets controller to **/app/cert/kubeseal-cert.pem** in the docker container.

Please use the [helm chart](https://github.com/Jaydee94/kubeseal-webgui/tree/master/chart/kubeseal-webgui) which is included in this repository.

### Get Public-Cert from sealed-secrets controller

(Login to your kubernetes cluster first)

`kubeseal --fetch-cert --controller-name <your-sealed-secrets-controller> --controller-namespace <your-sealed-secrets-controller-namespace> > kubeseal-cert.pem`

#! /bin/sh

BASEDIR=$(dirname "$0")
docker build $BASEDIR/../ui/ -t ui:2.0.0 -t kubesealwebgui/ui:2.0.0
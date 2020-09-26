#! /bin/sh

BASEDIR=$(dirname "$0")
docker build $BASEDIR/../api/ -t api:2.0.0 -t kubesealwebgui/api:2.0.0
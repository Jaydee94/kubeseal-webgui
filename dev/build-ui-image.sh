#! /bin/sh

BASEDIR=$(dirname "$0")
docker build $BASEDIR/.. -f $BASEDIR/../Dockerfile.ui -t ui:2.1.0 -t kubesealwebgui/ui:2.1.0

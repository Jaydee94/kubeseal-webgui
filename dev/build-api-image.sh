#! /bin/sh

BASEDIR=$(dirname "$0")
docker build $BASEDIR/.. -f $BASEDIR/../Dockerfile.api -t api:2.1.0 -t kubesealwebgui/api:2.1.0

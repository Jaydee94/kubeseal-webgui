#! /bin/sh

BASEDIR=$(dirname "$0")
minikube start && eval $(minikube docker-env)

helm upgrade sealedsecret $BASEDIR/../chart/kubeseal-webgui/

$BASEDIR/build-api-image.sh
$BASEDIR/build-ui-image.sh

kubectl rollout restart deployment/sealedsecret-kubeseal-webgui

kubectl get all -n default
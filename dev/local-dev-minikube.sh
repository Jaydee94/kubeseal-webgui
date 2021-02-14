#! /bin/sh

BASEDIR=$(dirname "$0")
minikube start && eval $(minikube docker-env)

helm template kubesealwebgui  $BASEDIR/../chart/kubeseal-webgui/ | kubectl delete -f -

$BASEDIR/build-api-image.sh
$BASEDIR/build-ui-image.sh

helm template kubesealwebgui  $BASEDIR/../chart/kubeseal-webgui/ | kubectl apply -f -

sleep 2

NEW_POD=$(kubectl get pods --field-selector status.phase=Pending -o custom-columns=":metadata.name")
echo " "
echo "Use the following commands to locally port-forward to the kubesealwebgui pod"
echo "-------------------------------------------"
printf "kubectl port-forward ${NEW_POD} -p 5000:5000\n"
printf "kubectl port-forward ${NEW_POD} -p 8080:8080\n"
echo " "

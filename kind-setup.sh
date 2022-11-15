#!/bin/bash
# Set-Up a kind cluster with kubeseal and kubeseal-webgui
# The ui will listen on http:$(localhost:7180)

set -eo pipefail

cat <<EOF | kind create cluster --name chart-testing --wait 3m --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 7180
    protocol: TCP
  - containerPort: 443
    hostPort: 7143
    protocol: TCP
EOF
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets -n kube-system --set-string fullnameOverride=sealed-secrets-controller sealed-secrets/sealed-secrets
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Build, load and start image
docker build -t kubesealwebgui/api:snapshot -f Dockerfile.api .
docker build -t kubesealwebgui/ui:snapshot -f Dockerfile.ui .
kind load docker-image --name chart-testing kubesealwebgui/api:snapshot
kind load docker-image --name chart-testing kubesealwebgui/ui:snapshot

kubectl create namespace kubeseal-webgui

helm template \
    --release-name e2e-test \
    --create-namespace \
    --namespace kubeseal-webgui \
    --set api.image.tag=snapshot \
    --set api.url=http://$(hostname -f):7180 \
    --set autoFetchCertResources=null \
    --set image.pullPolicy=Never \
    --set ingress.enabled=true \
    --set ingress.hostname=$(hostname -f) \
    --set resources=null \
    --set sealedSecrets.autoFetchCert=true \
    --set ui.image.tag=snapshot \
    chart/kubeseal-webgui \
    | kubectl apply -f - --namespace kubeseal-webgui

kubectl wait --namespace kubeseal-webgui \
  --for=condition=ready pod \
  --selector=app=kubeseal-webgui \
  --timeout=90s

sleep 5

curl -vvv -D - -f http://$(hostname -f):7180

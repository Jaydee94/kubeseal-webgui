#!/bin/bash
# Set-Up a kind cluster with kubeseal and kubeseal-webgui
# The ui will listen on http:$(localhost:7180)

set -eo pipefail

API_URL="https://$(hostname -f):7143"

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
docker build -t ghcr.io/jaydee94/kubeseal-webgui/api:snapshot -f Dockerfile.api .
docker build -t ghcr.io/jaydee94/kubeseal-webgui/ui:snapshot -f Dockerfile.ui .
kind load docker-image --name chart-testing ghcr.io/jaydee94/kubeseal-webgui/api:snapshot
kind load docker-image --name chart-testing ghcr.io/jaydee94/kubeseal-webgui/ui:snapshot

kubectl create namespace kubeseal-webgui

helm template \
    --release-name e2e-test \
    --create-namespace \
    --namespace kubeseal-webgui \
    --set api.image.tag=snapshot \
    --set api.url="${API_URL}" \
    --set autoFetchCertResources=null \
    --set image.pullPolicy=Never \
    --set ingress.enabled=true \
    --set ingress.hostname="$(hostname -f)" \
    --set resources=null \
    --set sealedSecrets.autoFetchCert=true \
    --set ui.image.tag=snapshot \
    --set securityContext.runAsUser=1042 \
    chart/kubeseal-webgui \
    | kubectl apply -f - --namespace kubeseal-webgui

kubectl wait --namespace kubeseal-webgui \
  --for=condition=ready pod \
  --selector=app=kubeseal-webgui \
  --timeout=90s

for _i in {1..3}; do
    curl -i -k -D - -f "${API_URL}" ||
        sleep 5
done

kubectl create namespace e2e
strict_secret=$(
  echo '{"secret": "strict-secret", "namespace": "e2e", "scope": "strict", "secrets": [{"key": "a-secret","value": "YQ=="}]}' |
    curl -f -H 'content-type: application/json' -X POST -k --data @- "${API_URL}/secrets" |
    jq -r -s '.[0][] | select(.key=="a-secret") | "a-secret: " + .value')
namespace_secret=$(
  echo '{"namespace": "e2e", "scope": "namespace-wide", "secrets": [{"key": "a-secret","value": "YQ=="}]}' |
    curl -f -H 'content-type: application/json' -X POST -k --data @- "${API_URL}/secrets" |
    jq -r -s '.[0][] | select(.key=="a-secret") | "a-secret: " + .value')
cluster_secret=$(
  echo '{"scope": "cluster-wide", "secrets": [{"key": "different-secret","value": "YQ=="}]}' |
    curl -f -H 'content-type: application/json' -X POST -k --data @- "${API_URL}/secrets" |
    jq -r -s '.[0][] | select(.key=="different-secret") | "a-secret: " + .value')

cat <<EOF | kubectl apply -n e2e -f -
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: strict-secret
  namespace: e2e
  annotations: {  }
spec:
  encryptedData:
    ${strict_secret}
EOF


cat <<EOF | kubectl apply -n e2e -f -
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: namespace-secret
  namespace: e2e
  annotations: { sealedsecrets.bitnami.com/namespace-wide: "true" }
spec:
  encryptedData:
    ${namespace_secret}
EOF

cat <<EOF | kubectl apply -n e2e -f -
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: cluster-secret
  namespace: e2e
  annotations: { sealedsecrets.bitnami.com/cluster-wide: "true" }
spec:
  encryptedData:
    ${cluster_secret}
EOF

sleep 5

for secret_name in strict-secret namespace-secret cluster-secret; do
  echo -n "Testing ${secret_name} "
  test "$(kubectl get secret "${secret_name}" -n e2e \
  -o go-template --template '{{ index .data "a-secret" }}')" = "YQ==" ||
 { echo ERR; exit 1; } &&
 echo OK
done

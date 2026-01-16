#!/bin/bash
# Set-Up a kind cluster with kubeseal and kubeseal-webgui
# The ui will listen on http://localhost:7180

set -euo pipefail

# Configuration
readonly CLUSTER_NAME="chart-testing"
readonly NAMESPACE="kubeseal-webgui"
readonly E2E_NAMESPACE="e2e"
HOSTNAME_FQDN="$(hostname -f)"
readonly API_URL="https://${HOSTNAME_FQDN}:7143"
readonly TIMEOUT="90s"
readonly MAX_RETRIES=3
readonly RETRY_DELAY=5

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

wait_for_api() {
    local url="$1"
    local retries="$2"
    local delay="$3"
    
    for i in $(seq 1 "$retries"); do
        if curl -s -k -f "$url" > /dev/null 2>&1; then
            log_info "API is ready"
            return 0
        fi
        log_warn "Waiting for API (attempt $i/$retries)..."
        sleep "$delay"
    done
    
    log_error "API failed to become ready after $retries attempts"
    return 1
}

create_sealed_secret() {
    local name="$1"
    local namespace="$2"
    local scope="$3"
    local key="$4"
    local annotations="$5"
    
    local payload
    if [[ "$scope" == "strict" ]]; then
        payload="{\"secret\": \"$name\", \"namespace\": \"$namespace\", \"scope\": \"$scope\", \"secrets\": [{\"key\": \"$key\",\"value\": \"YQ==\"}]}"
    elif [[ "$scope" == "namespace-wide" ]]; then
        payload="{\"namespace\": \"$namespace\", \"scope\": \"$scope\", \"secrets\": [{\"key\": \"$key\",\"value\": \"YQ==\"}]}"
    else
        payload="{\"scope\": \"$scope\", \"secrets\": [{\"key\": \"$key\",\"value\": \"YQ==\"}]}"
    fi
    
    local encrypted_data
    encrypted_data=$(echo "$payload" | \
        curl -sf -H 'content-type: application/json' -X POST -k --data @- "${API_URL}/secrets" | \
        jq -r -s ".[0][] | select(.key==\"$key\") | \"$key: \" + .value")
    
    cat <<EOF | kubectl apply -n "$namespace" -f -
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: $name
  namespace: $namespace
  annotations: $annotations
spec:
  encryptedData:
    $encrypted_data
EOF
}

# Main script
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    log_info "Kind cluster '$CLUSTER_NAME' already exists, skipping creation"
else
    log_info "Creating kind cluster: $CLUSTER_NAME"
    cat <<EOF | kind create cluster --name "$CLUSTER_NAME" --wait 3m --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  ipFamily: dual
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
fi

log_info "Installing sealed-secrets controller"
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets 2>/dev/null || true
if helm list -n kube-system | grep -q "^sealed-secrets"; then
    log_info "Sealed-secrets already installed, skipping"
else
    helm install sealed-secrets -n kube-system \
        --set-string fullnameOverride=sealed-secrets-controller \
        sealed-secrets/sealed-secrets
fi

log_info "Installing ingress-nginx"
if kubectl get namespace ingress-nginx &>/dev/null; then
    log_info "Ingress-nginx already installed, skipping"
else
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
fi
kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout="$TIMEOUT"

log_info "Building Docker images in parallel"
docker build -t ghcr.io/jaydee94/kubeseal-webgui/api:snapshot -f Dockerfile.api . &
api_build_pid=$!
docker build -t ghcr.io/jaydee94/kubeseal-webgui/ui:snapshot -f Dockerfile.ui . &
ui_build_pid=$!

# Wait for both builds to complete
wait "$api_build_pid" || { log_error "API build failed"; exit 1; }
wait "$ui_build_pid" || { log_error "UI build failed"; exit 1; }
log_info "Docker images built successfully"

log_info "Loading images into kind cluster"
kind load docker-image --name "$CLUSTER_NAME" \
    ghcr.io/jaydee94/kubeseal-webgui/api:snapshot \
    ghcr.io/jaydee94/kubeseal-webgui/ui:snapshot

log_info "Creating namespace: $NAMESPACE"
kubectl create namespace "$NAMESPACE" 2>/dev/null || log_info "Namespace '$NAMESPACE' already exists"

log_info "Deploying kubeseal-webgui via Helm"
helm template \
    --release-name e2e-test \
    --create-namespace \
    --namespace "$NAMESPACE" \
    --set api.image.tag=snapshot \
    --set api.url="$API_URL" \
    --set autoFetchCertResources=null \
    --set image.pullPolicy=Never \
    --set ingress.enabled=true \
    --set ingress.hostname="$(hostname -f)" \
    --set resources=null \
    --set sealedSecrets.autoFetchCert=true \
    --set ui.image.tag=snapshot \
    --set securityContext.runAsUser=1042 \
    chart/kubeseal-webgui \
    | kubectl apply -f - --namespace "$NAMESPACE"

log_info "Restarting deployment to use new images"
kubectl rollout restart deployment/e2e-test-kubeseal-webgui -n "$NAMESPACE"

log_info "Waiting for kubeseal-webgui deployment to complete"
kubectl rollout status deployment/e2e-test-kubeseal-webgui -n "$NAMESPACE" --timeout="$TIMEOUT"

kubectl wait --namespace "$NAMESPACE" \
    --for=condition=ready pod \
    --selector=app=kubeseal-webgui \
    --timeout="$TIMEOUT"

log_info "Verifying API accessibility"
wait_for_api "$API_URL" "$MAX_RETRIES" "$RETRY_DELAY"

log_info "Creating test namespace: $E2E_NAMESPACE"
kubectl create namespace "$E2E_NAMESPACE" 2>/dev/null || log_info "Namespace '$E2E_NAMESPACE' already exists"

log_info "Creating sealed secrets for testing"
create_sealed_secret "strict-secret" "$E2E_NAMESPACE" "strict" "a-secret" "{  }"
create_sealed_secret "namespace-secret" "$E2E_NAMESPACE" "namespace-wide" "a-secret" "{ sealedsecrets.bitnami.com/namespace-wide: \"true\" }"
create_sealed_secret "cluster-secret" "$E2E_NAMESPACE" "cluster-wide" "a-secret" "{ sealedsecrets.bitnami.com/cluster-wide: \"true\" }"

log_info "Waiting for secrets to be unsealed"
sleep 5

log_info "Verifying unsealed secrets"
for secret_name in strict-secret namespace-secret cluster-secret; do
    if [[ "$(kubectl get secret "$secret_name" -n "$E2E_NAMESPACE" \
        -o go-template --template '{{ index .data "a-secret" }}')" == "YQ==" ]]; then
        log_info "Testing ${secret_name}: OK"
    else
        log_error "Secret $secret_name verification failed"
        exit 1
    fi
done

log_info "Verifying Dual Stack (IPv6) connectivity"
kubectl run curl-test --image=curlimages/curl --restart=Never --command -- sleep 3600
kubectl wait --for=condition=ready pod/curl-test --timeout="$TIMEOUT"

# Get Pod IPv6 Address
POD_NAME=$(kubectl get pod -n "$NAMESPACE" -l app=kubeseal-webgui -o jsonpath='{.items[0].metadata.name}')
POD_IPV6=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.status.podIPs[*].ip}' | tr ' ' '\n' | grep ':')

if [ -z "$POD_IPV6" ]; then
    log_error "Could not find IPv6 address for pod $POD_NAME"
    kubectl delete pod curl-test
    exit 1
fi

log_info "Testing IPv6 connectivity to Pod IP: [$POD_IPV6]:8080"
if kubectl exec curl-test -- curl -v -f -g -6 "http://[$POD_IPV6]:8080/namespaces"; then
    log_info "IPv6 Connectivity: OK"
else
    log_error "IPv6 Connectivity Failed"
    kubectl delete pod curl-test
    exit 1
fi
kubectl delete pod curl-test

log_info "Setup complete! Access the UI at: http://$(hostname -f):7180"

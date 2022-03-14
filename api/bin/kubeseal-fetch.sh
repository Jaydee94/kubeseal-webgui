#!/bin/sh -eu

: "${KUBESEAL_BINARY:=/kubeseal-webgui/bin/kubeseal}"
: "${KUBESEAL_CERT:=/kubeseal-webgui/cert/kubeseal-cert.pem}"
: "${KUBESEAL_CONTROLLER_NAME:=sealed-secrets-controller}"
: "${KUBESEAL_CONTROLLER_NAMESPACE:=kube-system}"

if test $# -gt 0; then
  KUBESEAL_CERT="$1"
fi

CERT_DIR=$(dirname "$KUBESEAL_CERT")

mkdir -p "$CERT_DIR"

env -C "$CERT_DIR" "${KUBESEAL_BINARY}" --fetch-cert \
  --controller-name "$KUBESEAL_CONTROLLER_NAME" \
  --controller-namespace "${KUBESEAL_CONTROLLER_NAMESPACE}" \
| tee "$KUBESEAL_CERT" >/dev/null

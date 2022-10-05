#!/bin/sh -eu

: "${HOST:=0.0.0.0}"
: "${PORT:=5000}"
: "${BASE_PATH:=/}"

case "${1:-}" in
  -*|'') : ;;
  uwsgi) shift ;;
  *) exec "$@" ;;
esac

set -- --http-socket "${HOST}:${PORT}" \
  --mount "${BASE_PATH}=kubeseal_webgui_api.run:app" \
  "$@"

exec uwsgi "$@"

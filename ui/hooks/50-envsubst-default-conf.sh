#!/bin/sh -eu

: "${PUBLIC_HOST:=localhost}"
: "${PUBLIC_PORT:=8080}"
: "${PUBLIC_SCHEME:=http}"
: "${API_HOST:=localhost}"
: "${API_PORT:=5000}"
: "${API_SCHEME:=http}"

sed_file() {
  local target
  local parent
  local buffer

  target="$1"
  parent=$(dirname "$1")
  shift

  # `test -w` only checks permission bits against the current user; it does
  # not detect a filesystem that is mounted read-only (e.g. a Kubernetes
  # readOnlyRootFilesystem), where the bits can look writable but any actual
  # write fails. Guard every write attempt below so that outcome degrades to
  # a warning instead of aborting this script (and, under `set -e`, the
  # whole nginx entrypoint) with an unhandled error.
  if ! test -w "$target"; then
    echo "File (${target}) is not writable; skipping var expansion" 1>&2
  elif ! test -w "$parent"; then
    buffer=$(mktemp) || {
      echo "File (${target}) is not writable; skipping var expansion" 1>&2
      return 0
    }

    if ! sed "$@" "$target" > "$buffer" 2>/dev/null || ! cat "$buffer" > "$target" 2>/dev/null; then
      echo "File (${target}) is not writable; skipping var expansion" 1>&2
    fi
    rm -f "$buffer"
  else
    # inplace edit needs write permissions to the directory as well
    sed -i "$@" "$target" 2>/dev/null || echo "File (${target}) is not writable; skipping var expansion" 1>&2
  fi
}

sed_file /etc/nginx/conf.d/default.conf \
  -e "s;http://localhost:5000;${API_SCHEME}://${API_HOST}:${API_PORT};"

sed_file /usr/share/nginx/html/config.json \
    -e "s;http://localhost:5000;${PUBLIC_SCHEME}://${PUBLIC_HOST}:${PUBLIC_PORT};"

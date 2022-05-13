#!/bin/sh -eu

: "${PUBLIC_HOST:=localhost}
: "${PUBLIC_PORT:=8080}
: "${PUBLIC_SCHEME:=http}
: "${API_HOST:=localhost}
: "${API_PORT:=5000}
: "${API_SCHEME:=http}

sed_file() {
  local target
  local parent
  local buffer

  target="$1"
  parent=$(dirname "$1")
  shift

  if ! test -w "$target"; then
    echo "File (${target}) is not writable; skipping var expansion" 1>&2
  elif ! test -w "$parent"; then
    buffer=$(mktemp)

    sed "$@" "$target" > "$buffer"
    cat "$buffer" > "$target"
    rm "$buffer"
  else
    # inplace edit needs write permissions to the directory as well
    sed -i "$@" "$target"
  fi
}

sed_file /etc/nginx/conf.d/default.conf \
  -e "s;http://localhost:5000;${API_SCHEME}://${API_HOST}:${API_PORT};"

sed_file /usr/share/nginx/html/config.json \
    -e "s;http://localhost:5000;${PUBLIC_SCHEME}://${PUBLIC_HOST}:${PUBLIC_PORT};"

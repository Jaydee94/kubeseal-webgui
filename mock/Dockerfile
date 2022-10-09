FROM debian:latest as deps

ARG KUBESEAL_VERSION=0.18.5
ENV KUBESEAL_BINARY=/deps/kubeseal \
    PRIVATEKEY=/dev/null \
    PUBLICKEY=/deps/cert.pem

WORKDIR /deps

RUN apt update && apt install -y openssl curl
RUN openssl req -x509 -days 365 -nodes -newkey rsa:4096 -keyout "$PRIVATEKEY" -out "$PUBLICKEY" -subj "/CN=sealed-secret/O=sealed-secret"
RUN curl -Lsf -o - "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz" | \
    tar -xzf - && \
    chmod 0755 "${KUBESEAL_BINARY}"

FROM python:3.9-slim

ARG KUBESEAL_VERSION=0.18.5

RUN pip install --no-cache-dir \
    install 'uvicorn'

ENV UVICORN_PORT=5000 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_NO_DATE_HEADER=1 \
    UVICORN_NO_SERVER_HEADER=1 \
    KUBESEAL_BINARY=/tmp/kubeseal

WORKDIR /usr/src/kswg_mock

COPY . .
RUN pip install --no-cache-dir .

COPY --from=deps /deps/* /tmp/

USER daemon

CMD [ "uvicorn", "kswg_mock.app:app" ]

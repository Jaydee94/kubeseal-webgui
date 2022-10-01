FROM python:3.9-alpine

ARG KUBESEAL_VERSION=0.18.5

RUN pip install --no-cache-dir \
    install 'uvicorn'

ENV UVICORN_PORT=5000 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_NO_DATE_HEADER=1 \
    UVICORN_NO_SERVER_HEADER=1 \
    KUBESEAL_BINARY=/tmp/kubeseal

WORKDIR /usr/src/kswg_mock
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY test_cert.pem /tmp/cert.pem

WORKDIR /tmp

RUN wget -q "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz" && \
    tar -xzvf kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz && \
    chmod 0755 "${KUBESEAL_BINARY}"

WORKDIR /usr/src/kswg_mock

USER daemon

CMD [ "uvicorn", "kswg_mock.app:app" ]

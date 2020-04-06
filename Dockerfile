FROM abihf/wget AS Downloader
RUN wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.11.0/kubeseal-linux-amd64 && \
    mv kubeseal-linux-amd64 /tmp/kubeseal

FROM python:3.8-alpine3.11
RUN mkdir /kubeseal-webgui
COPY --from=Downloader /tmp/kubeseal /kubeseal-webgui
COPY app/ /kubeseal-webgui/
COPY requirements.txt /kubeseal-webgui/

WORKDIR /kubeseal-webgui

RUN pip install -r requirements.txt

RUN chown -R 1001:1001 /kubeseal-webgui && \
    chmod +x /kubeseal-webgui/app.py && \
    chmod +x /kubeseal-webgui/kubeseal

USER 1001

CMD [ "python", "./kubeseal-webgui/app.py" ]



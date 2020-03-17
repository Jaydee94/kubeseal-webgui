FROM abihf/wget AS Downloader
RUN wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.11.0/kubeseal-linux-amd64 && \
    mv kubeseal-linux-amd64 /tmp/kubeseal

FROM python:3.8-alpine3.11
RUN mkdir /app
COPY --from=Downloader /tmp/kubeseal /app
COPY app/ /app/

RUN pip install flask flask_wtf wtforms wtforms.validators flask_bootstrap

RUN chown -R 1001:1001 /app &&\
    chmod +x /app/app.py &&\
    chmod +x /app/kubeseal

USER 1001
WORKDIR /app

CMD [ "python", "./app.py" ]



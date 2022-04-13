FROM python:3.9-alpine

RUN pip install --no-cache-dir \
      install 'uvicorn'

ENV UVICORN_PORT=5080 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_NO_DATE_HEADER=1 \
    UVICORN_NO_SERVER_HEADER=1

WORKDIR /usr/src/kswg_mock
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER daemon

CMD [ "uvicorn", "kswg_mock.app:app" ]

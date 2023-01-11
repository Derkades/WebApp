FROM python:3.11

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir /app
WORKDIR /app

COPY ./src .
COPY ./docker/entrypoint.sh .
COPY ./docker/manage /usr/local/bin

RUN cat ./static/js/player/*.js > ./static/js/player/packed.js && \
    pybabel compile -d translations

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["./entrypoint.sh"]

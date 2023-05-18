FROM python:3.11

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

COPY ./docker/entrypoint.sh /entrypoint.sh
COPY ./docker/manage /usr/local/bin
COPY ./src /app

WORKDIR /app

RUN pybabel compile -d translations

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]

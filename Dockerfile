FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r /requirements.txt

COPY ./docker/entrypoint.sh /entrypoint.sh
COPY ./docker/manage /usr/local/bin
COPY ./src /app

WORKDIR /app

RUN PYTHONDONTWRITEBYTECODE=1 pybabel compile -d translations

ENV PYTHONUNBUFFERED 1
ENV MUSIC_MUSIC_DIR /music
ENV MUSIC_DATA_PATH /data

# For fontconfig: https://wiki.archlinux.org/title/Font_configuration#Fontconfig_configuration
ENV XDG_CACHE_HOME /tmp

USER 1000

ENTRYPOINT ["/entrypoint.sh"]

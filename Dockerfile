FROM python:3-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

RUN pip install yt-dlp flask

RUN mkdir /app

COPY ./app.py /app/
COPY ./templates /app/templates

WORKDIR /app

ENTRYPOINT ["flask", "run", "--host", "0.0.0.0"]

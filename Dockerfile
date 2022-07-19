FROM python:3-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

RUN pip install yt-dlp flask bs4 requests

RUN mkdir /app

COPY ./app.py /app/
COPY ./raphson.png /app/
COPY ./templates /app/templates

WORKDIR /app

ENTRYPOINT ["flask", "run", "--host", "0.0.0.0"]

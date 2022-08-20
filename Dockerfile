FROM python:3

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN pip install yt-dlp flask bs4 requests Pillow gunicorn

RUN mkdir /app

COPY *.py raphson.png script.js style.css /app/
COPY ./templates /app/templates
COPY ./assets /app/assets

WORKDIR /app

# ENTRYPOINT ["flask", "run", "--host", "0.0.0.0"]
ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "4", "--threads", "4", "app"]

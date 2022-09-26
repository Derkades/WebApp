FROM python:3

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir /app
WORKDIR /app

COPY ./src .

# TODO Find a better way to make '/app/static/.webassets-cache' etc others writable
RUN chmod -R 777 /app/static

RUN pybabel compile -d translations

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["./entrypoint.sh"]

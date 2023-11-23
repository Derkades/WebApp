FROM python:3.12-slim as base

FROM base as ffmpeg

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget bzip2 g++ make nasm pkg-config libopus-dev && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /build && \
    cd /build && \
    wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
    tar xjf ffmpeg-snapshot.tar.bz2 && \
    rm ffmpeg-snapshot.tar.bz2

RUN cd /build/ffmpeg && \
    ./configure \
        --prefix="/build/ffmpeg" \
        --extra-cflags="-I/build/ffmpeg/include" \
        --extra-ldflags="-L/build/ffmpeg/lib" \
        --extra-libs="-lpthread -lm" \
        --ld="g++" \
        --enable-libopus \
        --disable-ffplay \
        --disable-doc \
        --disable-network \
        --disable-indevs \
        --disable-outdevs \
        --disable-bsfs \
        --disable-protocols \
        --enable-protocol=file \
        --disable-decoders --disable-encoders \
        --enable-decoder=libopus --enable-encoder=libopus  \
        --enable-decoder=mp3 \
        --enable-decoder=aac --enable-encoder=aac \
        --enable-decoder=flac \
        --enable-decoder=pcm_s16le \
        --enable-decoder=mjpeg --disable-decoder=mjpeg \
        --disable-filters \
        --enable-filter=loudnorm \
        --enable-filter=aresample \
        && \
    make -j8

FROM base

RUN apt-get update && \
    apt-get install -y --no-install-recommends libopus0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r /requirements.txt

COPY --from=ffmpeg /build/ffmpeg/ffmpeg /usr/local/bin \
                   /build/ffmpeg/ffprobe /usr/local/bin

# Ensure ffmpeg works
RUN ffmpeg --help > /dev/null

COPY ./docker/entrypoint.sh /entrypoint.sh
COPY ./docker/manage /usr/local/bin
COPY ./app /app

RUN PYTHONDONTWRITEBYTECODE=1 pybabel compile -d app/translations

ENV PYTHONUNBUFFERED 1
ENV MUSIC_MUSIC_DIR /music
ENV MUSIC_DATA_PATH /data

ENTRYPOINT ["/entrypoint.sh"]

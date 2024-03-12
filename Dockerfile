FROM python:3.12-slim as base

FROM base as ffmpeg-build

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget bzip2 g++ make nasm pkg-config libopus-dev libwebp-dev zlib1g-dev&& \
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
        --extra-libs="-lm" \
        --ld="g++" \
        # External libraries
        --enable-libopus \
        --enable-libwebp \
        # Required for PNG
        --enable-zlib \
        # Configuration options
        --disable-autodetect \
        # Program options
        --disable-ffplay \
        # Documentation options
        --disable-doc \
        # Component options
        --disable-avdevice \
        --disable-network \
        # Individual component options
        --disable-everything \
        --enable-protocol=file \
        --enable-decoder=libopus \
        --enable-decoder=mp3 \
        --enable-decoder=aac \
        --enable-decoder=flac \
        --enable-decoder=vorbis \
        --enable-decoder=pcm_s16le \
        --enable-decoder=mjpeg  \
        --enable-decoder=webp \
        --enable-decoder=png \
        --enable-encoder=libopus \
        --enable-encoder=aac \
        --enable-encoder=libwebp \
        --enable-encoder=pcm_s16le \
        --enable-decoder=alac \
        --enable-demuxer=aac \
        --enable-demuxer=flac \
        --enable-demuxer=mjpeg \
        --enable-demuxer=matroska \
        --enable-demuxer=mp3 \
        --enable-demuxer=ogg \
        --enable-demuxer=pcm_s16le \
        --enable-demuxer=wav \
        --enable-demuxer=webm \
        --enable-demuxer=image_png_pipe \
        --enable-demuxer=image_jpeg_pipe \
        --enable-demuxer=image_webp_pipe \
        --enable-demuxer=mov \
        --enable-muxer=aac \
        --enable-muxer=flac \
        --enable-muxer=mjpeg \
        --enable-muxer=matroska \
        --enable-muxer=matroska_audio \
        --enable-muxer=mp3 \
        --enable-muxer=ogg \
        --enable-muxer=wav \
        --enable-muxer=webm \
        --enable-muxer=webp \
        --enable-muxer=ipod \
        --enable-muxer=null \
        --enable-filter=loudnorm \
        --enable-filter=aresample \
        --enable-filter=scale \
        --enable-filter=crop \
        && \
    make -j8

###############################################################################

FROM base AS base-pip

COPY requirements.txt /
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r /requirements.txt

###############################################################################

FROM base-pip AS dev

# FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends libopus0 libwebp7 zlib1g && \
    rm -rf /var/lib/apt/lists/*
COPY --from=ffmpeg-build /build/ffmpeg/ffmpeg  /usr/local/bin \
                         /build/ffmpeg/ffprobe /usr/local/bin

COPY ./docker/entrypoint-dev.sh /entrypoint.sh
COPY ./docker/manage-dev.sh /usr/local/bin/manage

COPY ./app ./app
COPY mp.py .

ENV PYTHONUNBUFFERED 1
ENV MUSIC_MUSIC_DIR /music
ENV MUSIC_DATA_PATH /data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["start", "--host", "0.0.0.0", "--dev"]

###############################################################################

FROM base-pip AS pyinstaller

RUN apt-get update && \
    apt-get install -y --no-install-recommends binutils && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyinstaller

RUN mkdir /build
WORKDIR /build

COPY ./app ./app
COPY mp.py .

RUN pybabel compile -d app/translations

RUN pyinstaller mp.py \
        --hidden-import=gunicorn.glogging \
        --hidden-import=gunicorn.workers.gthread \
        --add-data=app/migrations:./app/migrations \
        --add-data=app/sql:./app/sql \
        --add-data=app/static:./app/static \
        --add-data=app/templates:./app/templates \
        --add-data=app/translations:./app/translations

###############################################################################

FROM debian:bookworm-slim as prod

# FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends libopus0 libwebp7 zlib1g && \
    rm -rf /var/lib/apt/lists/*
COPY --from=ffmpeg-build /build/ffmpeg/ffmpeg  /usr/local/bin \
                         /build/ffmpeg/ffprobe /usr/local/bin

COPY ./docker/entrypoint-prod.sh /entrypoint.sh
COPY ./docker/manage-prod.sh /usr/local/bin/manage

COPY --from=pyinstaller /build/dist/mp /mp

ENV PYTHONUNBUFFERED 1
ENV MUSIC_MUSIC_DIR /music
ENV MUSIC_DATA_DIR /data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["start", "--host", "0.0.0.0", "--dev"]

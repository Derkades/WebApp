FROM python:3.12-slim-bookworm AS base

FROM base AS ffmpeg-build

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget bzip2 g++ make nasm pkg-config libopus-dev libwebp-dev zlib1g-dev libmp3lame-dev

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
        --enable-libmp3lame \
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
        --enable-encoder=mjpeg \
        --enable-encoder=libmp3lame \
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

# For later layer to copy
RUN mkdir /ffmpeg-libs && \
    cp -a /usr/lib/x86_64-linux-gnu/libopus.so* /ffmpeg-libs && \
    cp -a /usr/lib/x86_64-linux-gnu/libwebp.so* /ffmpeg-libs && \
    cp -a /usr/lib/x86_64-linux-gnu/libmp3lame.so* /ffmpeg-libs

# AcoustID fpcalc
# is also available via a debian package, but that pulls in lots of dependencies (like ffmpeg, which we already build ourselves)
RUN cd /build && \
    wget https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-linux-x86_64.tar.gz && \
    tar xzf chromaprint-fpcalc-1.5.1-linux-x86_64.tar.gz

###############################################################################

FROM base AS common

COPY docker/requirements.txt /
RUN PYTHONDONTWRITEBYTECODE=1 pip install --break-system-packages --no-cache-dir -r /requirements.txt

# FFmpeg
COPY --from=ffmpeg-build /build/ffmpeg/ffmpeg /build/ffmpeg/ffprobe /usr/local/bin/
COPY --from=ffmpeg-build /ffmpeg-libs /usr/lib/x86_64-linux-gnu

# AcoustID fpcalc
COPY --from=ffmpeg-build /build/chromaprint-fpcalc-1.5.1-linux-x86_64/fpcalc /usr/local/bin/

COPY ./docker/manage.sh /usr/local/bin/manage

ENV PYTHONUNBUFFERED=1
ENV MUSIC_MUSIC_DIR=/music
ENV MUSIC_DATA_PATH=/data

WORKDIR "/mp"

###############################################################################

FROM common AS prod

COPY ./raphson_mp /mp/raphson_mp

RUN PYTHONDONTWRITEBYTECODE=1 pybabel compile -d /mp/raphson_mp/translations

ENTRYPOINT ["python3", "-m", "raphson_mp"]
CMD ["start", "--host", "0.0.0.0"]

###############################################################################

FROM common AS dev

COPY ./docker/entrypoint-dev.sh /entrypoint-dev.sh

ENTRYPOINT ["/entrypoint-dev.sh"]
CMD ["start", "--host", "0.0.0.0", "--dev"]

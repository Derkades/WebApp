# Preparing for offline development

## Docker images

Download the python:3 base image locally: `docker pull python:3`. If you don't do this, buildx will attempt to pull the image very frequently while rebuilding, which won't work offline.

Then, build and start the container: `docker compose up --build`. Following builds will be cached, unless you change one of the `RUN` instructions in the `Dockerfile`.

## Music

Add some music to `./music`. Adding only a small amount is recommended. While online, start the web interface, enable all playlists and increase the queue size. This will ensure album art and lyrics are downloaded to the cache for all tracks.
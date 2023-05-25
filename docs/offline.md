# Offline mode

The music player has an 'offline mode'. In this mode, the application:

- Does not make any connections to the internet.
- Does not transcode audio or images, always uses high quality opus audio and webp images.
- Does not use a local music library, but synchronizes from a main music server. Any options related to the music library are not available.
- (TODO) Keeps a local history, which it submits to the main music server when an internet connection is available.

TODO: insert picture of music player in Tyrone

## Installation

To install the music player in offline mode, follow the [standard installation instructions](./installation.md) with one change; add the environment variable `MUSIC_OFFLINE_MODE: 1`.

## Synchronization

Run `docker compose exec music python3 offline_sync.py`.

It is safe to abort synchronization using Ctrl+C. When restarted, it will resume where it left off.

Note that only favorite playlists will be downloaded. About 5GB of disk space is used for every 1000 tracks.

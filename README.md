# WebApp

Music player for communities (hacker spaces, maker spaces).

## Development environment

```
docker compose up --build
```

## Production deployment

Prebuilt container image: `ghcr.io/danielkoomen/webapp`.

## Usage

### `MUSIC_MUSIC_DIR` (default `/music`)

This directory should contain one subdirectory for each person. Directory names may be prefixed with `Guest-` to mark the person as a guest. Place audio files in these person directories. Creating directories inside person directories is not supported at this time.

An example:

```
music
├── CB
│   ├── Sub Focus & Wilkinson - Ray Of Sun.mp3
│   ├── The Elite - Falling Angels (Official Video) _ Coone & Da Tweekaz & Hard Driver.mp3
│   ├── Toneshifterz - I Am Australian (Hardstyle) _ HQ Videoclip.mp3
├── DK
│   ├── 025 Midnight Oil - Beds Are Burning.mp3
│   ├── 061 Pink Floyd - Another Brick In The Wall.mp3
│   └── 078 Nena - Irgendwie irgendwo irgendwann (long version).mp3
├── Guest-RS
│   ├── Tom Misch & Yussef Dayes - Storm Before The Calm (feat. Kaidi Akinnibi) (Official Audio).webm
│   ├── U & ME - Alt J (Official Audio) [RMkxrJuxRsk].webm
│   └── Zes - Juniper [UNYiVK3Cl98].webm
├── Guest-WD
│   └── 08. Watercolors (feat. Dave Koz).mp3
└── JK
    ├── Aerosmith - Dream On.mp3
    ├── A spaceman came travelling.mp3
    └── A Warrior's Call.mp3
```

Don't worry about removing strings like "(Official Audio)" from song titles, these are automatically removed. If possible, do add the following metadata to each file: artist, album artist, album title, song title, album cover image.

### `MUSIC_CACHE_DIR` (default `/cache`)

This directory is used to store the result of time-consuming operations, like transcoding audio or web scraping for album art. It may be emptied at any time as long as the application is not running.

### `MUSIC_WEB_PASSWORD` (not set by default)

Set an optional password to access the web interface. Strongly recommended if exposed to the internet.

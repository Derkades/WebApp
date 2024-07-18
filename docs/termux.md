# Offline music player in Termux

## Installation

Install the F-Droid client from [f-droid.org](https://f-droid.org/F-Droid.apk).

Install "Termux" from F-Droid. Open Termux. You will be presented with a Linux terminal environment.

Install Git:
```
pkg install git
```

Clone repository:
```
git clone https://github.com/DanielKoomen/WebApp
```

Run installation script:
```
cd WebApp
termux/install
```

This will install Python and the required Python extensions.

## Sync music
```
cd WebApp
termux/sync
```

Note that only favorite playlists will be downloaded. Disliked tracks are not downloaded. About 5GB of storage space is used for every 1000 tracks.

## Start music player
```
cd WebApp
termux/start
```

Visit http://localhost:8080 in a web browser. Use Ctrl+C to stop the web server.

## Updating

Updates may introduce bugs. It is advisable that you do not update at a time where you need the music player to work.

1. Enter the correct directory.
2. Run `git pull` to download new source code.
3. If your previous update was before 2023-10-28, use the [migrations](./migrations.md) wiki page to update your database.
4. Run `termux/install` to update Python dependencies.

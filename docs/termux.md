# Offline music player in Termux

## Installation

Install an F-Droid client like [Droid-ify](https://f-droid.org/repo/com.looker.droidify_57.apk).

Install "Termux" from F-Droid. Open Termux. You will be presented with a Linux terminal environment.

Install Python and Git:
```
pkg install git python python-pip
```

Clone repository:
```
git clone https://github.com/DanielKoomen/WebApp
```

Install requirements:
```
cd WebApp
termux/install
```

## Sync music
```
cd WebApp
termux/sync
```

Note that only favorite playlists will be downloaded. About 5GB of disk space is used for every 1000 tracks.

## Start music player
```
cd WebApp
termux/start
```

Visit http://localhost:8080 in a web browser. Use Ctrl+C to stop the web server.

## Updating
1. Enter the correct directory.
2. Run `git pull` to download new source code.
3. Check the [migrations](./migrations.md) wiki page to see if there were any new database migrations since your previous update.
4. Run `termux/install` to ensure dependencies are up-to-date.

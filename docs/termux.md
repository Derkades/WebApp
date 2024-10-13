# Offline music player in Termux

## Installation

Install the F-Droid client from [f-droid.org](https://f-droid.org/F-Droid.apk).

Install "Termux" from F-Droid. Open Termux. You will be presented with a Linux terminal environment.

Install Git:
```
pkg install git
```

Install the `raphson-mp` package:
```
pip install raphson-mp
```

Create a script to start the music player with your arguments of choice. An example:

`./mp.sh`
```
python -m raphson_mp --offline --data-dir=~/mp-data --short-log-format $@a
```

don't forget: `chmod +x mp.sh`

## Sync music
```
./mp.sh sync
```

Note that only favorite playlists will be downloaded. Disliked tracks are not downloaded. About 5GB of storage space is used for every 1000 tracks.

## Start music player
```
./mp.sh start
```

Visit http://localhost:8080 in a web browser. Use Ctrl+C to stop the web server.

## Shortcuts

Using the Termux:Widget addon (install from F-Droid) you can add commands as shortcuts to your home screen, allowing you to start the music player with a single click.

```
mkdir .shortcuts
chmod +x 700 .shortcuts
cd .shortcuts
echo "~/mp.sh start" > music-start
echo "~/mp.sh sync" > music-sync
chmod +x *
```

## Updating

Updates may introduce bugs. It is advisable that you do not update at a time where you really need the music player to work, like just before going on a trip.

Run: `pip install --upgrade raphson-mp`

## Moving from legacy git clone installation to Python package

1. Follow the installation instructions again, but do not start the music player yet.
2. Move the `data` directory from `WebApp` to the correct location, for example `~/mp-data`
3. Start the music player, and make sure it all works
4. Delete the old installation: `rm -rf WebApp`

## Updating legacy git clone installation

1. Enter the correct directory.
2. Run `git pull` to download new source code.
3. If your previous update was before 2023-10-28, use the [migrations](./migrations.md) wiki page to update your database.
4. Run `termux/install` to update Python dependencies.

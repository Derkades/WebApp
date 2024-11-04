if [ -z "$1" ] || [ -z "$2" ]
then
    echo "Usage: $0 <audio file> <youtube url>"
    exit 1
fi

yt-dlp -f bestvideo --no-playlist --prefer-free-formats -o video.tmp "$2"
ffmpeg -i "$1" -i video.tmp -map_metadata 0 -map 0:a -map 1:v -c:a copy -c:v copy "$1.mkv"
rm video.tmp

# Music videos

The music player supports playing music videos alongside audio, for music files that contain both an audio and video stream. H264 and VP9 video streams are supported.

It is recommended to use the mkv container format, as it supports the widest variety of video formats and audio formats. ffmpeg can be used to combine take high quality audio and metadata from one file, and the video from another. For example:

```
ffmpeg -i music.flac -i video.webm -map_metadata 0 -map 0:a -map 1:v -c:a copy -c:v copy combined.mkv
```

The example script `./download-music-video.sh` can be used to automatically download a music video from youtube and merge it with an audio file. For best results, do take care to pick a video and audio stream that match (roughly) in length.

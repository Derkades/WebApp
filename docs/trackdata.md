# Track data

A track data object contains the following fields:
* `path` Relative path to music file
* `display` Display name
* `display_file` Fallback display string generated from file name
* `playlist` Relative path to playlist
* `playlist_display` Playlist display name
* `duration` Track duration
* `tags` Tags from genres metadata (possibly empty)
* `title` Track title or null
* `artists` Track artists or null
* `album` Track album or null
* `album_artist`
* `album_index`
* `year`

It is returned by the `/track_list` API endpoint. It is then stored by the frontend in `state.tracks`.

Track data for queued tracks is stored in `state.queue`, with additional data:
* `audioUrl` - URL for audio API endpiont
* `audioBlobUrl` - Downloaded audio, URL to local blob
* `imageUrl` - URL for lyrics API endpoint
* `imageBlobUrl`- Downloaded image, URL to local blob
* `lyrics`
  * `found` - boolean
  * `source` - Source URL (only present if lyrics were found)
  * `html` - Lyrics HTML (only present if lyrics were found)
# API

For all POST requests, a CSRF token is required as part of the request body with the name "csrf".

Track object:
  - `playlist` - playlist name (string)
  - `path` - relative path to track
  - `mtime` - integer, unix timestamp in seconds when the track was last modified
  - `duration` - integer
  - `title` - string
  - `album` - string
  - `album_artist` - string
  - `year` - integer
  - `artists` - list of artist names
  - `tags` - list of tag names
  - `video` - video type, `null`, `vp9`, `h264`
  - `display` - display title (string)

## Tracks

A track is identified by a `relpath` (relative path) locating a track within the music directory. For example: `RS/01 - Distraction.flac`.

### GET `/track/<relpath>/audio`

Retrieve audio for a track.

Params:
  - `type` - audio type, one of: `webm_opus_high`, `webm_opus_low`, `mp4_aac`, `mp3_with_metadata`

Response:
  - 200 OK
  - 304 Not Modified
  - 404 Not Found - if track does not exist

Response body (bytes): audio

Note: with type=mp3_with_metadata, a `Content-Disposition` header is present in the response instructing the browser to download the mp3 file with a suitable name.

### GET `/track/<relpath>/cover`

Retrieve cover image for a track.

### GET `/track/<relpath>/lyrics`

Retrieve lyrics for a track.

Params:
  - (`type`) - lyrics type, either `synced` or `plain`. If not specified, either may be returned

Response:
  - 200 OK
  - 304 Not Modified
  - 404 Not Found - if track does not exist

Response body (json):
  - `type` - `none`, `plain` or `synced`
  - `source` - a string, sometimes but not necessarily a URL
  - `text` if `type` == `plain` - string
  - `text` if `type` == `synced - list of objects
    - `start_time` - float
    - `text` - string

### POST `/track/<relpath>/update_metadata`

Request body (json):
  - `title` - string
  - `album` - string
  - `artists` - string list
  - `album_artist` - string
  - `tags` - string list
  - `year` - integer

Response:
  - 200 OK - updated successfully
  - 403 Forbidden - no write access to playlist
  - 404 Not Found - if track does not exist

### GET `/track/<relpath>/acoustid`

Response:
  - 200 OK
  - 404 Not Found - if track does not exist

Response body (json):

Array of objects:
 - `id`: string
 - `title`: string
 - `album`: string
 - `artists`: string list
 - `album_artist`: string
 - `year`: integer or `null`
 - `release_type`: string
 - `packaging`: string

### GET `/tracks/filter`

Params:
  - (`playlist`) - string
  - (`artist`) - string
  - (`album_artist`) - string
  - (`album`) - string
  - (`has_metadata`) - literal value `1`
  - (`tag`) - string

Response:
  - 200 OK
  - 304 Not Modified

Response body (json): list of track objects

### GET `/tracks/search`

Params:
  - `query` - string

Response:
  - 200 OK

Response body (json):
  - `tracks` list of track objects
  - `albums` list of objects
    - `album` album name
    - `artist` album artist name

### GET `/tracks/tags`

Response:
  - 200 OK

Response body (json): list of strings

## Playlists

### GET `/playlist/list`

Response:
  - 200 OK

Response body (json): list of objects:
  - `name`
  - `track_count`
  - `favorite`
  - `write`

Note: empty playlists are not returned by this endpoint

### POST `/playlist/<playlist_name>/choose_track`

Request body (json):
  - (`tag_mode`) `allow` or `deny`
  - (`tags`) list of tag names
  - (`require_metadata`) boolean

Response:
  - 200 OK
  - 404 Not Found - if no track could be chosen from this playlist

Response body (json): track object

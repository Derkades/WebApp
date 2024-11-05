## 1.3.0 2024-11-05
* New: playlist selection in guessing game
* New: experimental music video support
* New: setting to enable or disable lyrics
* New: download data export in account settings
* Improve: highlight current lyrics line
* Improve: automatically reload if browser loads outdated player from cache
* Improve: better sizing of cover image and lyrics box, will now take up as much screen space as possible
* Improve: remove BeautifulSoup and lxml dependency
* Improve: reduce memory usage and startup time in offline mode by only importing necessary modules
* Improve: add description to settings
* Improve: login box design
* Fix: missing play button for first track
* Fix: restore missing settings button in offline mode
* Fix: copy button missing if source playlist is not writable (source doesn't need to be writable)
* Fix: broken box shadows in music player

## 1.2.1 2024-10-26
* Improve: MusicBrainz search is more likely to find the correct cover image
* Fix: album cover from cache always being low quality
* Fix: time-synced lyrics are now available in offline-mode
* Fix: language and privacy account settings were applied for all users

## 1.2.0 2024-10-22
* New: time-synced lyrics
* New: automatic metadata lookup using AcoustID and MusicBrainz
* Fix: untranslated strings

## 1.1.0 2024-10-16

* New: add track to queue from web URL
* New: hotkey to open search
* New: artist similarity heatmap in statistics
* Improve: autofocus search field
* Improve: search UI
* Improve: switch search from trigram to unicode61 tokenizer. Misspellings are no longer tolerated, but returned results are a better match.
* Improve: restore home button to offline music player
* Improve: fixed height for queue so buttons don't jump around
* Fix: missing translations in package
* Fix: broken copy button for virtual tracks (like news)

## 1.0.1 2024-10-14

* Improve: tags UI
* Fix: lyrics extraction
* Fix: null albums in search
* Fix: missing dependencies in pypi package

## 1.0.0 2024-10-13

First release



from unittest import TestCase

from raphson_mp.lyrics import AZLyricsFetcher, GeniusFetcher, LrcLibFetcher, LyricFindFetcher, PlainLyrics, TimeSyncedLyrics


class TestLyrics(TestCase):
    def test_lrclib(self):
        # full length cd version
        lyrics = LrcLibFetcher().find('Strong', 'London Grammar', 'If You Wait', 276)
        assert isinstance(lyrics, TimeSyncedLyrics), lyrics
        assert lyrics.text[0].text == 'Excuse me for a while', lyrics.text[0]
        assert lyrics.text[0].start_time == 43.56, lyrics.text[0]

        # music video version
        lyrics = LrcLibFetcher().find('Strong', 'London Grammar', 'If You Wait', 242)
        assert isinstance(lyrics, TimeSyncedLyrics), lyrics
        assert lyrics.text[0].text == 'Excuse me for a while', lyrics.text[0]
        assert lyrics.text[0].start_time == 14.6, lyrics.text[0]

    def test_azlyrics(self):
        lyrics = AZLyricsFetcher().find('Starburster', 'Fontaines D.C.', None, None)
        assert isinstance(lyrics, PlainLyrics)
        assert "I wanna see you alone, I wanna sharp the stone" in lyrics.text, lyrics.text

    def test_genius(self):
        lyrics = GeniusFetcher().find('Give Me One Reason', 'Tracy Chapman', None, None)
        assert isinstance(lyrics, PlainLyrics)
        assert "You know that I called you, I called too many times" in lyrics.text, lyrics.text

    def test_lyricfind(self):
        lyrics = LyricFindFetcher().find('Blank Space', 'Taylor Swift', None, None)
        assert isinstance(lyrics, PlainLyrics)
        assert "Nice to meet you, where you been?" in lyrics.text, lyrics.text

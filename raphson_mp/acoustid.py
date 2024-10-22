import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import requests

from raphson_mp import settings

if settings.offline_mode:
    # Module must not be imported to ensure no data is ever downloaded in offline mode.
    raise RuntimeError('Cannot use bing in offline mode')


log = logging.getLogger(__name__)


API_KEY = 'rTTqI4IrbJ'


@dataclass
class Fingerprint:
    duration: int
    fingerprint_b64: str


def lookup(fingerprint: Fingerprint) -> Iterator[str]:
    """
    Returns: musicbrainz recording id
    """
    response = requests.get('https://api.acoustid.org/v2/lookup',
                            params={'format': 'json',
                                    'client': API_KEY,
                                    'duration': fingerprint.duration,
                                    'fingerprint': fingerprint.fingerprint_b64,
                                    'meta': 'recordingids'})
    response.raise_for_status()
    json = response.json()

    for result in json['results']:
        if 'recordings' in result:
            for recording in result['recordings']:
                yield recording['id']


def get_fingerprint(path: Path):
    output = subprocess.check_output(['fpcalc', path.absolute().as_posix()])
    split = output.splitlines()

    assert split[0].startswith(b'DURATION=')
    duration = int(split[0][9:].decode())

    assert split[1].startswith(b'FINGERPRINT=')
    fingerprint = split[1][12:].decode()

    return Fingerprint(duration, fingerprint)

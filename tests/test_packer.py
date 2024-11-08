import os
from pathlib import Path
import random
from tempfile import TemporaryDirectory
from unittest import TestCase

from raphson_mp import packer


class TestPacker(TestCase):
    def test_packer(self):
        with TemporaryDirectory() as tempdir:
            a = os.urandom(random.randint(0, 1000))
            b = os.urandom(random.randint(0, 1000))
            Path(tempdir, 'a').write_bytes(a)
            Path(tempdir, 'b').write_bytes(b)
            result = packer.pack(Path(tempdir))
            assert result == a + b

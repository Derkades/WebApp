import random
import secrets
from unittest import TestCase

from raphson_mp import auth


class TestPassword(TestCase):
    def test_hash(self):
        password = secrets.token_urlsafe(random.randint(0, 100))
        notpassword = secrets.token_urlsafe(random.randint(0, 100))
        hash = auth.hash_password(password)
        assert auth._verify_hash(hash, password)  # pyright: ignore[reportPrivateUsage]
        assert not auth._verify_hash(hash, notpassword)  # pyright: ignore[reportPrivateUsage]

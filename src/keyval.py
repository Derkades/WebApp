import settings

import redis


conn = redis.Redis(settings.redis_host, port=settings.redis_port, db=0)

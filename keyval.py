import redis


# TODO configurable
conn = redis.Redis('redis', port=6379, db=0)

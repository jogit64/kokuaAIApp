web: gunicorn assistant:app
worker: REDIS_URL=$(REDISCLOUD_URL) rq worker high default low



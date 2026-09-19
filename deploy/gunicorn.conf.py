# Gunicorn configuration for SP-Tech Software Solution
# Usage: gunicorn -c deploy/gunicorn.conf.py sanjivani.wsgi:application

import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Logging
accesslog = "/var/log/sanjivani/gunicorn-access.log"
errorlog  = "/var/log/sanjivani/gunicorn-error.log"
loglevel  = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

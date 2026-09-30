"""Celery application for PickleSphere.

Only imported when the ``celery`` package is installed (see
``picklesphere/__init__.py``), so the app boots without a broker in
development and tests. Start a worker with:

    celery -A picklesphere worker -l info
    celery -A picklesphere beat -l info
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'picklesphere.settings')

app = Celery('picklesphere')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

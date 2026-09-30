"""Minimal health endpoint for container healthchecks and load balancers.

Returns 200 with ``{"status": "ok"}`` when the application and database are
reachable, 503 otherwise. Deliberately unauthenticated and dependency-free.
"""

import json

from django.db import connection
from django.http import HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """Report liveness plus a quick database round-trip."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_ok = True
    except Exception:
        db_ok = False

    if db_ok:
        return HttpResponse(
            json.dumps({'status': 'ok', 'database': 'ok'}),
            content_type='application/json',
        )
    return HttpResponse(
        json.dumps({'status': 'degraded', 'database': 'unavailable'}),
        content_type='application/json',
        status=503,
    )

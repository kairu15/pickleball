"""
Cache utilities for PickleSphere page-level and query-level caching.

Provides:
- ``pages_cache_get_or_set``: cache a computed value in the 'pages' namespace
  (invalidated automatically by signals whenever related records change).
- ``cache_anon_page``: per-view decorator that full-page caches a view for
  anonymous visitors with no pending flash messages. Authenticated users and
  requests carrying undisplayed flash messages always bypass the cache so
  user-specific content and feedback messages stay accurate.
- ``invalidate_all_caches``: signal handler that clears the 'cms', 'pages'
  and 'default' (template fragment) namespaces.
- Monitoring: invalidation-event log, slow-query log, and per-alias cache stats
  for the super-admin Cache Monitor page.
"""

import time
from collections import deque
from functools import wraps

from django.conf import settings
from django.core.cache import caches
from django.utils.cache import patch_cache_control
from django.views.decorators.cache import cache_page

PAGES_CACHE_TIMEOUT = getattr(settings, 'PAGES_CACHE_TIMEOUT', 300)

# ---------------------------------------------------------------------------
# In-process monitoring logs (per worker). With Redis these are best-effort;
# the authoritative cache stats come from the backend itself.
# ---------------------------------------------------------------------------
_MONITOR_MAX = 200
_invalidation_events = deque(maxlen=_MONITOR_MAX)
_slow_queries = deque(maxlen=_MONITOR_MAX)


def get_pages_cache():
    """The 'pages' cache namespace used for page data and per-user helpers."""
    return caches['pages']


def pages_cache_get_or_set(key, fallback_fn, timeout=None):
    """Thread-safe cache get-or-set in the 'pages' namespace.

    Falls back to computing the value on every call if caching fails, so a
    broken cache backend can never take the site down.
    """
    cache = get_pages_cache()
    result = cache.get(key)
    if result is None:
        try:
            result = fallback_fn()
            cache.set(key, result, timeout or PAGES_CACHE_TIMEOUT)
        except Exception:
            result = None
    return result


def _record_invalidation(sender, kwargs):
    try:
        label = getattr(getattr(sender, '_meta', None), 'label', None) or str(sender)
        action = 'delete' if 'created' not in kwargs else ('create' if kwargs.get('created') else 'update')
        _invalidation_events.appendleft({
            'time': time.time(),
            'model': label,
            'action': action,
        })
    except Exception:
        pass


def invalidate_all_caches(sender=None, **kwargs):
    """Signal handler: clear CMS, page-data, full-page and fragment caches.

    Wired to every public-content model so any create/update/delete refreshes
    the public site within the next request. Each cache alias lives in its own
    Redis DB (or LocMem namespace), so clearing never flushes sessions or
    unrelated data.
    """
    try:
        for alias in ('cms', 'pages', 'default'):
            caches[alias].clear()
    except Exception:
        pass
    _record_invalidation(sender, kwargs)


def cache_anon_page(timeout, key_prefix=None):
    """Full-page cache decorator for anonymous visitors only.

    - Authenticated requests are rendered live and marked ``no-store`` so
      user-specific content is never cached.
    - Anonymous requests carrying undisplayed flash messages are rendered live
      too, so success/error toasts are never lost to (or frozen by) the cache.
    - All other anonymous GET/HEAD responses are served from the 'default'
      cache via Django's ``cache_page`` (the key includes the full path and
      query string, so filtered/paginated variants cache independently).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if user is not None and user.is_authenticated:
                response = view_func(request, *args, **kwargs)
                patch_cache_control(response, no_store=True)
                return response
            # Skip the cache while there are undisplayed flash messages so the
            # next page always shows them (cached pages cannot show session data).
            try:
                if request.session.get('_messages'):
                    response = view_func(request, *args, **kwargs)
                    patch_cache_control(response, no_store=True)
                    return response
            except Exception:
                pass
            return cache_page(timeout, key_prefix=key_prefix)(view_func)(request, *args, **kwargs)
        return _wrapped
    return decorator


# ---------------------------------------------------------------------------
# Monitoring support
# ---------------------------------------------------------------------------

def record_slow_query(duration_ms, sql):
    """Record a slow DB query for the Cache Monitor page."""
    _slow_queries.appendleft({
        'time': time.time(),
        'duration_ms': round(duration_ms, 1),
        'sql': (sql or '')[:500],
    })


def get_invalidation_events():
    return list(_invalidation_events)


def get_slow_queries():
    return list(_slow_queries)


def get_cache_stats():
    """Per-alias stats: backend class, key count, and (Redis) hit/miss counters."""
    stats = {}
    for alias in ('default', 'cms', 'pages', 'sessions'):
        entry = {'backend': 'unavailable', 'keys': 'n/a', 'hits': 'n/a', 'misses': 'n/a'}
        try:
            cache = caches[alias]
            entry['backend'] = cache.__class__.__name__
            raw = getattr(cache, '_cache', None)
            if raw is not None and hasattr(raw, 'get_client'):
                # django-redis
                try:
                    info = raw.get_client().info()
                    entry['keys'] = info.get('db0', {}).get('keys', 'n/a')
                    stats_section = info.get('stats', {})
                    entry['hits'] = stats_section.get('keyspace_hits', 'n/a')
                    entry['misses'] = stats_section.get('keyspace_misses', 'n/a')
                except Exception:
                    pass
            elif raw is not None and hasattr(raw, '_cache'):
                # LocMemCache
                try:
                    entry['keys'] = len(raw._cache)
                except Exception:
                    pass
            elif hasattr(cache, 'info'):
                try:
                    entry.update(cache.info() or {})
                except Exception:
                    pass
        except Exception as exc:
            entry['backend'] = f'unavailable ({exc})'
        stats[alias] = entry
    return stats

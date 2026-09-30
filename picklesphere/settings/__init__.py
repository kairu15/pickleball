"""Settings package for PickleSphere.

``picklesphere.settings`` keeps working as the settings module: it
star-imports ``picklesphere.settings.dev`` or ``picklesphere.settings.prod``
based on the ``DJANGO_ENV`` environment variable (default ``dev``), so this
package always exposes the full settings namespace. A specific module can
also be selected directly, e.g.
``DJANGO_SETTINGS_MODULE=picklesphere.settings.prod``.

All shared configuration lives in ``picklesphere.settings.base``; the dev and
prod modules only override what differs. The env variable is never mutated
here: Django and pytest-django must agree on one module name.
"""

import os

_env = os.environ.get('DJANGO_ENV', 'dev').strip().lower()

if _env == 'prod':
    from .prod import *  # noqa: F401,F403
    from .prod import *  # noqa: F401,F403  (explicit: keep linters quiet)
else:
    from .dev import *  # noqa: F401,F403

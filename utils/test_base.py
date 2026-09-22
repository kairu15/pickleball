"""
Test utilities — monkey-patches Django's test Client to pass a `request`
to `authenticate()` for django-axes compatibility.

Usage in test files:
    from utils.test_base import *  # (place after other django imports)
"""

from django.test import Client
from django.contrib.auth import authenticate

_original_login = Client.login


def _axes_compatible_login(self, **credentials):
    """
    Override Client.login() to pass a mock request to authenticate().

    django-axes v6+ requires a ``request`` argument in authenticate().
    Django's stock Client.login() does not pass one, causing
    AxesBackendRequestParameterRequired in any test that uses
    self.client.login().
    """
    from django.test.client import RequestFactory
    rf = RequestFactory()
    request = rf.get('/')
    user = authenticate(request=request, **credentials)
    if user:
        self._login(user)
        return True
    return False


Client.login = _axes_compatible_login

"""Test package for the accounts app.

The CI workflow runs ``python manage.py test accounts.tests``; before this
package existed that command failed with a ModuleNotFoundError, so the role
access-control step in CI never actually ran.
"""

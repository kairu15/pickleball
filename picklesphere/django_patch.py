"""
Django Python 3.14 Compatibility Patch

Python 3.14 changed how super() works - it no longer has __dict__
for setting new attributes. This breaks Django 4.2's template context copying.

This patch fixes the BaseContext.__copy__ method to work with Python 3.14.
"""

import sys
from copy import copy

# Only apply patch for Python 3.14+
if sys.version_info >= (3, 14):
    from django.template.context import BaseContext, Context, RequestContext

    def _fixed_basecontext_copy(self):
        """
        Fixed __copy__ method that doesn't rely on super().__copy__()
        which fails in Python 3.14 due to super() having no __dict__.
        """
        # Create new instance using object.__new__ to avoid __init__
        duplicate = object.__new__(self.__class__)
        
        # Copy all attributes from self to duplicate
        for attr_name in dir(self):
            # Skip private/special methods and properties
            if attr_name.startswith('_'):
                continue
            try:
                attr_value = getattr(self, attr_name)
                # Don't copy methods, only data attributes
                if not callable(attr_value):
                    setattr(duplicate, attr_name, attr_value)
            except (AttributeError, TypeError):
                pass
        
        # Ensure dicts is properly copied (it's a list of dicts)
        if hasattr(self, 'dicts'):
            duplicate.dicts = self.dicts[:]
        
        return duplicate

    # Apply the patch to BaseContext
    BaseContext.__copy__ = _fixed_basecontext_copy

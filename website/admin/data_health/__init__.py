"""
Read-only "Data Health" admin checks package.

Importing this package imports every check module (via ``checks``), whose
``@register_check`` decorators populate :data:`REGISTRY`. The package is
imported from ``website/admin/__init__.py`` so the checks are registered at
startup, and wired into the admin URLconf by
``MakeabilityLabAdminSite.get_urls()``.
"""

from website.admin.data_health import checks  # noqa: F401  (populates REGISTRY)
from website.admin.data_health.registry import REGISTRY  # noqa: F401

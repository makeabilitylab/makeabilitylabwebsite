"""
Public, read-only REST API for the Makeability Lab website (#1268).

Exposes already-public data (publications, projects, grants, people, and
project leadership) in a machine-readable, versioned form so external consumers
can treat this site as the source of truth instead of duplicating content. Two
concrete consumers drove the design: Project Sidewalk (grants / people /
leadership / publications for a project) and Jon's academic page (a "recent
publications" list).

Design summary (see docs/API.md for the full contract):
  * Django REST Framework, mounted at ``/api/v1/``.
  * Read-only (GET/HEAD/OPTIONS), no auth, no throttle -- the data is already
    public on the site, so nothing new is disclosed.
  * Cross-origin browser requests are allowed via ``ApiCorsMiddleware`` (scoped
    to ``/api/``) so a client-side widget can fetch it directly.
"""

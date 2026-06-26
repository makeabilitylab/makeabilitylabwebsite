"""Import every check module so its ``@register_check`` decorator runs.

The import order here is the order checks appear on the dashboard.
"""

from website.admin.data_health.checks import (  # noqa: F401
    duplicate_people,
    url_name_collisions,
    media_integrity,
    publication_quality,
    unlinked_artifacts,
    conference_papers_without_talk,
    poster_papers_without_poster,
    project_health,
    project_leadership,
    position_integrity,
    news_health,
    duplicate_keywords,
)

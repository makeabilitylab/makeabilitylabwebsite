"""
Data-health check: projects that are incomplete.

Public visibility is now governed solely by the ``is_visible`` flag (#1300), so
this check focuses on *completeness*: it flags projects missing a thumbnail
(``gallery_image``), a publication, currently-active members, or an umbrella.
The ``is_visible`` column is surfaced for context — a project that is visible
*and* incomplete is the most actionable case. Read-only.
"""

from datetime import date

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Project


@register_check
class ProjectHealthCheck(HealthCheck):
    slug = 'project-health'
    title = 'Project health'
    description = (
        'Projects missing a thumbnail or publication (invisible on the public '
        'site), with no currently-active members, or with no umbrella.'
    )
    group = 'Projects'
    link_model = 'project'
    columns = [
        'id', 'name', 'short_name', 'is_visible', 'has_thumbnail',
        'has_publication', 'active_member_count', 'has_umbrella', 'issues',
    ]

    def get_rows(self):
        today = date.today()
        rows = []
        for project in Project.objects.all().prefetch_related('projectrole_set'):
            has_thumbnail = bool(project.gallery_image)
            has_publication = project.has_publication()

            active_member_count = sum(
                1 for role in project.projectrole_set.all()
                if role.start_date and role.start_date <= today
                and (role.end_date is None or role.end_date >= today)
            )
            has_umbrella = project.project_umbrellas.exists()

            issues = []
            if not has_thumbnail:
                issues.append('no thumbnail')
            if not has_publication:
                issues.append('no publication')
            if active_member_count == 0:
                issues.append('no active members')
            if not has_umbrella:
                issues.append('no umbrella')

            if not issues:
                continue

            rows.append({
                'id': project.pk,
                'name': project.name,
                'short_name': project.short_name,
                'is_visible': bool(project.is_visible),
                'has_thumbnail': has_thumbnail,
                'has_publication': has_publication,
                'active_member_count': active_member_count,
                'has_umbrella': has_umbrella,
                'issues': ', '.join(issues),
            })

        rows.sort(key=lambda r: r['name'].lower())
        return rows

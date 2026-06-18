"""
Data-health check: projects with missing PI/Co-PI leadership info (#1182).

PI/Co-PI tracking lives on ``ProjectRole.lead_project_role`` (values ``PI`` /
``Co-PI``), not on the ``Project`` itself. This check flags two gaps:

- **no PI** — the project has no ``ProjectRole`` marked PI at all. Per the model
  help text, most projects should have Jon Froehlich as PI, so a project with
  zero PI roles is almost always an oversight.
- **no active PI** — the project hasn't ended, but every PI role on it has an
  end date in the past, so nobody is currently the PI of a live project.

Co-PI absence is intentionally *not* flagged: many projects legitimately have
only a PI. The Co-PI count is surfaced as context. Read-only.
"""

from datetime import date

from website.admin.data_health.registry import HealthCheck, register_check
from website.models import Project
from website.models.project_role import LeadProjectRoleTypes


@register_check
class ProjectLeadershipCheck(HealthCheck):
    slug = 'project-leadership'
    title = 'Project leadership (PI/Co-PI)'
    description = (
        'Projects with no PI on record, or ongoing projects whose PI role(s) '
        'have all ended (no currently-active PI).'
    )
    group = 'Projects'
    columns = [
        'id', 'name', 'short_name', 'is_visible', 'has_ended',
        'pi_count', 'active_pi_count', 'copi_count', 'pis', 'issues',
    ]

    def get_rows(self):
        today = date.today()
        rows = []
        projects = Project.objects.all().prefetch_related('projectrole_set__person')
        for project in projects:
            roles = list(project.projectrole_set.all())
            pi_roles = [
                r for r in roles
                if r.lead_project_role == LeadProjectRoleTypes.PI
            ]
            copi_roles = [
                r for r in roles
                if r.lead_project_role == LeadProjectRoleTypes.CO_PI
            ]

            def _is_active(role):
                return (
                    role.start_date and role.start_date <= today
                    and (role.end_date is None or role.end_date >= today)
                )

            active_pi_count = sum(1 for r in pi_roles if _is_active(r))
            has_ended = project.has_ended()

            issues = []
            if not pi_roles:
                issues.append('no PI')
            elif not has_ended and active_pi_count == 0:
                issues.append('no active PI')

            if not issues:
                continue

            pi_names = ', '.join(
                r.person.get_full_name() for r in pi_roles
            )
            rows.append({
                'id': project.pk,
                'name': project.name,
                'short_name': project.short_name,
                'is_visible': bool(project.is_visible),
                'has_ended': has_ended,
                'pi_count': len(pi_roles),
                'active_pi_count': active_pi_count,
                'copi_count': len(copi_roles),
                'pis': pi_names,
                'issues': ', '.join(issues),
            })

        rows.sort(key=lambda r: r['name'].lower())
        return rows

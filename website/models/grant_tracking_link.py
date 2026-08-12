from django.db import models


class GrantTrackingLink(models.Model):
    """
    A superuser-only bookmark to an official grant/finance tracking system —
    e.g. UW CSE's SharePoint "Financial Reporting and Projections" folder, or
    the UW-wide Award Portal. Rendered as a link bar at the top of the Grant
    changelist (see ``website/templates/admin/website/grant/change_list.html``).

    Why these live in the database instead of ``settings.py`` (#1448): the real
    URLs embed per-PI SharePoint sharing tokens and query parameters, and this
    repository is public. Keeping them as editable rows means nothing sensitive
    is ever committed — the maintainer pastes them in through ``/admin`` on each
    environment.

    Access is superuser-only by the same mechanism as ``Grant`` and ``Award``:
    the model is simply absent from ``EDITORS_MODELS``/``CONTRIBUTORS_SPEC`` in
    the ``setup_admin_groups`` management command.

    Usage::

        GrantTrackingLink.objects.create(
            label="UW CSE — Financial Reporting and Projections",
            url="https://uwnetid.sharepoint.com/sites/...",
            notes="Requires UW NetID sign-in",
            display_order=0,
        )
    """

    label = models.CharField(max_length=255)
    label.help_text = "Link text shown on the Grants page (e.g., 'UW Award Portal')"

    # NOT the URLField default of 200: the UW CSE SharePoint link runs well past
    # that once its folder id and sharing parameters are included. Postgres would
    # reject the insert outright. Pinned by a regression test.
    url = models.URLField(max_length=1000)
    url.help_text = "Full URL of the tracking system. May be very long (SharePoint links are)."

    notes = models.CharField(max_length=500, null=True, blank=True)
    notes.help_text = "Optional reminder shown next to the link (e.g., 'Requires UW NetID')"

    display_order = models.IntegerField(default=0)
    display_order.help_text = "Lower numbers appear first."

    class Meta:
        ordering = ['display_order', 'label']
        verbose_name = "grant tracking link"
        verbose_name_plural = "grant tracking links"

    def __str__(self):
        return self.label

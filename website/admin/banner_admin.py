from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from easy_thumbnails.files import get_thumbnailer
from image_cropping import ImageCroppingMixin

from website.models import Banner
from website.admin.admin_site import ml_admin_site


class MediaTypeFilter(admin.SimpleListFilter):
    """Right-sidebar filter to narrow banners by what media they carry.

    With ~200 banners, it's useful to isolate, e.g., the ones still missing
    an image/video ("No media") or the video banners. A banner can have both
    an image and a video, so "Has image" / "Has video" are not mutually
    exclusive; "No media" means neither is set.
    """
    title = 'media type'
    parameter_name = 'media_type'

    def lookups(self, request, model_admin):
        return (
            ('image', 'Has image'),
            ('video', 'Has video'),
            ('none', 'No media'),
        )

    def queryset(self, request, queryset):
        return self.filter_queryset(queryset, self.value())

    @staticmethod
    def filter_queryset(queryset, value):
        """Apply the media-type filter. Split out so it's unit-testable
        without constructing a full admin request."""
        no_image = Q(image='') | Q(image__isnull=True)
        no_video = Q(video='') | Q(video__isnull=True)
        if value == 'image':
            return queryset.exclude(no_image)
        if value == 'video':
            return queryset.exclude(no_video)
        if value == 'none':
            return queryset.filter(no_image & no_video)
        return queryset


@admin.register(Banner, site=ml_admin_site)
class BannerAdmin(ImageCroppingMixin, admin.ModelAdmin):

    # In Django, you can specify the order of fields using one of two methods:
    # - fields, a list of fields you want to display in order
    # - fieldsets, allows you to organize fields into sets
    fieldsets = [
        ('Banner Title and Caption', {'fields': ["title", "caption", "link"]}),
        ('Banner Video', {'fields': ["video"]}),
        ('Banner Image', {'fields': ["image", "alt_text", "cropping"]}),
        ('Banner Pages', {'fields': ["landing_page", "project"]}),
        ('Banner Properties', {'fields': ["favorite", "date_added"]})
    ]

    # The list page is the main tool for managing the ~200 banners on prod, so
    # it leads with a visual thumbnail and exposes inline toggles (#1082).
    list_display = ('thumbnail', 'title', 'project', 'landing_page', 'favorite',
                    'date_added', 'get_media_url')
    list_display_links = ('title',)
    list_editable = ('landing_page', 'favorite')

    # Right-sidebar filters + date drill-down + search (the asks in #1082).
    list_filter = ('landing_page', 'favorite', MediaTypeFilter, 'project')
    search_fields = ('title', 'caption', 'project__name', 'alt_text', 'link')
    date_hierarchy = 'date_added'
    ordering = ('-date_added',)
    list_per_page = 50

    autocomplete_fields = ['project']
    readonly_fields = ('date_added',)

    actions = ('add_to_landing_page', 'remove_from_landing_page',
               'mark_favorite', 'unmark_favorite')

    # 1600x500 is the banner's native aspect ratio; keep the list thumbnail
    # proportional so editors can recognize a banner at a glance.
    _THUMB_SIZE = (160, 50)

    def thumbnail(self, obj):
        """Small, cheap preview for the changelist. Uses easy_thumbnails so we
        don't ship 200 full-size banner images to the admin list page, and
        respects the editor-defined crop box."""
        if obj.image:
            try:
                thumb = get_thumbnailer(obj.image).get_thumbnail({
                    'size': self._THUMB_SIZE,
                    'box': obj.cropping,
                    'crop': True,
                    'detail': True,
                })
                return format_html(
                    '<img src="{}" width="160" height="50" alt="" '
                    'style="object-fit:cover;border-radius:3px;" />', thumb.url)
            except Exception:
                return format_html('<span style="color:#c00;">image error</span>')
        if obj.video:
            return format_html('<span title="Background video">🎥 video</span>')
        return format_html('<span style="color:#999;">—</span>')
    thumbnail.short_description = 'Preview'

    def get_media_url(self, obj):
        """Either returns the video url or the image url, if specified"""
        media_url = obj.image.url if obj.image else obj.video.url if obj.video else None
        return format_html('<a href="{}">{}</a>', media_url, media_url) if media_url else None
    get_media_url.short_description = 'Media'

    @admin.action(description='Add selected banners to the landing page')
    def add_to_landing_page(self, request, queryset):
        updated = queryset.update(landing_page=True)
        self.message_user(request, f'{updated} banner(s) added to the landing page.')

    @admin.action(description='Remove selected banners from the landing page')
    def remove_from_landing_page(self, request, queryset):
        updated = queryset.update(landing_page=False)
        self.message_user(request, f'{updated} banner(s) removed from the landing page.')

    @admin.action(description='Mark selected banners as favorite')
    def mark_favorite(self, request, queryset):
        updated = queryset.update(favorite=True)
        self.message_user(request, f'{updated} banner(s) marked as favorite.')

    @admin.action(description='Unmark selected banners as favorite')
    def unmark_favorite(self, request, queryset):
        updated = queryset.update(favorite=False)
        self.message_user(request, f'{updated} banner(s) unmarked as favorite.')

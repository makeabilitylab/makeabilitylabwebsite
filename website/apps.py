from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = 'website'

    # Because we are using the decorator approach to hook up signals in the website app, we need
    # to import the signals submodule in the ready() function.
    # See: https://docs.djangoproject.com/en/1.9/topics/signals/#connecting-receiver-functions
    def ready(self):
        import website.signals
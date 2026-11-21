"""Tests for ``read_server_setting`` in ``makeabilitylab/settings.py``.

The deployed sites (DJANGO_ENV of PROD or TEST) must refuse to start without a
real SECRET_KEY and ALLOWED_HOSTS in config.ini, instead of silently running on
defaults that are published in this public repository. Local dev keeps its
convenient fallbacks. Pure logic, no DB.
"""
from configparser import ConfigParser

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from makeabilitylab.settings import _PUBLIC_DEV_SECRET_KEY, read_server_setting

# ConfigParser treats '%' as interpolation syntax, so a literal '%' in an .ini
# value is written '%%'; config.get() hands back the single-'%' original.
ESCAPED_DEV_KEY = _PUBLIC_DEV_SECRET_KEY.replace('%', '%%')



def make_config(**django_options):
    """Build a ConfigParser with the given options in its [Django] section."""
    config = ConfigParser()
    if django_options:
        config['Django'] = django_options
    return config


class ReadServerSettingTests(SimpleTestCase):

    def test_configured_value_is_used_everywhere(self):
        config = make_config(SECRET_KEY='a-real-key')
        for env in ('PROD', 'TEST', 'DEBUG', None):
            with self.subTest(env=env):
                self.assertEqual(
                    read_server_setting(config, 'SECRET_KEY', env, 'dev'), 'a-real-key')

    def test_missing_option_falls_back_off_server(self):
        for env in ('DEBUG', None):
            with self.subTest(env=env):
                self.assertEqual(
                    read_server_setting(make_config(), 'ALLOWED_HOSTS', env, '*'), '*')

    def test_missing_option_raises_on_servers(self):
        for env in ('PROD', 'TEST'):
            with self.subTest(env=env):
                with self.assertRaises(ImproperlyConfigured):
                    read_server_setting(make_config(), 'SECRET_KEY', env, 'dev')

    def test_missing_section_raises_on_servers(self):
        # config.ini absent entirely -> ConfigParser has no [Django] section.
        with self.assertRaises(ImproperlyConfigured):
            read_server_setting(ConfigParser(), 'ALLOWED_HOSTS', 'PROD', '*')

    def test_blank_option_raises_on_servers(self):
        with self.assertRaises(ImproperlyConfigured):
            read_server_setting(make_config(SECRET_KEY='   '), 'SECRET_KEY', 'PROD', 'dev')

    def test_public_dev_key_is_rejected_on_servers(self):
        """A config.ini that copies the key from this repo is no better than none."""
        config = make_config(SECRET_KEY=ESCAPED_DEV_KEY)
        with self.assertRaises(ImproperlyConfigured):
            read_server_setting(config, 'SECRET_KEY', 'PROD', 'dev')
        # ...but it is still fine for local dev.
        self.assertEqual(
            read_server_setting(config, 'SECRET_KEY', 'DEBUG', 'dev'), _PUBLIC_DEV_SECRET_KEY)

    def test_error_names_the_option_but_never_a_value(self):
        config = make_config(SECRET_KEY=ESCAPED_DEV_KEY)
        with self.assertRaises(ImproperlyConfigured) as ctx:
            read_server_setting(config, 'SECRET_KEY', 'PROD', 'dev')
        self.assertIn('SECRET_KEY', str(ctx.exception))
        self.assertNotIn(_PUBLIC_DEV_SECRET_KEY, str(ctx.exception))

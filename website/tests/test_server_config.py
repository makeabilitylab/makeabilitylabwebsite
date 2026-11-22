"""Tests for ``read_server_setting`` in ``makeabilitylab/settings.py``.

The deployed sites (DJANGO_ENV of PROD or TEST) must refuse to start without a
real SECRET_KEY and ALLOWED_HOSTS in config.ini, instead of silently running on
defaults that are published in this public repository. Local dev keeps its
convenient fallbacks. Pure logic, no DB.
"""
from configparser import ConfigParser

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from makeabilitylab.settings import (
    _PUBLIC_DEV_SECRET_KEY,
    parse_allowed_hosts,
    read_server_setting,
    safe_config_get,
)

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
                # The file was read (it has a [Django] section) but lacks the option.
                with self.assertRaises(ImproperlyConfigured) as ctx:
                    read_server_setting(make_config(DEBUG='False'), 'SECRET_KEY', env, 'dev')
                self.assertIn('must set', str(ctx.exception))

    def test_missing_section_raises_on_servers(self):
        # config.ini absent entirely -> ConfigParser has no [Django] section.
        with self.assertRaises(ImproperlyConfigured):
            read_server_setting(ConfigParser(), 'ALLOWED_HOSTS', 'PROD', '*')

    def test_unread_config_gets_its_own_message(self):
        """An unreadable/missing file must not be reported as a missing option."""
        with self.assertRaises(ImproperlyConfigured) as ctx:
            read_server_setting(ConfigParser(), 'SECRET_KEY', 'TEST', 'dev')
        self.assertIn('not read', str(ctx.exception))

    def test_option_in_wrong_section_raises_on_servers(self):
        # Section names are case-sensitive: [django] is not [Django].
        config = ConfigParser()
        config['django'] = {'SECRET_KEY': 'a-real-key'}
        with self.assertRaises(ImproperlyConfigured):
            read_server_setting(config, 'SECRET_KEY', 'PROD', 'dev')

    def test_blank_option_raises_on_servers(self):
        for env in ('PROD', 'TEST'):
            with self.subTest(env=env):
                with self.assertRaises(ImproperlyConfigured):
                    read_server_setting(make_config(SECRET_KEY='   '), 'SECRET_KEY', env, 'dev')

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


class ParseAllowedHostsTests(SimpleTestCase):

    def test_strips_and_drops_empty_entries(self):
        self.assertEqual(
            parse_allowed_hosts(' a.edu ,b.edu,, ', 'PROD'), ['a.edu', 'b.edu'])

    def test_multiline_ini_value(self):
        # An indented continuation line in config.ini arrives with a newline.
        self.assertEqual(
            parse_allowed_hosts('a.edu,\nb.edu', 'TEST'), ['a.edu', 'b.edu'])

    def test_no_hostnames_raises_on_servers(self):
        for value in (',', ' , ,'):
            with self.subTest(value=value):
                with self.assertRaises(ImproperlyConfigured):
                    parse_allowed_hosts(value, 'PROD')

    def test_wildcard_is_accepted(self):
        # Accepted on the servers too (with a printed warning): rejecting it
        # could take down a site whose config has always relied on it.
        self.assertEqual(parse_allowed_hosts('*', 'PROD'), ['*'])
        self.assertEqual(parse_allowed_hosts('*', None), ['*'])


class ConfigErrorsNeverLeakValuesTests(SimpleTestCase):
    """configparser quotes the bad value in its errors; ours must not.

    These messages reach the deploy preflight's log, which is public.
    """

    SECRET = "abc%xyzTAILSECRET"  # a bare % is an interpolation syntax error

    def raw_config(self, text):
        config = ConfigParser()
        config.read_string(text)
        return config

    def test_bare_percent_in_secret_key(self):
        config = self.raw_config(f"[Django]\nSECRET_KEY={self.SECRET}\n")
        with self.assertRaises(ImproperlyConfigured) as ctx:
            read_server_setting(config, 'SECRET_KEY', 'PROD', 'dev')
        self.assertNotIn('TAILSECRET', str(ctx.exception))
        self.assertIn('SECRET_KEY', str(ctx.exception))
        # `from None`: the original configparser error must not ride along.
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)

    def test_missing_interpolation_target(self):
        config = self.raw_config("[Postgres]\nPASSWORD=hunter2%(nope)s\n")
        with self.assertRaises(ImproperlyConfigured) as ctx:
            safe_config_get(config, 'Postgres', 'PASSWORD')
        self.assertNotIn('hunter2', str(ctx.exception))

    def test_escaped_percent_reads_normally(self):
        config = self.raw_config("[Django]\nSECRET_KEY=abc%%def\n")
        self.assertEqual(safe_config_get(config, 'Django', 'SECRET_KEY'), 'abc%def')

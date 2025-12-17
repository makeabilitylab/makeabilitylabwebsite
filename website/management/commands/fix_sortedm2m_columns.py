# website/management/commands/fix_sortedm2m_columns.py

"""
Management command to ensure SortedManyToManyField intermediate tables have
the required sort_value column.

This fixes an issue where some models inheriting from Artifact (which uses
SortedManyToManyField for authors) may have been migrated before the field
was changed to SortedManyToManyField, resulting in missing sort_value columns.
"""

import logging
from django.core.management.base import BaseCommand
from django.db import connection

_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
        Checks SortedManyToManyField intermediate tables for missing sort_value
        columns and adds them if necessary. This ensures author ordering works
        correctly for all Artifact subclasses (Talk, Poster, Publication, etc.).
    """

    # Tables that use SortedManyToManyField and require a sort_value column
    TABLES_TO_CHECK = [
        'website_poster_authors',
        'website_talk_authors',
        'website_publication_authors',
        # Add other tables here if needed
    ]

    def handle(self, *args, **options):
        _logger.info("Running fix_sortedm2m_columns to check for missing sort_value columns...")

        tables_fixed = []
        tables_already_ok = []

        for table_name in self.TABLES_TO_CHECK:
            if not self._table_exists(table_name):
                _logger.debug(f"Table {table_name} does not exist, skipping")
                continue

            if self._column_exists(table_name, 'sort_value'):
                _logger.debug(f"Table {table_name} already has sort_value column")
                tables_already_ok.append(table_name)
            else:
                _logger.info(f"Table {table_name} is missing sort_value column, adding it...")
                self._add_sort_value_column(table_name)
                tables_fixed.append(table_name)

        # Summary
        if tables_fixed:
            _logger.info(f"Fixed {len(tables_fixed)} table(s): {', '.join(tables_fixed)}")
        else:
            _logger.info("No tables needed fixing")

        if tables_already_ok:
            _logger.debug(f"Tables already OK: {', '.join(tables_already_ok)}")

        _logger.info("Completed fix_sortedm2m_columns")

    def _table_exists(self, table_name):
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            bool: True if table exists, False otherwise
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, [table_name])
            return cursor.fetchone()[0]

    def _column_exists(self, table_name, column_name):
        """
        Check if a column exists in a table.

        Args:
            table_name: Name of the table
            column_name: Name of the column to check

        Returns:
            bool: True if column exists, False otherwise
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                )
            """, [table_name, column_name])
            return cursor.fetchone()[0]

    def _add_sort_value_column(self, table_name):
        """
        Add the sort_value column to a table.

        The column is added as INTEGER NOT NULL DEFAULT 0, which matches
        what django-sortedm2m expects.

        Args:
            table_name: Name of the table to modify
        """
        with connection.cursor() as cursor:
            # Using format string here because table names can't be parameterized,
            # but this is safe since table_name comes from our hardcoded list
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN sort_value INTEGER NOT NULL DEFAULT 0
            """)
            _logger.info(f"Successfully added sort_value column to {table_name}")
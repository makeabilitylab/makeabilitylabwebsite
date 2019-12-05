# This is an example migration for renaming Model field names without losing data

from django.db import migrations

# Based on the example here:
# https://gist.github.com/dhbradshaw/e2bdeb502b0d0d2acced
class Migration(migrations.Migration):

    dependencies = [
        ('website', '0009_auto_20191204_1418'),
    ]

    operations = [
    	migrations.RenameField('Position', 'grad_mentor', 'mentor'),
    ]

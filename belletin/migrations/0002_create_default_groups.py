from django.db import migrations
from belletin.admin import create_default_groups

def init_groups(apps, schema_editor):
    create_default_groups()

class Migration(migrations.Migration):
    dependencies = [
        ('belletin', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(init_groups),
    ] 
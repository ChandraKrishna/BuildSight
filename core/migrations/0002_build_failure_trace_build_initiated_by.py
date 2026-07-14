# Generated manually for the BuildSight build-detail feature.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]

    operations = [
        migrations.AddField(model_name='build', name='failure_trace', field=models.TextField(blank=True)),
        migrations.AddField(model_name='build', name='initiated_by', field=models.CharField(blank=True, max_length=255)),
    ]

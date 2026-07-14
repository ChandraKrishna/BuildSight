from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0002_build_failure_trace_build_initiated_by')]

    operations = [
        migrations.CreateModel(
            name='DisplayPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dashboard_default_days', models.PositiveSmallIntegerField(default=3)),
                ('report_default_days', models.PositiveSmallIntegerField(default=3)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

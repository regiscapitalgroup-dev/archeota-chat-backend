# Generated by Django 5.2.1 on 2025-07-09 22:59

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asset', '0005_rename_value_asset_acquisition_value_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='claimactiontransaction',
            options={'verbose_name': 'Claim Action Transaction', 'verbose_name_plural': 'Claim Action Transactions'},
        ),
        migrations.CreateModel(
            name='ImportLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('import_job_id', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('status', models.CharField(choices=[('SUCCESS', 'Success'), ('ERROR', 'Error')], max_length=10)),
                ('row_number', models.PositiveIntegerField()),
                ('error_message', models.TextField(blank=True, null=True)),
                ('row_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Import Log',
                'verbose_name_plural': 'Import Logs',
            },
        ),
    ]

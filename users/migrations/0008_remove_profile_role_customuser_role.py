# Generated by Django 5.2.1 on 2025-07-01 21:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_companyprofile'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='role',
        ),
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='users.role'),
        ),
    ]

# Generated by Django 5.2.1 on 2025-06-24 01:52

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_googleprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text='Role Code', max_length=50, unique=True)),
                ('description', models.TextField(blank=True, help_text='Role Description', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Role Active')),
            ],
            options={
                'verbose_name': 'Rol',
                'verbose_name_plural': 'Roles',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(blank=True, max_length=30, null=True, verbose_name='Phone Number')),
                ('nationalID', models.CharField(blank=True, max_length=100, null=True, verbose_name='National ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
                ('role', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='users.role')),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'Users Profiles',
            },
        ),
    ]

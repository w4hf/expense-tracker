# Generated by Django 4.2.21 on 2025-05-11 16:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='loan',
            options={'ordering': ['-created_at']},
        ),
    ]

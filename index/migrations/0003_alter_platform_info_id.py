# Generated by Django 4.2.9 on 2024-01-22 09:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0002_alter_platform_info_auth_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platform_info',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
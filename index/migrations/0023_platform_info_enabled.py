# Generated by Django 4.2.9 on 2024-01-25 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0022_alter_sys_user_account_alter_sys_user_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform_info',
            name='enabled',
            field=models.IntegerField(default=1, verbose_name='是否可用'),
        ),
    ]

# Generated by Django 4.2.9 on 2024-09-10 04:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0055_rename_platform_inspect_inspect_name_platform_inspect_item_platform_inspect_item_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform_info',
            name='is_notice',
            field=models.IntegerField(default=1, verbose_name='是否告警通知,0不是，1是'),
        ),
    ]

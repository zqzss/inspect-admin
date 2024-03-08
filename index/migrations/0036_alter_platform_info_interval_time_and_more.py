# Generated by Django 4.2.9 on 2024-01-31 02:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0035_platform_info_interval_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platform_info',
            name='interval_time',
            field=models.IntegerField(blank=True, default=1, null=True, verbose_name='通知间隔时间，单位(分钟)'),
        ),
        migrations.AlterField(
            model_name='platform_inspect_item',
            name='interval_time',
            field=models.IntegerField(blank=True, default=1, null=True, verbose_name='通知间隔时间，单位(分钟)'),
        ),
    ]
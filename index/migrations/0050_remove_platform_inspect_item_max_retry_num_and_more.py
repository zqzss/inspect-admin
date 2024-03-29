# Generated by Django 4.2.9 on 2024-02-18 02:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0049_platform_inspect_item_max_retry_num_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='platform_inspect_item',
            name='max_retry_num',
        ),
        migrations.RemoveField(
            model_name='platform_inspect_item',
            name='retry_num',
        ),
        migrations.AddField(
            model_name='platform_info',
            name='max_retry_num',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='最大请求重试次数'),
        ),
        migrations.AddField(
            model_name='platform_info',
            name='retry_num',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='请求次数'),
        ),
    ]

# Generated by Django 4.2.9 on 2024-02-19 02:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0051_platform_inspect_item_notice_ignore_not_online_num_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform_inspect_item',
            name='retry_num',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='请求失败次数'),
        ),
    ]
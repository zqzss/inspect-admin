# Generated by Django 4.2.9 on 2024-02-06 12:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0046_platform_info_last_not_online_device'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platform_info',
            name='last_not_online_device',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='上一次巡检不在线的设备'),
        ),
    ]

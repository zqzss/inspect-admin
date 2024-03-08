# Generated by Django 4.2.9 on 2024-02-19 02:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0050_remove_platform_inspect_item_max_retry_num_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform_inspect_item',
            name='notice_ignore_not_online_num',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='通知忽略设备后不在线设备个数'),
        ),
        migrations.AlterField(
            model_name='platform_info',
            name='max_retry_num',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='请求失败后，最大请求重试次数'),
        ),
        migrations.AlterField(
            model_name='platform_info',
            name='password',
            field=models.CharField(max_length=512, verbose_name='密码'),
        ),
        migrations.AlterField(
            model_name='platform_info',
            name='retry_num',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='请求失败次数'),
        ),
    ]
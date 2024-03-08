# Generated by Django 4.2.9 on 2024-02-01 02:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0042_platform_inspect_item_device_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='notice_config',
            name='notice_code',
            field=models.IntegerField(default=201, verbose_name='告警等级,和Inspect_Record的response_code值一致。200可用，201告警,500不可用'),
        ),
        migrations.AlterField(
            model_name='platform_inspect_item',
            name='disabled_reason',
            field=models.TextField(blank=True, null=True, verbose_name='不可用或告警的原因'),
        ),
        migrations.AlterField(
            model_name='platform_inspect_item',
            name='enabled',
            field=models.IntegerField(default=1, verbose_name='是否可用,0不可以，1可用,2告警'),
        ),
    ]
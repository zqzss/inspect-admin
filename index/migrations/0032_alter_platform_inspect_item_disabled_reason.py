# Generated by Django 4.2.9 on 2024-01-30 02:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0031_platform_inspect_item_request_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platform_inspect_item',
            name='disabled_reason',
            field=models.TextField(blank=True, max_length=128, null=True, verbose_name='不可用的原因'),
        ),
    ]

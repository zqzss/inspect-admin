# Generated by Django 4.2.9 on 2024-01-23 01:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0005_alter_platform_inspect_platform_info_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Platform_Inspect',
            new_name='Platform_Inspect_Item',
        ),
        migrations.AlterModelTable(
            name='platform_inspect_item',
            table='platform_inspect_item',
        ),
    ]
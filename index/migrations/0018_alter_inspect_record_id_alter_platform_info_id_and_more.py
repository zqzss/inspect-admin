# Generated by Django 4.2.9 on 2024-01-23 16:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0017_alter_inspect_record_id_alter_platform_info_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inspect_record',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='platform_info',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='platform_inspect_item',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]

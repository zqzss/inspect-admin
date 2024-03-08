# Generated by Django 4.2.9 on 2024-01-23 16:54

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0016_alter_inspect_record_inspect_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inspect_record',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='platform_info',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='platform_inspect_item',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
    ]

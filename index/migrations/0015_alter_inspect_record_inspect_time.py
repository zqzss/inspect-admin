# Generated by Django 4.2.9 on 2024-01-23 08:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0014_alter_inspect_record_inspect_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inspect_record',
            name='inspect_time',
            field=models.DateTimeField(verbose_name='巡检时间'),
        ),
    ]
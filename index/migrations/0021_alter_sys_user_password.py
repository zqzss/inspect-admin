# Generated by Django 4.2.9 on 2024-01-24 02:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0020_sys_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sys_user',
            name='password',
            field=models.CharField(max_length=128, verbose_name='密码'),
        ),
    ]

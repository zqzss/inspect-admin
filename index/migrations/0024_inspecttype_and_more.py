# Generated by Django 4.2.9 on 2024-01-29 02:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0023_platform_info_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='InspectType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('inspectTypeName', models.CharField(max_length=32, unique=True, verbose_name='巡检类型名称')),
            ],
        ),
        migrations.RemoveField(
            model_name='platform_inspect_item',
            name='inspect_type',
        ),
        migrations.AddField(
            model_name='platform_inspect_item',
            name='inspectTypeId',
            field=models.ForeignKey(blank=True, db_column='inspectTypeId', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='inspectTypeId', to='index.inspecttype'),
        ),
    ]
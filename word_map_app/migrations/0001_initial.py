# Generated by Django 4.2.3 on 2023-08-10 22:18

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GeoFeature',
            fields=[
                ('ogc_fid', models.AutoField(primary_key=True, serialize=False)),
                ('region', models.CharField(max_length=100, unique=True)),
                ('wkb_geometry', django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
            ],
        ),
    ]
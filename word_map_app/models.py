from django.contrib.gis.db import models

class GeoFeature(models.Model):
    ogc_fid = models.AutoField(primary_key=True)
    region = models.CharField(max_length=100, unique=True)
    wkb_geometry = models.PolygonField()

    def __str__(self):
        return self.region
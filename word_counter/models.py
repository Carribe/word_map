from django.contrib.gis.db import models
from word_map_app.models import GeoFeature

class ProcessedWord(models.Model):
    word = models.CharField(max_length=255, db_index=True)
    pos = models.CharField(max_length=50, db_index=True)
    count = models.IntegerField()
    xlsx_source = models.CharField(max_length=255, db_index=True)
    region = models.ForeignKey(GeoFeature, to_field='ogc_fid', on_delete=models.CASCADE, null=True, blank=True)
    # другие поля модели

    def __str__(self):
        return f"{self.word} ({self.count}) - {self.pos} ({self.xlsx_source}) [{self.region}]"



class UploadedFile(models.Model):
    file = models.FileField(upload_to='files_xlsx/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

from django.contrib import admin
from .models import ProcessedWord, UploadedFile

admin.site.register(ProcessedWord)
admin.site.register(UploadedFile)
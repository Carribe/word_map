from django import forms
from word_map_app.models import GeoFeature

class UploadFileForm(forms.Form):
    file = forms.FileField()
    region = forms.ModelChoiceField(queryset=GeoFeature.objects.all())


from django import forms

class QueryForm(forms.Form):
    query = forms.CharField(label='Введите слово', widget=forms.TextInput(attrs={'placeholder': 'Введите слово'}))
    submit = forms.widgets.Input(attrs={'type': 'submit', 'value': 'Поиск', 'class': 'fit'})

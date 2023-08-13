from celery import Celery
import os

# Установите переменную окружения 'DJANGO_SETTINGS_MODULE'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'word_map_project.settings')

import django
django.setup()

# Создаем экземпляр Celery
app = Celery('word_map_project')

# Загружаем настройки из нашего Django-приложения
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение и регистрация задач из приложений Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

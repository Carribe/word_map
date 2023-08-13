import spacy
import datetime
import pandas as pd
import logging
import time
import shutil
from django.db import transaction
from django.db.utils import OperationalError
from word_map_project import settings
import os
from django.db import connections
from word_counter.models import ProcessedWord
from word_map_app.models import GeoFeature
from word_map_project.settings import BASE_DIR

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "word_map_project.settings")

import django
django.setup()

from word_counter.models import ProcessedWord

# Загрузка модели для русского языка
nlp = spacy.load("ru_core_news_sm")

# Настройки логирования
log_file_path = os.path.join(BASE_DIR, "word_counter", "../word_map.log")
logging.basicConfig(filename=log_file_path, level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def process_word(args):
    word, count = args
    doc = nlp(word)
    lemmatized_word = " ".join([token.lemma_ for token in doc if not token.is_stop and len(token.lemma_) >= 3 and token.pos_ in {"NOUN", "VERB", "ADJ"}])
    if lemmatized_word.strip():
        pos = doc[0].pos_
        return lemmatized_word, count, pos
    return None

def move_processed_file(input_file_path, destination_folder):
    # Создаем папку, если ее нет
    os.makedirs(destination_folder, exist_ok=True)

    # Получаем имя файла и расширение из полного пути
    filename, file_extension = os.path.splitext(os.path.basename(input_file_path))

    # Формируем новое имя файла с добавлением timestamp в конце
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    new_filename = f"{filename}_{timestamp}{file_extension}"

    # Путь для перемещения файла в папку 'used_files_xlsx'
    destination_path = os.path.join(destination_folder, new_filename)

    # Перемещаем файл в папку 'used_files_xlsx'
    shutil.move(input_file_path, destination_path)

    logging.info(f"Файл '{os.path.basename(input_file_path)}' успешно перемещен в папку '{destination_folder}' с новым именем '{new_filename}'.")


def process_file(input_file_path, file, selected_region_id):
    try:
        # Отключаем индексы перед обработкой файла
        for db_name in connections:
            with connections[db_name].cursor() as cursor:
                try:
                    cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
                    cursor.execute("SET synchronous_commit = OFF;")
                    cursor.execute("SET maintenance_work_mem = '16MB';")
                    cursor.execute("SET work_mem = '2MB';")
                except OperationalError:
                    pass
        df = pd.read_excel(input_file_path, nrows=200)
        df = df[df["Количество"] >= 10]
        df["Слово"] = df["Слово"].astype(str)

        with transaction.atomic():
            # Создаем словарь для хранения подсчитанных повторений слов
            word_counts = {}

            # Обрабатываем новые записи из файла и подсчитываем повторения
            for index, row in df.iterrows():
                lemmatized_word = process_word((row["Слово"], row["Количество"]))
                if lemmatized_word is not None:
                    word_key = (lemmatized_word[0], lemmatized_word[2])  # Используем слово и POS в качестве ключа
                    if word_key in word_counts:
                        word_counts[word_key] += lemmatized_word[1]
                    else:
                        word_counts[word_key] = lemmatized_word[1]
                        print(f"Слово: {word_key[0]}, POS: {word_key[1]}, Количество: {lemmatized_word[1]}")

            # Удаляем все записи для выбранного региона
            ProcessedWord.objects.filter(region_id=selected_region_id).delete()

            # Добавляем новые записи в базу данных
            for (word, pos), count in word_counts.items():
                processed_word = ProcessedWord(
                    word=word,
                    pos=pos,
                    xlsx_source=file,
                    region_id=selected_region_id,
                    count=count
                )
                processed_word.save()

        logging.info(f"Результаты из файла '{input_file_path}' сохранены в базе данных.")

    except FileNotFoundError:
        logging.error(f"Ошибка: Файл '{input_file_path}' не найден.")
    except PermissionError:
        logging.error(f"Ошибка: Нет прав на доступ к файлу '{input_file_path}'.")
    except Exception as e:
        logging.error(f"Ошибка: Возникла непредвиденная ошибка: {e}")
    finally:
        # Включаем индексы в случае возникновения исключения
        for db_name in connections:
            with connections[db_name].cursor() as cursor:
                try:
                    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
                    cursor.execute("SET synchronous_commit = ON;")
                    cursor.execute("RESET maintenance_work_mem;")
                    cursor.execute("RESET work_mem;")
                except OperationalError:
                    pass


def main(file_path, file_name, selected_region_id):
    start_time = time.time()
    destination_folder = os.path.join(settings.BASE_DIR, "word_counter", "used_files_xlsx")

    process_file(file_path, file_name, selected_region_id)  # Передаем selected_region_id

    move_processed_file(file_path, destination_folder)
    print(f"Время обработки файла: {time.time() - start_time} секунд")
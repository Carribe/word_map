import spacy
import datetime
from tqdm import tqdm
import pandas as pd
import logging
import time
import shutil
from django.db import transaction
from django.db import connections
from django.db.utils import OperationalError
import multiprocessing

import os

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



# Остальной код не изменился, включая функцию process_word

def process_file(input_file_path):
    input_file = os.path.basename(input_file_path)
    try:
        # Отключаем индексы перед обработкой файла
        for db_name in connections:
            with connections[db_name].cursor() as cursor:
                try:
                    cursor.execute("PRAGMA defer_foreign_keys=ON;")
                    cursor.execute("PRAGMA synchronous=OFF;")
                    cursor.execute("PRAGMA journal_mode=MEMORY;")
                    cursor.execute("PRAGMA cache_size=-16000;")
                except OperationalError:
                    pass

        df = pd.read_excel(input_file_path, nrows=200)
        df = df[df["Количество"] >= 10]
        df["Слово"] = df["Слово"].astype(str)

        word_count_args = zip(df["Слово"], df["Количество"])

        with multiprocessing.Pool() as pool, tqdm(total=len(df["Слово"])) as pbar:
            lemmatized_words = list(pool.imap(process_word, word_count_args))
            lemmatized_words = [word for word in lemmatized_words if word is not None]

        # Создаем список объектов ProcessedWord для bulk_create
        objs_to_create = [ProcessedWord(word=word, count=count, pos=pos, xlsx_source=input_file) for word, count, pos in lemmatized_words]

        # Вставляем объекты в базу данных с помощью bulk_create
        with transaction.atomic():
            for obj in objs_to_create:
                processed_word, created = ProcessedWord.objects.get_or_create(
                    word=obj.word,
                    pos=obj.pos,
                    xlsx_source=obj.xlsx_source,
                    defaults={'count': obj.count}
                )
                if not created:
                    processed_word.count += obj.count
                    processed_word.save()

        logging.info(f"Результаты из файла '{input_file_path}' сохранены в базу данных.")

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
                    cursor.execute("PRAGMA defer_foreign_keys=OFF;")
                    cursor.execute("PRAGMA synchronous=ON;")
                    cursor.execute("PRAGMA journal_mode=DELETE;")
                    cursor.execute("PRAGMA cache_size=-2000;")
                except OperationalError:
                    pass


def main():
    start_time = time.time()
    # Папка с входными XLSX-файлами
    input_folder = "/Users/artem/PycharmProjects/word_map_ru/word_map_project/word_counter/files_xlsx"
    # Папка для перемещения обработанных XLSX-файлов
    destination_folder = "/Users/artem/PycharmProjects/word_map_ru/word_map_project/word_counter/used_files_xlsx"

    # Список всех XLSX-файлов в папке
    file_list = [f for f in os.listdir(input_folder) if f.endswith(".xlsx")]

    for input_file in file_list:
        input_file_path = os.path.join(input_folder, input_file)
        logging.info(f"Обработка файла: {input_file}")
        process_file(input_file_path)  # Убрано передача input_file как аргумент

        # Перемещение файла в папку 'used_files_xlsx'
        move_processed_file(input_file_path, destination_folder)

    print(f"Общее время обработки всех файлов: {time.time() - start_time} секунд")

if __name__ == "__main__":
    main()

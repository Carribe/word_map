from celery import shared_task
import spacy
import pandas as pd
import logging
from django.db import transaction
from django.db.utils import OperationalError
import os
from django.db import connections
from word_map_project.settings import BASE_DIR
from word_counter.models import ProcessedWord

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "word_map_project.settings")

import django
django.setup()



@shared_task
def process_word_file_task(file_content, file_name, selected_region_id):
    try:
        # Здесь можете добавить код для сохранения файла из file_content, если необходимо

        # Загрузка модели для русского языка
        nlp = spacy.load("ru_core_news_sm")

        # Настройки логирования
        log_file_path = os.path.join(BASE_DIR, "word_counter", "../word_map.log")
        logging.basicConfig(filename=log_file_path, level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        def process_word(args):
            word, count = args
            doc = nlp(word)
            lemmatized_word = " ".join([token.lemma_ for token in doc if
                                        not token.is_stop and len(token.lemma_) >= 3 and len(token.lemma_) <= 25 and token.pos_ in {"NOUN", "VERB",
                                                                                                        "ADJ"}])
            if lemmatized_word.strip():
                pos = doc[0].pos_
                return lemmatized_word, count, pos
            return None

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
                df = pd.read_excel(input_file_path)
                df = df[df["Количество"] >= 10]
                df["Слово"] = df["Слово"].astype(str)

                with transaction.atomic():
                    # Создаем словарь для хранения подсчитанных повторений слов
                    word_counts = {}

                    # Обрабатываем новые записи из файла и подсчитываем повторения
                    for index, row in df.iterrows():
                        lemmatized_word = process_word((row["Слово"], row["Количество"]))
                        if lemmatized_word is not None:
                            word_key = (
                            lemmatized_word[0], lemmatized_word[2])  # Используем слово и POS в качестве ключа
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

        # Вызываем process_file для обработки файла
        process_file(file_content, file_name, selected_region_id)

        logging.info(f"Обработка файла '{file_name}' успешно завершена.")

    except Exception as e:
        logging.error(f"Ошибка при обработке файла '{file_name}': {e}")

import geopandas as gpd
from django.http import JsonResponse
from django.shortcuts import render
import folium
import time
from sqlalchemy import create_engine
from word_counter.models import ProcessedWord
from django.db.models import Count
from .forms import QueryForm


def query_view(request):
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            print("Введенное слово:", query)  # Вывод в консоль

    return JsonResponse({'message': 'Слово успешно получено и выведено в консоль.'})


def word_map(request):
    # Подключение к базе данных PostGIS
    engine = create_engine('postgresql://artem:1234@localhost:5432/postgres')

    # Создание словаря для хранения информации о количестве уникальных слов для каждого региона
    region_unique_word_counts = {}
    # Получение данных о количестве уникальных слов для каждого региона из модели ProcessedWord
    processed_words = ProcessedWord.objects.values('region_id').annotate(unique_words=Count('word', distinct=True))
    for processed_word in processed_words:
        region_unique_word_counts[processed_word['region_id']] = processed_word['unique_words']

    # Загрузка данных из базы данных PostGIS
    sql = "SELECT * FROM word_map_app_geofeature"
    russia_regions_gdf = gpd.GeoDataFrame.from_postgis(sql, engine, geom_col='wkb_geometry')

    # Создание объекта GeoJson с геометрией регионов России
    geojson_layer = folium.GeoJson(russia_regions_gdf)

    # Создание объекта карты
    map_russia = folium.Map(location=[61.5240, 105.3188], zoom_start=3)

    style_function = lambda x: {'fillColor': '#B0E0E6',
                                'color': '#000000',
                                'fillOpacity': 0.5,
                                'weight': 0.5}
    highlight_function = lambda x: {'fillColor': '#FFC0CB',
                                    'color': '#000000',
                                    'fillOpacity': 0.50,
                                    'weight': 0.5}

    for feature in geojson_layer.data['features']:
        region_id = feature['properties']['ogc_fid']
        unique_words_count = region_unique_word_counts.get(region_id)

        if unique_words_count is not None:
            popup_text = f"{unique_words_count} уникальных слов"
        else:
            popup_text = 'Данные по региону отсутствуют' + '<div class="3u$ 12u$(small)"> <input type="submit" value="Поиск" id="submitButton" class="fit" /></div>'

        # Создание объекта GeoJson для региона с обработчиком событий
        region_geojson = folium.GeoJson(
            feature,
            style_function=style_function,  # Скрытие заливки
            highlight_function=highlight_function,  # Подсветка при наведении
            tooltip=folium.GeoJsonTooltip(fields=['region'], aliases=['Регион']),
            popup=folium.Popup(popup_text)  # Создание popup для текущего региона
        )
        # Добавление объекта GeoJson на карту
        map_russia.add_child(region_geojson)

    # Преобразование карты в HTML-строку
    start_time = time.time()
    map_html = map_russia.get_root().render()
    print(f"Время преобразования карты в HTML-строку: {time.time() - start_time} секунд")

    # Контекст для передачи в шаблон
    context = {'map_html': map_html}

    return render(request, 'word_map_app/word_map.html', context)
import geopandas as gpd

def check_geodata_correctness():
    # Замените параметры подключения к вашей базе данных
    # Если используется другая СУБД, измените соответствующим образом
    connection_params = {
        'host': 'localhost',
        'database': 'your_database',
        'user': 'your_user',
        'password': 'your_password'
    }

    # Подключение к базе данных и получение данных GeoFeature
    gdf = gpd.GeoDataFrame.from_postgis('SELECT * FROM your_table_name;', **connection_params)

    # Проверка типа геометрии
    print("Проверка типа геометрии...")
    valid_geometry_types = ['POINT', 'LINESTRING', 'POLYGON', 'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON']
    invalid_geometries = gdf[~gdf['geometry'].geom_type.isin(valid_geometry_types)]
    if not invalid_geometries.empty:
        print("Обнаружены некорректные типы геометрии:")
        print(invalid_geometries)

    # Проверка SRID
    print("\nПроверка SRID...")
    srid = 4326  # Замените на нужный SRID, если он отличается
    invalid_srid = gdf[gdf['geometry'].srid != srid]
    if not invalid_srid.empty:
        print("Обнаружены некорректные SRID:")
        print(invalid_srid)

    # Проверка замкнутости полигонов
    print("\nПроверка замкнутости полигонов...")
    invalid_polygons = gdf[gdf['geometry'].geom_type == 'POLYGON'].apply(lambda row: not row['geometry'].is_closed, axis=1)
    if invalid_polygons.any():
        print("Обнаружены незамкнутые полигоны:")
        print(gdf[invalid_polygons])

    # TODO: Дополните функцию проверкой на правильное упорядочение полигонов (если требуется)

    print("Проверка завершена.")

if __name__ == "__main__":
    check_geodata_correctness()

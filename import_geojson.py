import json
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "word_map_project.settings")
django.setup()
import json
from django.contrib.gis.geos import Polygon
from word_map_app.models import GeoFeature

def import_geojson_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)

    features = data.get('features', [])

    for feature in features:
        region = feature['properties']['region']
        coordinates = feature['geometry']['coordinates']

        # Check if there are multiple polygons for the region
        if len(coordinates) > 1:
            multi_polygon = []
            for polygon_coords in coordinates:
                if len(polygon_coords) >= 4:  # Ensure there are enough points for LinearRing
                    polygon = Polygon(polygon_coords[0], polygon_coords[1:])
                    multi_polygon.append(polygon)
            if multi_polygon:
                geo_feature = GeoFeature(region=region, geometry=multi_polygon)
                geo_feature.save()
        else:
            if len(coordinates[0]) >= 4:  # Ensure there are enough points for LinearRing
                polygon = Polygon(coordinates[0], coordinates[1:])
                geo_feature = GeoFeature(region=region, geometry=polygon)
                geo_feature.save()

if __name__ == '__main__':
    geojson_file = '/Users/artem/PycharmProjects/word_map_ru/word_map_project/word_map_app/geojson/Russia_regions.geojson'

    import_geojson_data(geojson_file)

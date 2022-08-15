""" 
    Start the flask server by running:

        $ python server.py

    And then head to http://127.0.0.1:5000/ in your browser to see the map displayed

"""

from flask import Flask

import geopandas as gpd
from shapely.geometry import Polygon
from shapely.ops import transform
import shapely
import pathlib
import passion

from copy import deepcopy

import folium

app = Flask(__name__)

def open_csv_results(results_path, filename):
    if (results_path / filename).is_file():
        # exists
        results = passion.util.io.load_csv(results_path, filename)
    else:
        # does not exist
        results = None
    
    return results

@app.route('/')
def index():
    start_coords = (50.77595349670269, 6.088548416982711)
    folium_map = folium.Map(location=start_coords, zoom_start=15)

    # TILE LAYERS
    folium.TileLayer('cartodbpositron').add_to(folium_map)
    folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(folium_map)
    
    outlines = open_csv_results(pathlib.Path('workflow/output/economic/'), 'lcoe.csv')
    add_outlines_layer(folium_map, outlines, 'economic')
    
    outlines = open_csv_results(pathlib.Path('workflow/output/technical/'), 'technical.csv')
    add_outlines_layer(folium_map, outlines, 'technical')
    
    outlines = open_csv_results(pathlib.Path('workflow/output/rooftops/'), 'rooftops.csv')
    add_outlines_layer(folium_map, outlines, 'rooftops')
    

    outlines = open_csv_results(pathlib.Path('workflow/output/sections/'), 'sections.csv')
    add_outlines_layer(folium_map, outlines, 'sections')
    
    # config.yml bbox frame
    min_lat = 50.77850739604879
    min_lon = 6.0768084397936395
    max_lat = 50.77214558009357
    max_lon = 6.091035433169415
    
    draw_bbox((min_lat, min_lon), (max_lat, max_lon), folium_map)

    folium.LayerControl().add_to(folium_map)
    return folium_map._repr_html_()

def add_outlines_layer(map, outlines, name):
    outlines_latlon_copy = deepcopy(outlines)
    geo_j = get_geoj_from_latlon_outlines(outlines_latlon_copy)
    layer_geom = get_layer_from_geoj(name + '-latlon', geo_j)
    layer_geom.add_to(map)
    
    return

def get_geoj_from_latlon_outlines(outlines):
    for section in outlines:
        section_geom = shapely.wkt.loads(section['outline_latlon'])

        section_geom = transform(lambda x, y: (y, x), section_geom)
        section['outline_latlon'] = list(section_geom.exterior.coords)

    crs = {'init': 'epsg:4326'}
    polygon_gdf = gpd.GeoDataFrame(
                                   crs=crs,
                                   geometry=[Polygon(section['outline_latlon']) for section in outlines]
                                   )
    geo_j = folium.GeoJson(polygon_gdf)

    return geo_j

def get_layer_from_geoj(name, geo_j):
    
    layer_geom = folium.FeatureGroup(name=name,control=True)

    for feature in geo_j.data['features']:
        # GEOJSON layer consisting of a single feature
        temp_layer = folium.GeoJson(feature)
        # create Popup and add it to our lone feature
        #folium.Popup(feature['properties']['name']).add_to(temp_layer)

        # consolidate individual features back into the main layer
        temp_layer.add_to(layer_geom)
    return layer_geom

def draw_bbox(min_latlon, max_latlon, map):
    folium.Rectangle(
        bounds=[
            [min_latlon[0], min_latlon[1]],
            [min_latlon[0], max_latlon[1]],
            [max_latlon[0], max_latlon[1]],
            [max_latlon[0], min_latlon[1]]
            ],
        color='#ff7800',
        fill=True,
        fill_color='#ffff00',
        fill_opacity=0.15,
        weight=0
    ).add_to(map)
    draw_circle(min_latlon[0], min_latlon[1], 'min_lat, min_lon', map, 'black')
    draw_circle(min_latlon[0], max_latlon[1], 'min_lat, max_lon', map, 'black')
    draw_circle(max_latlon[0], max_latlon[1], 'max_lat, max_lon', map, 'black')
    draw_circle(max_latlon[0], min_latlon[1], 'max_lat, min_lon', map, 'black')

def draw_circle(lat, lon, popup, map, color):
    folium.CircleMarker(
        location=[lat, lon],
        popup=popup,
        radius=4,
        color=color,
        fill_color=color,
        fill_opacity=0.7,
        weight=0
        ).add_to(map)

if __name__ == '__main__':
    app.run(debug=True)
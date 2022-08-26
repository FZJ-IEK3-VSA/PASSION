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
import matplotlib.colors
import numpy as np
import math

from copy import deepcopy

import folium
import branca
from util import rooftop_popup_html

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
    folium.TileLayer(
        'cartodbpositron',
        overlay = False
        ).add_to(folium_map)
    folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(folium_map)
    
    outlines = open_csv_results(pathlib.Path('workflow/output/rooftops/'), 'rooftops.csv')
    create_gradient_from_column(outlines, 'area', '#96BDC6', '#96BDC6')
    add_outlines_layer(folium_map, outlines, 'rooftops', '#96BDC6', 
                        ['area', 'center_lat', 'center_lon', 'color'])
    
    outlines = open_csv_results(pathlib.Path('workflow/output/sections/'), 'sections.csv')
    create_gradient_from_column(outlines, 'area', '#96BDC6', '#96BDC6')
    add_outlines_layer(folium_map, outlines, 'sections', '#15616D', 
                        ['area', 'center_lat', 'center_lon', 'flat', 'azimuth', 'tilt_angle', 'color'])
    
    outlines = open_csv_results(pathlib.Path('workflow/output/technical/'), 'technical.csv')
    create_gradient_from_column(outlines, 'yearly_gen', '#ff0000', '#00ff00')
    add_outlines_layer(folium_map, outlines, 'technical', '#E3B505', 
                        ['area', 'center_lat', 'center_lon', 'yearly_gen', 'capacity', 'modules_cost', 'color'])
    
    outlines = open_csv_results(pathlib.Path('workflow/output/economic/'), 'lcoe.csv')
    create_gradient_from_column(outlines, 'lcoe_eur_MWh', '#ff0000', '#00ff00')
    add_outlines_layer(folium_map, outlines, 'economic', '#81F499', 
                        ['area', 'center_lat', 'center_lon', 'lcoe_eur_MWh', 'color'])

    folium.LayerControl().add_to(folium_map)
    return folium_map._repr_html_()

def create_gradient_from_column(outlines, column, min_color, max_color):
    min_value = 9999999999999999999999999999
    max_value = -999999999999999999999999999
    # get min and max values for column
    for section in outlines:
        if section[column] > max_value: max_value = section[column]
        if section[column] < min_value: min_value = section[column]
    # normalize value between 0 and 1
    for section in outlines:
        norm_value = (section[column] - min_value) / (max_value - min_value)
        if (norm_value != 0): math.log(10*norm_value, 10) 
        color = color_fader(min_color, max_color, norm_value)
        section['color'] = color
        
    return

# https://stackoverflow.com/a/50784012
def color_fader(c1,c2,mix=0): #fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
    c1=np.array(matplotlib.colors.to_rgb(c1))
    c2=np.array(matplotlib.colors.to_rgb(c2))
    return matplotlib.colors.to_hex((1-mix)*c1 + mix*c2)

def add_outlines_layer(map, outlines, name, color, display_properties=[]):
    outlines_latlon_copy = deepcopy(outlines)
    geo_j = get_geoj_from_latlon_outlines(outlines_latlon_copy, display_properties)
    layer_geom = get_layer_from_geoj(name + ' layer', geo_j, color)
    layer_geom.add_to(map)
    
    return

def get_geoj_from_latlon_outlines(outlines, display_properties):
    display_dict = {}
    for display_property in display_properties:
        display_dict[display_property] = []
    for section in outlines:
        section_geom = shapely.wkt.loads(section['outline_latlon'])

        section_geom = transform(lambda x, y: (y, x), section_geom)
        section['outline_latlon'] = list(section_geom.exterior.coords)

        for display_property in display_properties:
            try:
                display_dict[display_property] += [section[display_property]]
            except:
                display_dict[display_property] += [None]

    crs = {'init': 'epsg:4326'}
    polygon_gdf = gpd.GeoDataFrame(
                                   data=display_dict,
                                   crs=crs,
                                   geometry=[Polygon(section['outline_latlon']) for section in outlines]
                                   )
    geo_j = folium.GeoJson(polygon_gdf)

    return geo_j

def get_layer_from_geoj(name, geo_j, color):
    layer_geom = folium.FeatureGroup(name=name, control=True, show=False, overlay=True)

    for feature in geo_j.data['features']:
        # GEOJSON layer consisting of a single feature
        style = {
            'fillColor': feature['properties']['color'],
            'color': feature['properties']['color'] # line color
            }
        style_function = lambda x: {
            'fillColor': x['properties']['color'],
            'color': x['properties']['color'] # line color
            }
        temp_layer = folium.GeoJson(feature, style_function=style_function)
                    
        popup_dict = {
            'name': name
        }
        for key, value in feature['properties'].items():
            popup_dict[key] = value

        html = rooftop_popup_html(popup_dict)
        iframe = branca.element.IFrame(html=html,width=300,height=150)
        folium.Popup(folium.Html(html, script=True), max_width=500).add_to(temp_layer)

        # consolidate individual features back into the main layer
        temp_layer.add_to(layer_geom)
    return layer_geom

if __name__ == '__main__':
    app.run(debug=True)
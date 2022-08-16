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
    folium.TileLayer('cartodbpositron').add_to(folium_map)
    folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(folium_map)
    
    outlines = open_csv_results(pathlib.Path('workflow/output/rooftops/'), 'rooftops.csv')
    add_outlines_layer(folium_map, outlines, 'rooftops', '#96BDC6')
    
    outlines = open_csv_results(pathlib.Path('workflow/output/sections/'), 'sections.csv')
    add_outlines_layer(folium_map, outlines, 'sections', '#15616D')
    
    outlines = open_csv_results(pathlib.Path('workflow/output/technical/'), 'technical.csv')
    add_outlines_layer(folium_map, outlines, 'technical', '#E3B505')
    
    outlines = open_csv_results(pathlib.Path('workflow/output/economic/'), 'lcoe.csv')
    add_outlines_layer(folium_map, outlines, 'economic', '#81F499')

    folium.LayerControl().add_to(folium_map)
    return folium_map._repr_html_()

def add_outlines_layer(map, outlines, name, color):
    outlines_latlon_copy = deepcopy(outlines)
    geo_j = get_geoj_from_latlon_outlines(outlines_latlon_copy)
    layer_geom = get_layer_from_geoj(name + ' layer', geo_j, color)
    layer_geom.add_to(map)
    
    return

def get_geoj_from_latlon_outlines(outlines):
    gdf_data_center = []
    gdf_data_area = []
    for section in outlines:
        section_geom = shapely.wkt.loads(section['outline_latlon'])

        section_geom = transform(lambda x, y: (y, x), section_geom)
        section['outline_latlon'] = list(section_geom.exterior.coords)
        try:
            gdf_data_center.append((section['center_lat'], section['center_lon']))
            gdf_data_area.append(section['area'])
        except:
            gdf_data_center.append(None)
            gdf_data_area.append(None)

    gdf_data = {}
    gdf_data['gdf_data_center'] = gdf_data_center
    gdf_data['gdf_data_area'] = gdf_data_area
    crs = {'init': 'epsg:4326'}
    polygon_gdf = gpd.GeoDataFrame(
                                   data=gdf_data,
                                   crs=crs,
                                   geometry=[Polygon(section['outline_latlon']) for section in outlines]
                                   )
    geo_j = folium.GeoJson(polygon_gdf)

    return geo_j

def get_layer_from_geoj(name, geo_j, color):
    layer_geom = folium.FeatureGroup(name=name, control=True, show=False)

    for feature in geo_j.data['features']:
        # GEOJSON layer consisting of a single feature
        style = {'fillColor': color, 'lineColor': color, 'color': color}
        temp_layer = folium.GeoJson(feature, style_function=lambda x:style)
        # create Popup and add it to our lone feature
        area = feature['properties']['gdf_data_area']
        outline_center = feature['properties']['gdf_data_center']
        if outline_center == None: outline_center = [1,1]

        popup_dict = {
            'name': 'Rooftop',
            'area': str(int(area * 100) / 100) + ' m2',
            'center': (int(outline_center[0] * 10000) / 10000, int(outline_center[1] * 10000) / 10000)
        }
        html = rooftop_popup_html(popup_dict)
        iframe = branca.element.IFrame(html=html,width=300,height=150)
        folium.Popup(folium.Html(html, script=True), max_width=500).add_to(temp_layer)

        # consolidate individual features back into the main layer
        temp_layer.add_to(layer_geom)
    return layer_geom

if __name__ == '__main__':
    app.run(debug=True)
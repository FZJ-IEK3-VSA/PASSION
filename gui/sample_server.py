""" 
    Start the flask server by running:

        $ python server.py

    And then head to http://127.0.0.1:5000/ in your browser to see the map displayed

"""

from flask import Flask

import geopandas as gpd
from shapely.geometry import Polygon

import folium

app = Flask(__name__)


@app.route('/')
def index():
    start_coords = (50.77595349670269, 6.088548416982711)
    folium_map = folium.Map(location=start_coords, zoom_start=5)

    # TILE LAYERS
    folium.TileLayer('cartodbpositron').add_to(folium_map)
    folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(folium_map)

    # DEFINE POLYGONS
    lat_list_1 = [50.854457, 52.518172, 50.072651, 48.853033, 50.854457]
    lon_list_1 = [4.377184, 13.407759, 14.435935, 2.349553, 4.377184]
    lat_list_2 = [45.12345, 46.12345, 46.12345, 45.12345]
    lon_list_2 = [4.12345, 4.12345, 14.12345, 14.12345]

    polygon_geom_1 = Polygon(zip(lon_list_1, lat_list_1))
    polygon_geom_2 = Polygon(zip(lon_list_2, lat_list_2))
    crs = {'init': 'epsg:4326'}
    polygon_gdf = gpd.GeoDataFrame(
                                   data=['name1', 'name2'],
                                   index=[0, 1],
                                   crs=crs,
                                   geometry=[polygon_geom_1, polygon_geom_2],
                                   columns=['name']
                                   )

    geo_j = folium.GeoJson(polygon_gdf)
    
    layer_geom = folium.FeatureGroup(name='layer1',control=True)

    for feature in geo_j.data['features']:
        print(feature)
        # GEOJSON layer consisting of a single feature
        temp_layer = folium.GeoJson(feature)
        # create Popup and add it to our lone feature
        folium.Popup(feature['properties']['name']).add_to(temp_layer)

        # consolidate individual features back into the main layer
        temp_layer.add_to(layer_geom)
    
    layer_geom.add_to(folium_map)
    
    folium.LayerControl().add_to(folium_map)
    return folium_map._repr_html_()

if __name__ == '__main__':
    app.run(debug=True)
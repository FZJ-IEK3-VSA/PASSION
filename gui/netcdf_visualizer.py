from flask import Flask
import flask
import geopandas as gpd
import shapely
import shapely.wkt
import pathlib
import folium
import rasterio
import xarray
import numpy as np
import pandas as pd

import passion.util

from util import rooftop_popup_html

app = Flask(__name__)


@app.route('/')
def index():
    region = flask.request.args.get('region', default = 'skopje', type = str)
    zoom = flask.request.args.get('zoom', default = 19, type = int)
    n_samples = flask.request.args.get('n_samples', default = 99999999, type = int)
    show_raster = flask.request.args.get('show_raster')
    if not region or not zoom: return 'Please specify a results region name and a zoom level.'
    results_path = pathlib.Path(f'workflow/output/{region}-z{zoom}')
    if not results_path.exists(): return 'The specified results do not exist.'

    pred_opacity = 0.8
    layer_opacity = 0.8
    panel_opacity = 0.95

    sample_satellite = list((results_path / 'satellite').glob('*.tif'))[0]
    sample_src = rasterio.open(sample_satellite)
    zoom_level = int(sample_src.tags().get('zoom_level'))
    west, east, south, north = sample_src.bounds.left, sample_src.bounds.right, sample_src.bounds.bottom, sample_src.bounds.top
    start_coords = passion.util.gis.xy_tolatlon(((west + east) // 2), ((south + north) // 2), zoom_level)
    folium_map = folium.Map(location=start_coords, zoom_start=15, max_zoom=20)

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
    if show_raster is not None:
        print(f'Rendering satellite images...')
        layer = geotiff_folder_to_featuregroup('Source satellite', results_path / 'satellite', num_channels = 3, opacity = 1)
        layer.add_to(folium_map)
        
        print(f'Rendering rooftop predictions...')
        layer = geotiff_folder_to_featuregroup('Rooftop predictions', results_path / 'segmentation/rooftops', num_channels = 1, opacity = pred_opacity)
        layer.add_to(folium_map)
        print(f'Rendering section predictions...')
        layer = geotiff_folder_to_featuregroup('Section predictions', results_path / 'segmentation/sections', num_channels = 1, opacity = pred_opacity)
        layer.add_to(folium_map)
        print(f'Rendering superstructure predictions...')
        layer = geotiff_folder_to_featuregroup('Superstructure predictions', results_path / 'segmentation/superstructures', num_channels = 1, opacity = pred_opacity)
        layer.add_to(folium_map)
    
    
    with xarray.open_dataset(str(results_path / 'economic/lcoe.nc')) as economic_ds:
        print(f'Loaded dataset.')
        # Transform sections WKT to polygons
        wkt_latlon_df = economic_ds.section_wkt_latlon.to_dataframe()
        section_poly_latlon_df = wkt_latlon_df['section_wkt_latlon'].apply(lambda x: shapely.wkt.loads(x))
        section_poly_latlon_df = section_poly_latlon_df.rename('geometry')
        section_poly_lonlat_df = section_poly_latlon_df.apply(lambda x: reverse_geom(x))
        # Transform filtered sections WKT to polygons
        filtered_wkt_latlon_df = economic_ds.filtered_wkt_latlon.to_dataframe()
        filtered_poly_latlon_df = filtered_wkt_latlon_df['filtered_wkt_latlon'].apply(lambda x: shapely.wkt.loads(x))
        filtered_poly_latlon_df = filtered_poly_latlon_df.rename('geometry')
        filtered_poly_lonlat_df = filtered_poly_latlon_df.apply(lambda x: reverse_geom(x))
        # Transform panels WKT to polygons
        pv_wkt_latlon_df = economic_ds.section_pv_layout_wkt.to_dataframe()
        pv_poly_latlon_df = pv_wkt_latlon_df['section_pv_layout_wkt'].apply(lambda x: shapely.wkt.loads(x))
        pv_poly_latlon_df = pv_poly_latlon_df.rename('geometry')
        pv_poly_lonlat_df = pv_poly_latlon_df.apply(lambda x: reverse_geom(x))
        # Transform superstructures WKT to polygons
        superst_wkt_latlon_df = economic_ds.superst_wkt_latlon.to_dataframe()
        superst_poly_latlon_df = superst_wkt_latlon_df['superst_wkt_latlon'].apply(lambda x: shapely.wkt.loads(x))
        superst_poly_latlon_df = superst_poly_latlon_df.rename('geometry')
        superst_poly_lonlat_df = superst_poly_latlon_df.apply(lambda x: reverse_geom(x))
        superst_area_df = economic_ds.superst_area.to_dataframe()

        ds = xarray.open_dataset(str(results_path / 'rooftops/rooftops.nc'))
        id_df = ds.section_id.to_dataframe()
        azimuth_df = economic_ds.section_azimuth.to_dataframe()
        tilt_df = economic_ds.section_tilt.to_dataframe()
        flat_df = economic_ds.section_flat.to_dataframe()
        area_df = economic_ds.section_area.to_dataframe()
        filtered_azimuth_df = economic_ds.filtered_azimuth.to_dataframe()
        filtered_tilt_df = economic_ds.filtered_tilt.to_dataframe()
        filtered_flat_df = economic_ds.filtered_flat.to_dataframe()
        filtered_area_df = economic_ds.filtered_area.to_dataframe()
        panel_area_df = economic_ds.section_panel_area.to_dataframe()
        n_panels_df = economic_ds.section_n_panels.to_dataframe()
        lcoe_df = economic_ds.section_lcoe.to_dataframe()
        yearly_capacity_factor_df = economic_ds.section_yearly_capacity_factor.to_dataframe()
        yearly_system_generation_df = economic_ds.section_yearly_system_generation.to_dataframe()

        seg_class_df = economic_ds.superst_seg_class.to_dataframe()

        sections_df = pd.concat([
            section_poly_lonlat_df, azimuth_df, tilt_df, flat_df, area_df, id_df
        ], axis=1)
        filtered_sections_df = pd.concat([
            filtered_poly_lonlat_df, filtered_azimuth_df, filtered_tilt_df, filtered_flat_df, filtered_area_df
        ], axis=1)
        tech_panels_df = pd.concat([
            pv_poly_lonlat_df, yearly_system_generation_df, panel_area_df, n_panels_df
        ], axis=1)
        econ_panels_df = pd.concat([
            pv_poly_lonlat_df, lcoe_df, panel_area_df, n_panels_df
        ], axis=1)
        superst_df = pd.concat([
            superst_poly_lonlat_df, seg_class_df, superst_area_df
        ], axis=1)
        
        # Transform panels WKT to polygons
        show_existing_panels = (economic_ds.get('panel_pv_layout_wkt') is not None)
        if show_existing_panels:
            existing_yearly_system_generation_df = economic_ds.panel_yearly_system_generation.to_dataframe()
            existing_panel_area_df = economic_ds.panel_area.to_dataframe()
            existing_n_panels_df = economic_ds.panel_n_panels.to_dataframe()

            existing_pv_wkt_latlon_df = economic_ds.panel_pv_layout_wkt.to_dataframe()
            existing_pv_wkt_latlon_df = existing_pv_wkt_latlon_df[existing_pv_wkt_latlon_df != ''].dropna()
            existing_pv_poly_latlon_df = existing_pv_wkt_latlon_df['panel_pv_layout_wkt'].apply(lambda x: shapely.wkt.loads(x))
            existing_pv_poly_latlon_df = existing_pv_poly_latlon_df.rename('geometry')
            existing_pv_poly_lonlat_df = existing_pv_poly_latlon_df.apply(lambda x: reverse_geom(x))

            existing_panels_df = pd.concat([
                existing_pv_poly_lonlat_df, existing_yearly_system_generation_df, existing_panel_area_df, existing_n_panels_df
            ], axis=1)

    sections_gdf = gpd.GeoDataFrame(sections_df.head(n_samples), geometry='geometry')
    sections_gdf.crs = 'EPSG:4326'
    gjson = sections_gdf.to_json()
    geo_j = folium.GeoJson(gjson)
    layer_geom = get_layer_from_geoj('Section layer', geo_j, '#96BDC6', layer_opacity, True)
    layer_geom.add_to(folium_map)
    
    filtered_sections_gdf = gpd.GeoDataFrame(filtered_sections_df.head(n_samples), geometry='geometry')
    filtered_sections_gdf.crs = 'EPSG:4326'
    gjson = filtered_sections_gdf.to_json()
    geo_j = folium.GeoJson(gjson)
    layer_geom = get_layer_from_geoj('Filtered section layer', geo_j, '#FF0000', layer_opacity, True)
    layer_geom.add_to(folium_map)
    
    tech_pv_gdf = gpd.GeoDataFrame(tech_panels_df.head(n_samples), geometry='geometry')
    tech_pv_gdf.crs = 'EPSG:4326'
    gjson = tech_pv_gdf.to_json()
    geo_j = folium.GeoJson(gjson)
    layer_geom = get_layer_from_geoj('Technical layer', geo_j, '#C68E17', panel_opacity, False)
    layer_geom.add_to(folium_map)
    
    econ_pv_gdf = gpd.GeoDataFrame(econ_panels_df.head(n_samples), geometry='geometry')
    econ_pv_gdf.crs = 'EPSG:4326'
    gjson = econ_pv_gdf.to_json()
    geo_j = folium.GeoJson(gjson)
    layer_geom = get_layer_from_geoj('Economic layer', geo_j, '#00FF00', panel_opacity, False)
    layer_geom.add_to(folium_map)
    
    superst_gdf = gpd.GeoDataFrame(superst_df.head(n_samples), geometry='geometry')
    superst_gdf.crs = 'EPSG:4326'
    gjson = superst_gdf.to_json()
    geo_j = folium.GeoJson(gjson)
    layer_geom = get_layer_from_geoj('Superstructure layer', geo_j, '#A98307', layer_opacity, True)
    layer_geom.add_to(folium_map)
    
    if show_existing_panels:
        existing_gdf = gpd.GeoDataFrame(existing_panels_df.head(n_samples), geometry='geometry')
        existing_gdf.crs = 'EPSG:4326'
        gjson = existing_gdf.to_json()
        geo_j = folium.GeoJson(gjson)
        layer_geom = get_layer_from_geoj('Existing panels layer', geo_j, '#FFFF00', panel_opacity, True)
        layer_geom.add_to(folium_map)
    

    folium.LayerControl().add_to(folium_map)
    html_out = folium_map._repr_html_()

    print(f'HTML out...')
    return html_out

def geotiff_folder_to_featuregroup(name: str, path: pathlib.Path, num_channels: int, opacity: float):
    layer_predictions = folium.FeatureGroup(name=name, control=True, show=False, overlay=True)
    for f in (path).glob('*.tif'):
        src = rasterio.open(f)
        zoom_level = int(src.tags().get('zoom_level'))
        c_list = []
        for channel in range(num_channels):
            c = src.read(channel + 1)
            c_list.append(c)
        img = np.dstack(c_list)

        west, east, south, north = src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top
        lat1, lon1 = passion.util.gis.xy_tolatlon(west, north, zoom_level)
        lat2, lon2 = passion.util.gis.xy_tolatlon(east, south, zoom_level)
        folium_img = folium.raster_layers.ImageOverlay(
            name=name,
            image=img,
            bounds=[[lat1, lon1], [lat2, lon2]],
            opacity=opacity,
            interactive=True,
            cross_origin=False,
            zindex=1,
        )
        folium_img.add_to(layer_predictions)
    return layer_predictions

def reverse_geom(geom):
    geom = shapely.ops.transform(lambda x, y: (y, x), geom)
    return geom

def get_layer_from_geoj(name, geo_j, color, opacity, stroke):
    layer_geom = folium.FeatureGroup(name=name, control=True, show=False, overlay=True)

    for feature in geo_j.data['features']:
        # GEOJSON layer consisting of a single feature
        style_function = lambda x: {
            'fillColor': color,
            'color': color,
            'weight': 1,
            'fillOpacity': opacity,
            'opacity': opacity,
            'stroke': stroke
            }
        temp_layer = folium.GeoJson(feature, style_function=style_function)
        
        popup_dict = {
            'name': name
        }
        for key, value in feature['properties'].items():
            popup_dict[key] = value

        html = rooftop_popup_html(popup_dict)
        folium.Popup(folium.Html(html, script=True), max_width=500).add_to(temp_layer)

        # consolidate individual features back into the main layer
        temp_layer.add_to(layer_geom)
    return layer_geom

if __name__ == '__main__':
    app.run(debug=True, port=8082)
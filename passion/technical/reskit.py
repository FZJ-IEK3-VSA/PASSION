import pathlib
import pandas as pd
import reskit as rk
import shapely.geometry
import shapely.wkt
import xarray

import passion.util

def generate_technical(input_path: pathlib.Path,
                       input_filename: str,
                       output_path: pathlib.Path,
                       output_filename: str,
                       merra_path: pathlib.Path,
                       solar_atlas_path: pathlib.Path,
                       minimum_section_area: float,
                       pv_panel_properties: dict
):
  '''Generates a NetCDF file containing the technical potential of the input sections.
  
  Solar simulation is carried out with RESKit. This requires two datasets:
    -ERA5 climate dataset.
    -SARAH solar irradiance dataset.


  ---
  
  input_path            -- Path, folder in which the sections analysis is stored.
  input_filename        -- str, name for the sections analysis file.
  output_path           -- Path, folder in which the technical potential analysis will be stored.
  output_filename       -- str, name for the technical analysis output.
  merra_path            -- Path, folder in which the MERRA-2 dataset is stored.
  solar_atlas_path      -- Path, folder in which the Solar Atlas dataset is stored.
  minimum_section_area  -- float, threshold area to filter sections in square meters.
  pv_panel_properties   -- Path, dictionary containing the properties for the panel simulation.
  '''
  output_path.mkdir(parents=True, exist_ok=True)

  pv_model_id = pv_panel_properties.get('id')
  pv_model_name = pv_panel_properties.get('name')
  pv_model_capacity = pv_panel_properties.get('capacity')
  pv_model_width = pv_panel_properties.get('width')
  pv_model_height = pv_panel_properties.get('height')
  pv_model_price = pv_panel_properties.get('price')
  pv_spacing_factor = pv_panel_properties.get('spacing_factor')
  pv_border_spacing = pv_panel_properties.get('border_spacing')
  pv_n_offset = pv_panel_properties.get('n_offset')

  placements = pd.DataFrame(columns=[
                      'lon', 'lat', 'elev', 'capacity', 'tilt', 'azimuth', 'area',
                      'flat', 'outline_latlon', 'outline_xy', 'original_image_name',
                      #'rooftop_image_name',
                      'n_panels', 'modules_cost'])

  
  if not input_filename.endswith('.nc'):
    input_filename += '.nc'
  with xarray.open_dataset(str(input_path / input_filename)) as sections_ds:
    print(f'Loaded dataset {input_filename}')
    section_id = sections_ds.section_id.to_dataframe()
    section_wkt_latlon = sections_ds.section_wkt_latlon.to_dataframe()
    section_wkt_xy = sections_ds.section_wkt_xy.to_dataframe()
    section_azimuth = sections_ds.section_azimuth.to_dataframe()
    section_tilt = sections_ds.section_tilt.to_dataframe()
    section_flat = sections_ds.section_flat.to_dataframe()
    section_area = sections_ds.section_area.to_dataframe()
    section_img_center_lat = sections_ds.section_img_center_lat.to_dataframe()
    section_img_center_lon = sections_ds.section_img_center_lon.to_dataframe()
    original_image_shape = sections_ds.original_image_width.item(), sections_ds.original_image_height.item()
    zoom_level = sections_ds.zoom_level.item()

    # Create separate dataset for filtered rooftops, and rename variables
    filtered_ds = sections_ds.where(sections_ds.section_area < minimum_section_area, drop=True)
    section_vars = [var for var in list(sections_ds.variables) if 'section_' in var]
    filter_vars = [var.replace('section_','filtered_') for var in section_vars]
    filtered_ds = filtered_ds[section_vars]
    rename_dict = dict(zip(section_vars, filter_vars))
    filtered_ds = filtered_ds.rename(rename_dict)

    sections_df = pd.concat([section_id,
                             section_wkt_latlon,
                             section_wkt_xy,
                             section_azimuth,
                             section_tilt,
                             section_flat,
                             section_area,
                             section_img_center_lat,
                             section_img_center_lon
                             ], axis=1)
    # Rename to remove "section_"
    sections_df.columns = sections_df.columns.str.replace('section_', '')
    print(f'Converted sections to pandas DataFrame, columns: {sections_df.columns}')

    
    superst_id = sections_ds.superst_id.to_dataframe()
    superst_wkt_latlon = sections_ds.superst_wkt_latlon.to_dataframe()
    superst_wkt_xy = sections_ds.superst_wkt_xy.to_dataframe()
    superst_seg_class = sections_ds.superst_seg_class.to_dataframe()
    superst_img_center_lat = sections_ds.superst_img_center_lat.to_dataframe()
    superst_img_center_lon = sections_ds.superst_img_center_lon.to_dataframe()
    superst_area = sections_ds.superst_area.to_dataframe()

    supersts_df = pd.concat([superst_id,
                             superst_wkt_latlon,
                             superst_wkt_xy,
                             superst_seg_class,
                             superst_img_center_lat,
                             superst_img_center_lon,
                             superst_area
                             ], axis=1)
    obstacles_df = supersts_df
    obstacles_ds = xarray.Dataset.from_dataframe(obstacles_df)

    # Rename to remove "superst_"
    supersts_df.columns = supersts_df.columns.str.replace('superst_', '')

    panels_df = supersts_df.drop(supersts_df[supersts_df.seg_class != 1].index)

    print(f'Converted panels to pandas DataFrame, columns: {panels_df.columns}')
    print(f'Converted obstacles to pandas DataFrame, columns: {obstacles_df.columns}')
  
  # CALCULATE SECTIONS
  if not sections_df.empty:
    # Necessary for RESKit: lat, lon, azimuth, tilt, elevation, capacity
    sections_df['poly_latlon'] = sections_df['wkt_latlon'].apply(lambda x: shapely.wkt.loads(x))
    sections_df['poly_xy'] = sections_df['wkt_xy'].apply(lambda x: shapely.wkt.loads(x))
    # filter empty polygons
    sections_df = sections_df[sections_df.poly_latlon.apply(lambda x: not x.is_empty)]
    sections_df['centroid_latlon'] = sections_df['poly_latlon'].apply(lambda x: x.centroid)
    sections_df['lat'] = sections_df['centroid_latlon'].apply(lambda x: x.coords[0][0])
    sections_df['lon'] = sections_df['centroid_latlon'].apply(lambda x: x.coords[0][1])
    sections_df['elev'] = 204.0 #TODO: request elevation from 'https://api.opentopodata.org/v1/'
    # Non necessary for RESKit: area, flat, wkt_latlon, wkt_xy, n_panels, modules_cost
    sections_df['pv_model'] = pv_model_name

    sections_df['gr'] = sections_df['lat'].apply(lambda lat: passion.util.gis.ground_resolution(lat, zoom_level))
    sections_df['pv_pixel_size'] = sections_df['gr'].apply(lambda gr: (pv_model_width / gr, pv_model_height / gr))
    sections_df['pv_border_spacing_pixels'] = sections_df['gr'].apply(lambda gr: pv_border_spacing / gr)

    sections_df['pv_layout_multipoly'] = sections_df.apply(lambda x: passion.util.shapes.get_panel_layout(x.poly_xy,
                                                                                              panel_size=x.pv_pixel_size,
                                                                                              azimuth=x.azimuth,
                                                                                              spacing_factor=pv_spacing_factor,
                                                                                              border_spacing=x.pv_border_spacing_pixels,
                                                                                              n_offset=pv_n_offset),
                                                                                              axis=1)
    sections_df['n_panels'] = sections_df['pv_layout_multipoly'].apply(lambda x: len(x.geoms))
    sections_df = sections_df.drop(sections_df[sections_df.n_panels < 1].index)

  if not sections_df.empty:
    sections_df['pv_layout_wkt'] = sections_df.apply(lambda x: passion.util.shapes.xy_poly_to_latlon(x.pv_layout_multipoly,
                                                                                            (x.img_center_lat, x.img_center_lon),
                                                                                            original_image_shape,
                                                                                            zoom_level).wkt,
                                                                                            axis=1)

    sections_df['panel_area'] = sections_df['n_panels'] * pv_model_width * pv_model_height
    sections_df['modules_cost'] = sections_df['n_panels'] * pv_model_price
    sections_df['capacity'] = sections_df['n_panels'] * pv_model_capacity
    
    sections_df = sections_df[['id', 'lat','lon', 'elev', 'capacity', 'tilt', 'azimuth', 'flat', 'area', 'wkt_latlon', 'wkt_xy',
                              'pv_layout_wkt', 'panel_area', 'n_panels', 'modules_cost', 'pv_model']]

    print(f'Sections columns: {sections_df.columns}')

  
  # CALCULATE PANELS
  if not panels_df.empty:
    # Necessary for RESKit: lat, lon, azimuth, tilt, elevation, capacity
    panels_df['poly_latlon'] = panels_df['wkt_latlon'].apply(lambda x: shapely.wkt.loads(x))
    panels_df['poly_xy'] = panels_df['wkt_xy'].apply(lambda x: shapely.wkt.loads(x))
    # filter empty polygons
    panels_df = panels_df[panels_df.poly_latlon.apply(lambda x: not x.is_empty)]
    panels_df['centroid_latlon'] = panels_df['poly_latlon'].apply(lambda x: x.centroid)
    panels_df['lat'] = panels_df['centroid_latlon'].apply(lambda x: x.coords[0][0])
    panels_df['lon'] = panels_df['centroid_latlon'].apply(lambda x: x.coords[0][1])
    panels_df['elev'] = 204.0 #TODO: request elevation from 'https://api.opentopodata.org/v1/'
    panels_df['azimuth'] = 180.0
    panels_df['tilt'] = 31.0
    # Calculate capacity
    panels_df['gr'] = panels_df['lat'].apply(lambda lat: passion.util.gis.ground_resolution(lat, zoom_level))
    panels_df['pv_pixel_size'] = panels_df['gr'].apply(lambda gr: (pv_model_width / gr, pv_model_height / gr))
    panels_df['pv_border_spacing_pixels'] = panels_df['gr'].apply(lambda gr: pv_border_spacing / gr)
    panels_df['pv_layout_multipoly'] = panels_df.apply(lambda x: passion.util.shapes.get_panel_layout(x.poly_xy,
                                                                                              panel_size=x.pv_pixel_size,
                                                                                              azimuth=x.azimuth,
                                                                                              spacing_factor=1,
                                                                                              border_spacing=0,
                                                                                              n_offset=pv_n_offset),
                                                                                              axis=1)
    panels_df['n_panels'] = panels_df['pv_layout_multipoly'].apply(lambda x: len(x.geoms))
    panels_df = panels_df.drop(panels_df[panels_df.n_panels < 1].index)

  if not panels_df.empty:
    panels_df['pv_layout_wkt'] = panels_df.apply(lambda x: passion.util.shapes.xy_poly_to_latlon(x.pv_layout_multipoly,
                                                                                            (x.img_center_lat, x.img_center_lon),
                                                                                            original_image_shape,
                                                                                            zoom_level).wkt,
                                                                                            axis=1)
    panels_df['panel_area'] = panels_df['n_panels'] * pv_model_width * pv_model_height
    panels_df['modules_cost'] = panels_df['n_panels'] * pv_model_price
    panels_df['capacity'] = panels_df['n_panels'] * pv_model_capacity

    panels_df = panels_df[['id', 'lat','lon', 'elev', 'capacity', 'tilt', 'azimuth', 'wkt_latlon', 'wkt_xy',
                           'area', 'pv_layout_wkt', 'panel_area', 'n_panels', 'modules_cost']]

    print(f'Panels columns: {panels_df.columns}')

  '''
  Possible output_variables:
  Defined by PASSION:
  ['lat', 'lon', 'elev', 'capacity', 'tilt',
  'azimuth', 'flat', 'wkt_latlon', 'wkt_xy',
  'panel_area', 'n_panels', 'modules_cost',
  'pv_model', 'pv_layout_wkt']

  Defined by RESKit:
  ['direct_normal_irradiance', 'global_horizontal_irradiance', 'surface_wind_speed',
  'surface_pressure', 'surface_air_temperature', 'surface_dew_temperature',
  'solar_azimuth', 'apparent_solar_zenith', 'extra_terrestrial_irradiance',
  'air_mass', 'diffuse_horizontal_irradiance', 'angle_of_incidence', 'poa_global',
  'poa_direct', 'poa_diffuse', 'poa_sky_diffuse', 'poa_ground_diffuse',
  'cell_temperature', 'module_dc_power_at_mpp', 'module_dc_voltage_at_mpp',
  'capacity_factor', 'total_system_generation']
  '''
  
  if not sections_df.empty:
    output_variables = [
      'lat', 'lon', 'elev', 'capacity', 'tilt',
      'azimuth', 'flat', 'wkt_latlon', 'wkt_xy',
      'area', 'panel_area', 'n_panels', 'modules_cost',
      'pv_model', 'pv_layout_wkt',
      'capacity_factor', 'total_system_generation'
    ]
    print(f'Simulating sections...')
    technical_ds = rk.solar.openfield_pv_merra_ryberg2019(sections_df,
                                                          str(merra_path),
                                                          str(solar_atlas_path),
                                                          module=pv_model_id,
                                                          output_variables=output_variables
                                                          )
  
  if not panels_df.empty:
    output_variables = [
      'lat', 'lon', 'elev', 'capacity', 'tilt',
      'azimuth', 'wkt_latlon', 'wkt_xy',
      'area', 'panel_area', 'n_panels', 'modules_cost',
      'pv_layout_wkt',
      'capacity_factor', 'total_system_generation'
    ]
    print(f'Simulating existing panels...')
    panels_ds = rk.solar.openfield_pv_merra_ryberg2019(panels_df,
                                                        str(merra_path),
                                                        str(solar_atlas_path),
                                                        module=pv_model_id,
                                                        output_variables=output_variables
                                                        )
  
  # Mean capacity factor by location (annual mean capacity factor)
  if not sections_df.empty:
    yearly_capacity_factor = technical_ds.capacity_factor.fillna(0).mean(dim='time')
    yearly_system_generation = technical_ds.total_system_generation.fillna(0).mean(dim='time') * 365 * 24
    technical_ds = technical_ds.assign(yearly_capacity_factor=yearly_capacity_factor)
    technical_ds = technical_ds.assign(yearly_system_generation=yearly_system_generation)
  # Mean capacity factor by location (annual mean capacity factor)
  if not panels_df.empty:
    yearly_capacity_factor = panels_ds.capacity_factor.fillna(0).mean(dim='time')
    yearly_system_generation = panels_ds.total_system_generation.fillna(0).mean(dim='time')
    panels_ds = panels_ds.assign(yearly_capacity_factor=yearly_capacity_factor)
    panels_ds = panels_ds.assign(yearly_system_generation=yearly_system_generation)

  print(f'Filtered sections variables: {list(filtered_ds.keys())}')
  filtered_wkt_latlon_str, filtered_wkt_xy_str = filtered_ds.filtered_wkt_latlon.astype(str), \
                                                 filtered_ds.filtered_wkt_xy.astype(str)
  filtered_ds = filtered_ds.assign(filtered_wkt_latlon=filtered_wkt_latlon_str, \
                                   filtered_wkt_xy=filtered_wkt_xy_str)
  print(f'Superstructures variables: {list(obstacles_ds.keys())}')
  ds_list = [obstacles_ds, filtered_ds]
  if not sections_df.empty:
    # Rename variables
    current_variables = list(technical_ds.keys())
    print(f'Estimated panels current variables: {current_variables}')
    prefix_variables = [('section_' + var) for var in current_variables]
    rename_dict = dict(zip(current_variables, prefix_variables))
    technical_ds = technical_ds.rename(name_dict=rename_dict)
    new_variables = list(technical_ds.keys())
    print(f'Estimated panels new variables: {new_variables}')
    ds_list.append(technical_ds)
  if not panels_df.empty:
    # Rename variables
    current_variables = list(panels_ds.keys())
    print(f'Existing panels current variables: {current_variables}')
    prefix_variables = [('panel_' + var) for var in current_variables]
    rename_dict = dict(zip(current_variables, prefix_variables))
    panels_ds = panels_ds.rename(name_dict=rename_dict)
    new_variables = list(panels_ds.keys())
    print(f'Existing panels new variables: {new_variables}')
    ds_list.append(panels_ds)
  final_ds = xarray.merge(ds_list)

  if not output_filename.endswith('.nc'):
    output_filename += '.nc'
  final_ds.to_netcdf(str(output_path / output_filename))

  return
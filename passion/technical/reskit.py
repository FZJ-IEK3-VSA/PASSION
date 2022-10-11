import pathlib
import pandas as pd
import reskit as rk
import shapely.geometry
import shapely.wkt

import passion.util

def generate_technical(input_path: pathlib.Path,
                       input_filename: str,
                       output_path: pathlib.Path,
                       output_filename: str,
                       era5_path: pathlib.Path,
                       sarah_path: pathlib.Path,
                       pv_panel_properties: dict
):
  '''Generates a CSV file containing the technical potential of the input sections.

  The CSV file will contain the following columns:
    -lat: float latitude value of the section center.
    -lon: float longitude value of the section center.
    -yearly_gen: yearly estimated generation of the section in Wh.
    -elevation: sea level of the building.
    -capacity: total capacity of the estimated PV system.
    -tilt: estimated tilt of the section. If flat, an optimal value is given.
    -azimuth: estimated orientation of the section. If flat, an optimal value is given.
    -area: estimated area of the section in square meters.
    -flat: int indicating if the section was estimated to be flat (1) or not (0).
    -outline_xy: list of tuples indicating the section outline relative to the original image.
    -outline_latlon: list of tuples indicating the section outline in latitude and longitude.
    -original_image_name: name of the image from which the rooftop was extracted.
    -rooftop_image_name: name of the generated image of the section in the 'img' folder.
    -modules_cost: total estimated cost of the system PV modules.
  
  Solar simulation is carried out with RESKit. This requires two datasets:
    -ERA5 climate dataset.
    -SARAH solar irradiance dataset.


  ---
  
  input_path         -- Path, folder in which the sections analysis is stored.
  input_filename     -- str, name for the sections analysis file.
  output_path        -- Path, folder in which the technical potential analysis will be stored.
  output_filename    -- str, name for the technical analysis output.
  era5_path          -- Path, folder in which the ERA5 dataset is stored.
  sarah_path         -- Path, folder in which the SARAH dataset is stored.
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
                      'rooftop_image_name', 'n_panels', 'modules_cost'])

  sections = passion.util.io.load_csv(input_path, input_filename + '.csv')
  for i, section in enumerate(sections):
    # for the panel layout, we need:
    azimuth = float(section['azimuth'])
    lat = section['center_lat']
    lon = section['center_lon']
    outline_xy_poly = shapely.wkt.loads(section['outline_xy'])
    # panel size meters to pixels
    original_image_name = section['original_image_name']
    _latlon, zoom = passion.util.gis.extract_filename(original_image_name.replace('.png', ''))
    gr = passion.util.gis.ground_resolution(lat, zoom)
    
    pv_size_pixels = (pv_model_width / gr, pv_model_height / gr)
    pv_border_spacing_pixels = pv_border_spacing / gr
    layout_multipolygon = passion.util.shapes.get_panel_layout(outline_xy_poly,
                                           pv_size_pixels,
                                           azimuth,
                                           spacing_factor = pv_spacing_factor,
                                           border_spacing = pv_border_spacing_pixels,
                                           n_offset = pv_n_offset)
    outline_xy = layout_multipolygon.wkt
    n_panels = len(layout_multipolygon.geoms)
    if n_panels > 0:
      # Necessary for RESKit:
      section['capacity'] = pv_model_capacity * n_panels
      capacity = float(section['capacity'])
      tilt = float(section['tilt_angle'])
      section['elevation'] = 204.0 #TODO: request elevation from 'https://api.opentopodata.org/v1/'
      elevation = section['elevation']

      # Not necessary for RESKit:
      area = n_panels * pv_model_width * pv_model_height
      flat = section['flat']

      # Convert panel outline into latlon outline, accounting for the pixel offset
      polygons = []
      for geom in layout_multipolygon.geoms:
        points = []
        for x,y in geom.exterior.coords:
          _bbox = passion.util.gis.get_image_bbox(_latlon, zoom, (1475,2000))
          offset_x, offset_y = passion.util.gis.get_image_offset(_bbox, zoom)
          lat, lon = passion.util.gis.xy_tolatlon(x + offset_x, y + offset_y, zoom)
          points.append((lat, lon))
        polygons.append(shapely.geometry.Polygon(points))
      outline_latlon = shapely.geometry.MultiPolygon(polygons)
      outline_latlon = outline_latlon.wkt

      rooftop_image_name = section['rooftop_image_name']
      modules_cost = float(pv_model_price * n_panels)

      placements.loc['S'+str(i)] = [ lon, lat, elevation, capacity, tilt, azimuth, area,
                                    flat, outline_latlon, outline_xy, original_image_name,
                                    rooftop_image_name, float(n_panels), modules_cost ]

  xds = rk.solar.openfield_pv_sarah_unvalidated(placements, sarah_path, era5_path, module=pv_model_id)

  sections = []
  for i,j in enumerate(xds.location):
    total_gen = passion.util.io.safe_eval((xds.total_system_generation[:, j].fillna(0).mean()*24*365).values)
    lat = passion.util.io.safe_eval((xds.lat[j]).values)
    lon = passion.util.io.safe_eval((xds.lon[j]).values)
    elevation = passion.util.io.safe_eval((xds.elev[j]).values)
    capacity = passion.util.io.safe_eval((xds.capacity[j]).values)
    tilt = passion.util.io.safe_eval((xds.tilt[j]).values)
    azimuth = passion.util.io.safe_eval((xds.azimuth[j]).values)
    area = passion.util.io.safe_eval((xds.area[j]).values)
    flat = passion.util.io.safe_eval((xds.flat[j]).values)
    outline_latlon = passion.util.io.safe_eval((xds.outline_latlon[j]).values)
    outline_xy = passion.util.io.safe_eval((xds.outline_xy[j]).values)
    original_image_name = passion.util.io.safe_eval((xds.original_image_name[j]).values)
    rooftop_image_name = passion.util.io.safe_eval((xds.rooftop_image_name[j]).values)
    n_panels = passion.util.io.safe_eval((xds.n_panels[j]).values)
    modules_cost = passion.util.io.safe_eval((xds.modules_cost[j]).values)
    
    section = {
        'center_lat': lat,
        'center_lon': lon,
        'yearly_gen': total_gen,
        'elevation': elevation,
        'capacity': capacity,
        'tilt': tilt,
        'azimuth': azimuth,
        'area': area,
        'flat': flat,
        'outline_latlon': outline_latlon,
        'outline_xy': outline_xy,
        'rooftop_image_name': rooftop_image_name,
        'original_image_name': original_image_name,
        'n_panels': n_panels,
        'modules_cost': modules_cost
    }

    sections.append(section)

  passion.util.io.save_to_csv(sections, output_path, output_filename)

  return
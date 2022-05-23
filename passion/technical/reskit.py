import pathlib
import pandas as pd
import reskit as rk
import shapely.geometry

import passion.util

class PVModule():
  '''Object representation of a Photovoltaic module.
  Properties of the panel that are interesting for the
  analysis are the module's capacity, area and price.
  '''
  def __init__(self, name, capacity, area, space_factor):
    self.name = name
    self.capacity = capacity
    self.area = area * space_factor
    self.price = 350

DEFAULT_PVMODULE = PVModule('LG370Q1C-A5', 370, 1.7*1.016, 1.4)
DEFAULT_RESKIT_MODULE = 'LG Electronics LG370Q1C-A5'

def set_pv_module(module: PVModule):
  '''Sets the default module for the analysis as a new PVModule.'''
  DEFAULT_PVMODULE = module
  return

def generate_technical(input_path: pathlib.Path,
                       input_filename: str,
                       output_path: pathlib.Path,
                       output_filename: str,
                       era5_path: pathlib.Path,
                       sarah_path: pathlib.Path
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
    -section_image_name: name of the generated image of the section in the 'img' folder.
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

  placements = pd.DataFrame(columns=[
                      'lon', 'lat', 'elev', 'capacity', 'tilt', 'azimuth', 'area',
                      'flat', 'outline_latlon', 'outline_xy', 'original_image_name',
                      'section_image_name', 'n_panels', 'modules_cost'])

  sections = passion.util.io.load_csv(input_path, input_filename + '.csv')
  for i, section in enumerate(sections):
    
    n_panels = section['area'] // DEFAULT_PVMODULE.area
    section['capacity'] = DEFAULT_PVMODULE.capacity * n_panels
    # TODO: request elevation from 'https://api.opentopodata.org/v1/'
    section['elevation'] = 204.0

    # Necessary for RESKit:
    lat = section['center_lat']
    lon = section['center_lon']
    elevation = section['elevation']
    capacity = section['capacity']
    tilt = section['tilt_angle']
    azimuth = section['azimuth']

    # Not necessary for RESKit:
    area = section['area']
    flat = section['flat']
    outline_latlon = shapely.geometry.Polygon(section['outline_latlon']).wkt
    outline_xy = shapely.geometry.Polygon(section['outline_xy']).wkt
    original_image_name = section['original_image_name']
    section_image_name = section['section_image_name']
    modules_cost = DEFAULT_PVMODULE.price * n_panels

    placements.loc['S'+str(i)] = [ lon, lat, elevation, capacity, tilt, azimuth, area,
                                   flat, outline_latlon, outline_xy, original_image_name,
                                   section_image_name, n_panels, modules_cost ]

  xds = rk.solar.openfield_pv_sarah_unvalidated(placements, sarah_path, era5_path, module=DEFAULT_RESKIT_MODULE)

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
    section_image_name = passion.util.io.safe_eval((xds.section_image_name[j]).values)
    modules_cost = passion.util.io.safe_eval((xds.modules_cost[j]).values)
    
    section = {
        'lat': lat,
        'lon': lon,
        'yearly_gen': total_gen,
        'elevation': elevation,
        'capacity': capacity,
        'tilt': tilt,
        'azimuth': azimuth,
        'area': area,
        'flat': flat,
        'outline_latlon': outline_latlon,
        'outline_xy': outline_xy,
        'section_image_name': section_image_name,
        'original_image_name': original_image_name,
        'modules_cost': modules_cost
    }

    sections.append(section)

  passion.util.io.save_to_csv(sections, output_path, output_filename)

  return
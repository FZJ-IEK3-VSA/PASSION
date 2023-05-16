from math import cos, sin, pi, log, atan, exp, floor
import urllib
import urllib.request
from functools import singledispatch
import shapefile
import shapely
from typing import List
from osgeo import osr

'''
Bing Maps conversion helper functions as specified in:
https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
'''
EARTH_RADIUS = 6378137
MINLAT = -85.05112878
MAXLAT = 85.05112878
MINLON = -180
MAXLON = 180
MAXZOOM = 22

def map_width(zoom):
  '''width in pixels of the world map at a given level of detail'''
  return 256 << zoom
def ground_resolution(lat, zoom):
  '''distance on the ground that’s represented by a single pixel in the map'''
  return cos(lat * pi / 180) * 2 * pi * EARTH_RADIUS / map_width(zoom)
def map_scale(lat, zoom, screen_dpi):
  '''ratio between map distance and ground distance'''
  return 0.0254 / (ground_resolution(lat, zoom) * screen_dpi)

def latlon_toXY(lat, lon, zoom):
  '''converts a point from latlon WGS-84 in degrees into the pixel representation in the world map'''
  lat, lon = max(MINLAT, min(MAXLAT, lat)), \
             max(MINLON, min(MAXLON, lon))

  sin_lat = sin(lat * pi/180)
  pixel_x = ((lon + 180) / 360) * map_width(zoom)
  pixel_y = (0.5 - log((1 + sin_lat) / (1 - sin_lat)) / (4 * pi)) * map_width(zoom)

  return floor(pixel_x + 0.5), floor(pixel_y + 0.5)

def xy_tolatlon(pixel_x, pixel_y, zoom):
  '''converts a point from the pixel representation in the world map into latlon WGS-84 in degrees'''
  map_size = map_width(zoom);  
  x = (pixel_x / map_size) - 0.5
  y = 0.5 - pixel_y / map_size

  latitude = 90 - 360 * atan(exp(-y * 2 * pi)) / pi  
  longitude = 360 * x

  return(latitude, longitude)

def xy_totile(pixel_x, pixel_y):
  '''converts a point in pixel coordinates to the coordinates of the tile containing it'''
  return(floor(pixel_x / 256), floor(pixel_y / 256))

def tile_toxy(pixel_x, pixel_y):
  '''converts the coordinates of a tile into the pixel coordinates of its upper-left corner'''
  return(pixel_x * 256, pixel_y * 256)

def get_image_offset(bbox, zoom):
  '''Returns the pixel values of the image offset (upperleft corner) considering map_width.'''
  try:
    (lat1, lon1), (lat2, lon2) = bbox
  except Exception as e:
    raise ValueError('Bounding box must have shape ((lat,lon), (lat,lon)).')
  offset_x1, offset_y1 = latlon_toXY(lat1, lon1, zoom)
  offset_x2, offset_y2 = latlon_toXY(lat2, lon2, zoom)
  offset_x, offset_y = min(offset_x1, offset_x2), min(offset_y1, offset_y2)

  return offset_x, offset_y

def get_image_bbox(latlon: tuple, zoom: int, img_shape: tuple):
  '''Takes the center of an image, its zoom level and its pixel shape and returns the latlon bounding box.
  img_shape is in PIL order! With numpy shapes, it should be inverted.
  '''
  center_lat, center_lon = latlon

  size_y, size_x = img_shape[:2]

  center_x, center_y = latlon_toXY(center_lat, center_lon, zoom)

  min_lat, min_lon = xy_tolatlon(int(center_x - (size_x / 2)), int(center_y - (size_y / 2)), zoom)
  max_lat, max_lon = xy_tolatlon(int(center_x + (size_x / 2)), int(center_y + (size_y / 2)), zoom)

  min_lat, max_lat = min(min_lat, max_lat), max(min_lat, max_lat)
  min_lon, max_lon = min(min_lon, max_lon), max(min_lon, max_lon)

  bbox = ((min_lat, min_lon), (max_lat, max_lon))

  return bbox

def get_filename(latlon: tuple, zoom: int, extension: str = 'png'):
  '''Generates a filename with the format:
  DD[D]MM[M]SSSSS[S][NORTH/SOUTH]DD[D]MM[M]SSSSS[S][WEST/EAST]_LL[L].[EXT]
  
  For example:
  50D40M46461SNORTH_95D48M26533SWEST_19L.png

  Seconds are saved with three decimal places and no decimal separator.
  '''
  lat, lon = latlon

  lat_deg, lat_mnt, lat_sec = dd_to_dms(abs(lat))
  lon_deg, lon_mnt, lon_sec = dd_to_dms(abs(lon))

  lat_deg, lat_mnt, lon_deg, lon_mnt = int(lat_deg), int(lat_mnt), int(lon_deg), int(lon_mnt)

  lat_orientation = 'NORTH' if lat >= 0 else 'SOUTH'
  lon_orientation = 'EAST' if lon >= 0 else 'WEST'

  filename = '{0:02d}D{1:02d}M{2:05d}S{3}_{4:02d}D{5:02d}M{6:05d}S{7}_{8:02d}L.{9}'.format(lat_deg, lat_mnt, int(lat_sec*1000), lat_orientation,
                                                  lon_deg, lon_mnt, int(lon_sec*1000), lon_orientation,
                                                  zoom, extension)
  return filename

def dd_to_dms(dd: float):
  '''Converts decimal degrees into degrees, minutes and seconds.'''
  mnt, sec = divmod(dd*3600, 60)
  deg, mnt = divmod(mnt, 60)
  return deg, mnt, sec

def dms_to_dd(deg: float, mnt: float, sec: float):
  '''Converts degrees, minutes and seconds into decimal degrees.'''
  dd = deg + (mnt / 60.0) + (sec / 3600.0)
  return dd

def extract_filename(name: str):
  '''Extracts latlon and zoom from a filename built following the format in get_filename().'''
  name = name.lower()

  lat_neg = 'south' in name
  lon_neg = 'west' in name

  name = name.replace('north', '').replace('south', '').replace('west', '').replace('east', '')

  split = name.split('_')

  if len(split) != 3:
    print('Error analysing filename, format unknown.')
    return -1

  lat_str = split[0]
  lon_str = split[1]
  zoom_str = split[2]

  lat_deg, lat_mnt, lat_sec = str_to_ddmmss(lat_str)
  lon_deg, lon_mnt, lon_sec = str_to_ddmmss(lon_str)

  lat = dms_to_dd(lat_deg, lat_mnt, lat_sec)
  lon = dms_to_dd(lon_deg, lon_mnt, lon_sec)

  if lat_neg: lat = -lat
  if lon_neg: lon = -lon

  latlon = (lat, lon)

  zoom = int(zoom_str.replace('l', ''))

  return latlon, zoom

def str_to_ddmmss(ddmmss: str):
  '''Extracts a lat/lon into deg, mnt and sec from the format generated in get_filename().'''
  ddmmss = ddmmss.lower()
  ddmmss = ddmmss.replace('d','_').replace('m', '_').replace('s', '')

  split = ddmmss.split('_')
  
  if len(split) != 3:
    print('Error analysing filename, format unknown.')
    return -1

  deg = int(split[0])
  mnt = int(split[1])
  sec = int(split[2]) / 1000

  return deg, mnt, sec

def shape_to_pixels(shape: shapefile.Shape, zoom):
  '''Gets a shapefile.Shape and returns a list of tuples with the coordinates representation.'''
  pixel_points = [latlon_toXY(coord[1], coord[0], zoom) for coord in shape.points]
  return pixel_points

def shape_bbox(shape: shapefile.Shape):
  '''Gets a shapefile.Shape and returns its bounding box.'''

  min_latlon = shape.bbox[1], shape.bbox[2]
  max_latlon = shape.bbox[3], shape.bbox[0]

  return min_latlon, max_latlon

def latlon_to_bbox(minlat: float, minlon: float, maxlat: float, maxlon: float, zoom: int):
  '''Returns ABSOLUTE pixel values for the bounding box of given dimensions'''
  minxy = latlon_toXY(minlat, minlon, zoom)
  maxxy = latlon_toXY(maxlat, maxlon, zoom)

  return [ minxy, (minxy[0], maxxy[1]), maxxy, (maxxy[0], minxy[1]) ]

def polygons_intersect(polygon1, polygon2):
  '''Returns True if polygons expressed as lists IN THE SAME COORDINATE SYSTEM intersect'''
  p1 = shapely.geometry.Polygon(polygon1)
  p2 = shapely.geometry.Polygon(polygon2)
  return p1.intersects(p2)

def substract_offset(polygon, offset_x, offset_y):
  '''Returns the polygon expressed as a list after substracting the given offset'''
  return [(coord[0]-offset_x, coord[1]-offset_y) for coord in polygon]

def get_gdal_transform(extent: List[int], width: int, height: int):
  ''''''
  resx = (extent[2] - extent[0]) / width
  resy = (extent[3] - extent[1]) / height

  return [extent[0], resx, 0, extent[3] , 0, -resy]

def get_gdal_projection(epsg: int):
  ''''''
  projection = osr.SpatialReference()
  projection.ImportFromEPSG(epsg)

  return projection.ExportToWkt()
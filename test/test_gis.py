import passion.util.gis

import pytest
import random
import math

def test_map_width():
  '''
  GIS functions
  https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
  '''
  maxzoom = passion.util.gis.MAXZOOM

  for i in range(1,maxzoom+2):
    assert passion.util.gis.map_width(i) == (256 * (2 ** i))
    
def test_ground_resolution():
  '''
  GIS functions
  https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
  '''
  maxzoom = passion.util.gis.MAXZOOM
  equator_ground_resolution = 78271.517

  for i in range(1,maxzoom+2):
    assert pytest.approx(passion.util.gis.ground_resolution(0, i), 0.001) == equator_ground_resolution / (2 ** (i-1))

def test_map_scale():
  '''
  GIS functions
  https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
  '''
  maxzoom = passion.util.gis.MAXZOOM
  equator_map_scale = 295829355.45

  for i in range(1,maxzoom+2):
    assert pytest.approx(1 / passion.util.gis.map_scale(0, i, 96), 0.001) == equator_map_scale / (2 ** (i-1))

def test_conversions():
  '''
  GIS functions
  https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
  '''
  random.seed(101)

  maxzoom = passion.util.gis.MAXZOOM

  n_random_points = 1000
  for lvl in range(maxzoom):
    for i in range(n_random_points):
      lat = random.uniform(passion.util.gis.MINLAT, passion.util.gis.MAXLAT)
      lon = random.uniform(passion.util.gis.MINLON, passion.util.gis.MAXLON)

      x, y = passion.util.gis.latlon_toXY(lat, lon, lvl + 1)

      calc_lat, calc_lon = passion.util.gis.xy_tolatlon(x, y, lvl + 1)

      # Lat and lon are computed to their pixel representation, causing an error
      # equivalent to the ground resolution (meters)
      # 
      # This is more accentuated for lower levels
      #
      # To convert the ground resolution to latlon representation:
      # meters/latitude_degree = (2*pi/360) * r_earth * cos(lat_degrees)
      # Approx 111km/latitude_degree

      m_degree = (2*math.pi/360)* passion.util.gis.EARTH_RADIUS*math.cos(math.radians(lat))
      m_resolution = passion.util.gis.ground_resolution(lat, lvl + 1)

      # Ground resolution in latitude degrees will be:
      degree_resolution = m_resolution / abs(m_degree)
    
      assert abs(lat) > (abs(calc_lat) - degree_resolution) and abs(lat) < (abs(calc_lat) + degree_resolution)
      assert abs(lon) > (abs(calc_lon) - degree_resolution) and abs(lon) < (abs(calc_lon) + degree_resolution)

    # Converting values out of range
    assert passion.util.gis.latlon_toXY(passion.util.gis.MINLAT-1, 0, lvl) == passion.util.gis.latlon_toXY(passion.util.gis.MINLAT, 0, lvl)
    assert passion.util.gis.latlon_toXY(passion.util.gis.MAXLAT+1, 0, lvl) == passion.util.gis.latlon_toXY(passion.util.gis.MAXLAT, 0, lvl)
    assert passion.util.gis.latlon_toXY(0, passion.util.gis.MINLON-1, lvl) == passion.util.gis.latlon_toXY(0, passion.util.gis.MINLON, lvl)
    assert passion.util.gis.latlon_toXY(0, passion.util.gis.MAXLON+1, lvl) == passion.util.gis.latlon_toXY(0, passion.util.gis.MAXLON, lvl)
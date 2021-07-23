import numpy as np
import PIL
import PIL.ImageDraw
import shapely.geometry
import cv2

import passion.util

def xy_outline_to_latlon(outline_xy: list,
                         img_center_latlon: tuple,
                         img_shape: tuple,
                         zoom: int,
                         lonlat_order: bool = False
):
  '''Takes a list of points in a pixel coordinate system and trasforms it
  into latitude and longitude taking into account the zoom level.

  If lonlat_order is set to True, the returned list will be in
  longitude latitude format instead of latitude longitude.
  '''
  
  img_center_lat, img_center_lon = img_center_latlon
  img_center_x, img_center_y = passion.util.gis.latlon_toXY(img_center_lat, img_center_lon, zoom)
  img_size_y, img_size_x = img_shape
  img_start_x = img_center_x - (img_size_x // 2)
  img_start_y = img_center_y - (img_size_y // 2)

  outline_latlon = []
  for point in outline_xy:
    lat, lon = passion.util.gis.xy_tolatlon(img_start_x + point[0], img_start_y + point[1], zoom)
    new_point = [lon, lat] if lonlat_order else [lat, lon]
    outline_latlon.append(new_point)
  return outline_latlon

def get_outline_center(outline: list):
  '''Given an outline as a list of coordinates, return its center.'''
  center_x, center_y = shapely.geometry.Polygon(outline).centroid.coords.xy
  return (center_x[0], center_y[0])

def get_area(outline_xy: list, center_latlon: tuple, zoom: int):
  '''Given a list of coordinates, the latitude and zoom level,
  returns the area in square meters.
  '''
  polygon = shapely.geometry.Polygon(outline_xy)
  center_latitude = center_latlon[0]
  
  ground_resolution = passion.util.gis.ground_resolution(center_latitude, zoom)

  area = polygon.area
  area_meters = area * (ground_resolution ** 2)
  
  return area_meters

def get_rooftop_image(outline, image):
  '''Given an image and an outline as a list of coordinates, returns the
  filtered image of the rooftop cropped to its bounding box.
  TODO: docstring'''
  poly = shapely.geometry.Polygon(outline)
  minx, miny, maxx, maxy = poly.bounds

  image_portion = image[int(miny):int(maxy), int(minx):int(maxx)]

  outline_image = filter_outline(outline, image)

  outline_image_portion = outline_image[int(miny):int(maxy), int(minx):int(maxx)]

  outline_mask = np.amax(outline_image_portion, 2) != 0

  result = image_portion * np.stack((outline_mask,)*3, axis=-1)

  return result

def filter_outline(outline, image):
  '''Takes an outline in a list of coordinates and a numpy image and returns the
  filtered image using the outline as a mask.
  '''

  size_y, size_x = image.shape[:2]
  
  img_mask_pil = PIL.Image.new('L', (size_x, size_y))
  draw = PIL.ImageDraw.Draw(img_mask_pil, 'L')
  draw.polygon(outline, fill=255, outline=None)

  img_mask = np.asarray(img_mask_pil)
  
  image = image * np.stack((img_mask,)*3, axis=-1)

  return image

def outlines_to_image(polygons, shape):
  '''Takes a list of polygons and an image size, and returns the numpy
  representation of the binary image with the polygons as a mask.'''
  size_y, size_x = shape[:2]

  img_bin = PIL.Image.new('L', (size_x, size_y))
  draw = PIL.ImageDraw.Draw(img_bin, 'L')
  img_bin = PIL.Image.new('L', (size_x, size_y))
  draw = PIL.ImageDraw.Draw(img_bin, 'L')

  for polygon in polygons:
    draw.polygon(polygon, fill=255, outline=None)

  img_bin = np.asarray(img_bin)
  return img_bin

def get_image_rooftops_xy(image: np.ndarray):
  '''Takes a binary image in numpy representation and returns a list
  of polygons as a list of coordinates. The representation is in xy
  format relative to the image.
  '''
  img_size_y, img_size_x = image.shape
  
  ret, thresh = cv2.threshold(image, 127, 255, 0)
  # FOR A SAMPLE, NUMBER OF POINTS
  # CHAIN_APPROX_SIMPLE: 44
  # CHAIN_APPROX_TC89_L1: 25
  # CHAIN_APPROX_TC89_KCOS: 25
  contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)

  poly_list = []
  for contour in contours:
    if len(contour) > 2:
      points = []
      for point in contour:
        points.append((point[0][0], point[0][1]))

      poly = shapely.geometry.Polygon(points)

      poly_list.append(list(poly.exterior.coords))

  return poly_list

def filter_image(image: np.ndarray, mask: np.ndarray):
  '''Filters an image with a binary or grayscale mask.'''
  normalize = max(1, np.amax(mask))

  if len(image.shape) > 2:
      n_channels = image.shape[-1]
      mask = np.stack((mask,)*n_channels, axis=-1)
  
  return (mask // normalize) * image
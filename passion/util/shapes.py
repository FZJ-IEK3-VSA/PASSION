import numpy as np
import PIL
import PIL.ImageDraw
import shapely.geometry
from shapely import affinity
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
  poly = shapely.geometry.Polygon(outline)
  center_x, center_y = shapely.geometry.Polygon(outline).centroid.coords.xy
  return (center_x[0], center_y[0])

def get_area(polygon: shapely.geometry.Polygon, center_latlon: tuple, zoom: int):
  '''Given a polygon in pixel coordinates, the latitude and zoom level,
  returns the area in square meters.
  '''
  polygon = shapely.geometry.Polygon(polygon)
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

def filter_outline(polygon, image):
  '''Takes an outline as a Polygon and a numpy image and returns the
  filtered image using the outline as a mask.
  '''
  outline = polygon.exterior.coords

  size_y, size_x = image.shape[:2]
  
  img_mask_pil = PIL.Image.new('L', (size_x, size_y))
  draw = PIL.ImageDraw.Draw(img_mask_pil, 'L')
  draw.polygon(outline, fill=255, outline=None)

  img_mask = np.asarray(img_mask_pil)
  
  image = image * np.stack((img_mask,)*3, axis=-1)

  return image

def outlines_to_image(polygons, classes, shape):
  '''Takes a list of polygons and an image size, and returns the numpy
  representation of the binary image with the polygons as a mask.'''
  size_y, size_x = shape[:2]

  img_bin = PIL.Image.new('L', (size_x, size_y))
  draw = PIL.ImageDraw.Draw(img_bin, 'L')

  for i, polygon in enumerate(polygons):
    polygon = shapely.geometry.Polygon(polygon)
    shrunken_polygon = polygon.buffer(-2)
    
    # If buffering breaks the polygon, keep the original one
    if (type(shrunken_polygon) == shapely.geometry.MultiPolygon): shrunken_polygon = polygon
    # If buffering empties the polygon, keep the original one
    if shrunken_polygon.is_empty: shrunken_polygon = polygon

    shrunken_polygon_list = list(shrunken_polygon.exterior.coords)
    draw.polygon(shrunken_polygon_list, fill=int(classes[i]), outline=None)

  img_bin = np.asarray(img_bin)
  return img_bin

def get_image_rooftops_xy(image: np.ndarray):
  '''Takes a binary image in numpy representation and returns a list
  of polygons as a list of coordinates. The representation is in xy
  format relative to the image.
  '''
  seg_classes = np.unique(image)[np.unique(image) != 0]
  class_list = []
  polygon_list = []
  for seg_class in seg_classes:
    image_class = image.copy()
    image_class = (image_class == seg_class).astype(np.uint8)
    
    contours, hierarchy = cv2.findContours(image_class, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)
    
    for contour in contours:
      if len(contour) > 2:
        points = []
        for point in contour:
          points.append((point[0][0], point[0][1]))
        poly = shapely.geometry.Polygon(points)
        # Fix invalid polygons
        poly = poly.buffer(0)
        # TODO: deal multipolygons
        if poly.geom_type == 'MultiPolygon':
          poly = list(poly.geoms)[0]
        
        polygon_list.append(poly)
        class_list.append(seg_class)
  
  return class_list, polygon_list

def filter_image(image: np.ndarray, mask: np.ndarray):
  '''Filters an image with a binary or grayscale mask.'''
  mask = (mask != 0).astype(int)

  if len(image.shape) > 2:
      n_channels = image.shape[-1]
      mask = np.stack((mask,)*n_channels, axis=-1)
  
  return mask * image

def get_layout(outline, panel_size, azimuth, spacing_factor, border_spacing, offset):
  '''
  Takes an outline, a panel size, azimuth, spacing factor,
  minimum space to the border and starting offset for
  the grid, and returns the list of found panels.
  '''
  panel_width, panel_height = panel_size
  
  cell_width  = panel_width * spacing_factor
  cell_height = panel_height * spacing_factor

  grid_cells = []
  outter_cells = []
  panel_cells = []

  # get polygon bbox oriented to 0 degrees
  xmin, ymin, xmax, ymax = outline.bounds
  xmin += offset
  ymin += offset
  xmax += offset
  ymax += offset
  
  bbox = shapely.geometry.Polygon([(xmin,ymin),(xmin,ymax),(xmax,ymax),(xmax,ymin),(xmin,ymin)])

  # Shrink objective polygon by offset in order to have space in the borders
  outline = outline.buffer(-border_spacing)
  for x0 in np.arange(xmin, xmax, cell_width):
    for y0 in np.arange(ymin, ymax, cell_height):
      # getting the installation bbox from the grid
      x1 = x0+cell_width
      y1 = y0+cell_height
      new_cell = shapely.geometry.box(x0, y0, x1, y1)
      new_cell = affinity.rotate(new_cell, -azimuth, origin=bbox.centroid)

      # shrinking the bbox to get the actual panel bbox
      panel_x0 = x0+((cell_width - panel_width)/2)
      panel_y0 = y0+((cell_height - panel_height)/2)
      panel_x1 = panel_x0+panel_width
      panel_y1 = panel_y0+panel_height
      panel_cell = shapely.geometry.box(panel_x0, panel_y0, panel_x1, panel_y1)
      panel_cell = affinity.rotate(panel_cell, -azimuth, origin=bbox.centroid)

      # if the installation space is inside the rooftop, add it
      if new_cell.within(outline):
        grid_cells.append(new_cell)
        panel_cells.append(panel_cell)
      else:
        outter_cells.append(new_cell)
  return panel_cells

def get_panel_layout(outline: shapely.geometry.Polygon,
                     panel_size: tuple,
                     azimuth: float,
                     spacing_factor: float,
                     border_spacing: int,
                     n_offset: int,
                    ):
  '''
  Takes an outline, a panel size, azimuth and spacing factor,
  and returns a shapely.geometry.MultiPolygon object of the
  found layout of panels inside the outline.
  Tries n_offset times both the vertical and horizontal
  layouts, starting the grid on a different offset
  to find the optimal.
  '''
  if n_offset < 1: n_offset = 1
  panel_width, panel_height = panel_size

  cell_length  = max(panel_width, panel_height) * spacing_factor
  
  panel_cells = []
  for offset in np.arange(0, cell_length, cell_length / n_offset):
    p_h = get_layout(outline, (panel_width, panel_height), azimuth, spacing_factor, border_spacing, offset)
    if len(p_h) > len(panel_cells):
      panel_cells = p_h
    p_v = get_layout(outline, (panel_height, panel_width), azimuth, spacing_factor, border_spacing, offset)
    if len(p_v) > len(panel_cells):
      panel_cells = p_v

  return shapely.geometry.MultiPolygon(panel_cells)
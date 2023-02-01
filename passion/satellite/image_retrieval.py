import pathlib
import urllib
from urllib import request
import shapefile
import PIL.Image
import numpy as np
import tqdm
import math
import traceback
import pkg_resources
import mahotas.polygon
import rasterio

import passion.util

# MAXIMUM SIZE THAT THE APIs ALLOW TO RETRIEVE
MAX_WIDTH_BING, MAX_HEIGHT_BING = 2000, 1500
MAX_WIDTH_GOOGLE, MAX_HEIGHT_GOOGLE = 640, 640

# SIZE OF THE WATERMARK IN ORDER TO REMOVE IT
WATERMARK_BING = 25
WATERMARK_GOOGLE = 40

# GETTING RESOURCES FROM /data FOLDER, NEEDED TO CHECK NULL IMAGES
SATELLITE_DATA_PATH = pathlib.Path(__file__).parent.resolve() / 'data'
NULL_IMAGE_BING_PATH = SATELLITE_DATA_PATH / 'bing_null_image.png'
NULL_IMAGE_GOOGLE_PATH = SATELLITE_DATA_PATH / 'google_null_image_1280.png'
NULL_IMAGE_BING = PIL.Image.open(NULL_IMAGE_BING_PATH)
NULL_IMAGE_GOOGLE = PIL.Image.open(NULL_IMAGE_GOOGLE_PATH)

def generate_dataset(
  api_key: str,
  service: str,
  output_path: pathlib.Path,
  zoom: int = passion.util.gis.MAXZOOM,
  bbox: tuple = None,
  shapefile: shapefile.Shape = None,
  find_valid_zoom: bool = False
):
  '''Generate satellite tiles of a region into an output folder.

  Lat and Lon indicate the center of the image and are written using ISO6709
  removing all separating characters to avoid conflicts in the filenames.

  50°40′46.461″N 95°48′26.533″W
  with a zoom level of 19 would be:
  50D40M46461SNORTH_95D48M26533SWEST_19L.tif

  One of bbox or shapefile must be specified in order to define a region.
  If both are specified, shapefile is taken.
  TODO: if both are specified, select the bbox inside the shapefile
  ---
  
  api_key           -- string, API key of the specified service
  service           -- string, currently must be one of 'bing' or 'google'
  output_path       -- Path, folder in which tiles will be stored
  zoom              -- integer, zoom level (https://docs.microsoft.com/en-us/bingmaps/articles/understanding-scale-and-resolution)
  bbox              -- tuple of tuples of floats: ((lat1, lon1), (lat2, lon2))
  shapefile         -- shapefile, used for filtering
  find_valid_zoom   -- bool, finds the next available zoom level if True
  '''
  if bbox == None and shapefile == None:
    raise ValueError('Either bbox and/or shapefile must be specified.')

  if bbox == None:
      bbox = passion.util.gis.shape_bbox(shapefile)
  try:
    (lat1, lon1), (lat2, lon2) = bbox
  except Exception as e:
    raise ValueError('Bounding box must have shape ((lat,lon), (lat,lon)).')

  output_path.mkdir(parents=True, exist_ok=True)
  
  watermark = WATERMARK_GOOGLE if service =='google' else WATERMARK_BING
  request_width = MAX_WIDTH_GOOGLE if service =='google' else MAX_WIDTH_BING
  request_height = MAX_HEIGHT_GOOGLE if service =='google' else MAX_HEIGHT_BING

  finished = False
  minimum_zoom = 0 if find_valid_zoom else (zoom - 1)
  for z in range(zoom, minimum_zoom, -1):
    if finished: break
    
    offset_x, offset_y = passion.util.gis.get_image_offset(bbox, zoom)

    northwest_x1, northwest_y1 = passion.util.gis.latlon_toXY(lat1, lon1, zoom)
    northwest_x2, northwest_y2 = passion.util.gis.latlon_toXY(lat2, lon2, zoom)
    northwest_x1, northwest_x2 = min(northwest_x1, northwest_x2), max(northwest_x1, northwest_x2)
    northwest_y1, northwest_y2 = min(northwest_y1, northwest_y2), max(northwest_y1, northwest_y2)

    # START CENTER INSTEAD OF BORDER
    x1 = northwest_x1 + (request_width//2)
    y1 = northwest_y1 + ((request_height)//2)

    current_x = x1
    current_y = y1

    valid_request = True

    print('Trying zoom level: {0}'.format(zoom))
    print('Map pixels from\t({0},{1})\nTo\t({2},{3})'.format(northwest_x1,northwest_y1,northwest_x2,northwest_y2))

    # x=0, y=0 is at lat=90 lon=-180
    total = math.ceil(abs(x1-northwest_x2)/request_width) * math.ceil(abs(y1-northwest_y2)/request_height)
    pbar = tqdm.tqdm(total=total, position=0, leave=True)
    while ((current_y  < northwest_y2) and valid_request):
      while ((current_x < northwest_x2) and valid_request):
        # Current image center latlon values
        current_lat, current_lon = passion.util.gis.xy_tolatlon(current_x, current_y, zoom)

        try:
          #TODO: adjust image center at the width and height borders, so that we cover the exact area
          limit_x, limit_y = current_x + request_width, current_y + request_height
          image_bbox = [ (current_x, current_y), (current_x, limit_y), (limit_x, limit_y), (limit_x, current_y) ]

          image_intersects = True
          if shapefile:
            shapefile_pixels = passion.util.gis.shape_to_pixels(shapefile, zoom)
            shapefile_pixels_corrected = passion.util.gis.substract_offset(shapefile_pixels, offset_x, offset_y)
            shapefile_pixels_relative = passion.util.gis.substract_offset(shapefile_pixels_corrected, current_x-offset_x, current_y-offset_y)
            
            image_intersects = passion.util.gis.polygons_intersect(shapefile_pixels, image_bbox)
          
          if image_intersects:
            img = retrieve_image(api_key, service, (current_lat, current_lon), (request_width, request_height), zoom)

            if (is_null_image(img, service)):
              raise RuntimeError('Null image retrieved, {0} level of detail not available.'.format(zoom))
            
            # WATERMARK ADJUSTMENT
            img = img.crop((0,0,request_width,request_height-watermark))
            tmp_x, tmp_y = passion.util.gis.latlon_toXY(current_lat, current_lon, zoom)
            current_lat, current_lon = passion.util.gis.xy_tolatlon(tmp_x, tmp_y - (watermark//2), zoom)

            if shapefile:
              img = filter_image_shapefile(img, shapefile_pixels_relative)
            
            filename = passion.util.gis.get_filename((current_lat, current_lon), zoom)
            #save_img(img, output_path, filename)

            tif_name = filename.replace('.png', '.tif')
            img_np = np.asarray(img)
            height, width, channels = img_np.shape
            img_rgb = np.moveaxis(img_np, -1, 0)
            west, north, east, south = (current_x - (width//2), current_y + (height//2) - (watermark//2), current_x + (width//2), current_y - (height//2) - (watermark//2))
            transform = rasterio.transform.from_bounds(west=west,
                                                       south=south,
                                                       east=east,
                                                       north=north,
                                                       width=width,
                                                       height=height)
            # https://epsg.io/3857
            crs = rasterio.CRS.from_epsg(3857)

            new_dataset = rasterio.open(str(output_path / tif_name), 'w', driver='GTiff',
                                        height = height, width = width,
                                        count=3, dtype=str(img_rgb.dtype),
                                        crs=crs,
                                        transform=transform)
            new_dataset.update_tags(zoom_level=zoom)
            new_dataset.write(img_rgb)
            new_dataset.close()
        
        except Exception as e:
          #TODO: handle specific exceptions
          print(traceback.format_exc())
          valid_request = False
          pbar.close()


        current_x += request_width
        pbar.update(1)
      current_x = x1
      current_y += request_height - watermark
    pbar.close()
    if valid_request: finished = True

def is_null_image(img, service):
  '''Checks if a retrieved image is null by comparing it
  with the image that each service returns when
  making an invalid request.'''
  null_image = NULL_IMAGE_GOOGLE if service == 'google' else NULL_IMAGE_BING

  nonzero = np.count_nonzero(np.array(img) == np.array(null_image))
  total = (np.array(img) == np.array(null_image)).size

  return (nonzero / total > 0.8)

def filter_image_shapefile(img: PIL.Image, shapefile_pixels_relative: list):
  '''Filter image leaving only the intersection with a shapefile.
  Rest of the image pixels will have a value of (0,0,0).'''
  img_arr = np.array(img)
  canvas = np.zeros(img_arr.shape, dtype=int)

  polygon_arr = np.array(shapefile_pixels_relative)
  polygon_arr[:,1][polygon_arr[:,1]>(img.height-1)] = (img.height - 1)
  polygon_arr[:,0][polygon_arr[:,0]>(img.width-1)] = (img.width - 1)
  polygon_arr[polygon_arr<0] = 0
  polygon_arr[:,[0, 1]] = polygon_arr[:,[1, 0]]

  mahotas.polygon.fill_polygon(polygon_arr, canvas)
  masked = (img_arr * canvas).astype(np.uint8)

  img = PIL.Image.fromarray(masked)

  return img

def save_img(img: PIL.Image, output_path: pathlib.Path, filename):
  '''Saves a PIL Image into a pathlib Path with a given filename.'''
  img.save(output_path / filename)
  return

def retrieve_image(
  api_key: str,
  service: str,
  latlon: tuple,
  size: tuple,
  zoom: int
):
  '''Retrieve a single image from a given service at a latlon and zoom level'''
  if service != 'bing' and service != 'google':
    raise ValueError('Service must be either "bing" or "google"')
  
  width, height = size

  url = get_url(api_key, latlon, zoom, (width, height), service)

  n_tries = 0
  success = False
  while not (success or n_tries > 10):
    try:
      img = img_from_url(url)
      success = True
    except urllib.error.URLError:
      n_tries += 1
  if not success: raise urllib.error.URLError('URL connection error')
  
  return img


def img_from_url(url: str, timeout: int=120):
  '''Get an image from the http response of a url.'''
  http_response = urllib.request.urlopen(url, timeout=timeout)
  img = PIL.Image.open(http_response)
  return img

def get_url(
  api_key: str,
  latlon: tuple,
  zoom: int,
  size: tuple,
  service: str
  ):
  '''Returns a valid URL for a given service and location data.
  service must be either 'bing' or 'google', and ValueError
  is raised otherwise.
  
  size is a tuple (width, height) in pixels
  '''
  lat, lon = latlon
  width, height = size

  latlon_str = '{0},{1}'.format(lat, lon)
  mapsize = '{0},{1}'.format(width, height)

  url = ''

  if service == 'bing':
    base_url = 'https://dev.virtualearth.net/REST/v1/Imagery/Map/{0}/{1}/{2}?&mapSize={3}&key={4}'
    url = base_url.format('Aerial', latlon_str, zoom, mapsize, api_key)

  elif service == 'google':
    base_url = 'https://maps.googleapis.com/maps/api/staticmap?'

    parameters = [
      'center={0},{1}'.format(lat, lon),
      'zoom={0}'.format(zoom),
      'size={0}x{1}'.format(width, height),
      'scale={0}'.format(1),
      'maptype={0}'.format('satellite'),
      'key={0}'.format(api_key)
    ]

    url = base_url + '&'.join(parameters)

  else:
    raise ValueError('Service must be either "bing" or "google"')

  return url
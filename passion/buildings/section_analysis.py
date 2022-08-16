import pathlib
import cv2
import shapely.geometry
import shapely.ops
import numpy as np
import tqdm
import math

import passion.util

SUPERSTRUCTURE_FACTOR = 0.8
def set_superstructure_factor(factor: float):
  '''Changes the default area reduction factor that
  accounts for the removal of superstructures.

  The factor is 0.8 by default.
  '''
  SUPERSTRUCTURE_FACTOR = factor
  return

def generate_sections(input_path: pathlib.Path,
                      input_filename: str,
                      output_path: pathlib.Path,
                      output_filename: str,
                      tilt_distribution_path: pathlib.Path
):
  '''Generates a CSV file containing the detected sections of the input rooftops.
  It will also generate an 'img' folder containing the filtered image of each
  section, with the same naming convention as the previous images with the
  latitude and longitude values of the center of the section.

  The CSV file will contain the following columns:
    -rooftop_id: id of the rooftop as part of a single analysis.
    -section_id: id of the section as part of a single analysis.
    -flat: int indicating if the section was estimated to be flat (1) or not (0).
    -azimuth: estimated orientation of the section. If flat, an optimal value is given.
    -tilt_angle: estimated tilt of the section. If flat, an optimal value is given.
    -outline_xy: list of tuples indicating the section outline relative to the original image.
    -outline_latlon: list of tuples indicating the section outline in latitude and longitude.
    -outline_lonlat: list of tuples indicating the section outline in longitude and latitude.
    -center_lat: float latitude value of the section center.
    -center_lon: float longitude value of the section center.
    -area: estimated area of the section in square meters.
    -original_image_name: name of the image from which the rooftop was extracted.
    -section_image_name: name of the generated image of the section in the 'img' folder.

  The methodology to detect tilted rooftops is specified in process_rooftop().

  A tilt distribution is given as input in order to generate new rooftop tilt values from
  a ground truth.


  ---
  
  input_path              -- Path, folder in which the rooftop analysis is stored.
  input_filename          -- str, name for the rooftops analysis file.
  output_path             -- Path, folder in which section analysis will be stored.
  output_filename         -- str, name for the sections analysis file.
  tilt_distribution_path  -- Path, folder in which the tilt distribution is stored.
  '''
  output_path.mkdir(parents=True, exist_ok=True)
  img_output_path = output_path / 'img'
  img_output_path.mkdir(parents=True, exist_ok=True)

  tilt_distribution = passion.util.io.load_pickle(tilt_distribution_path)

  rooftops = passion.util.io.load_csv(input_path, input_filename + '.csv')

  sections = []

  for rooftop in tqdm.tqdm(rooftops):
    tilt_angle = get_tilt(tilt_distribution)
    img_path = input_path / 'img' / rooftop['rooftop_image_name']
    filename = img_path.stem
    rooftop_image = passion.util.io.load_image(img_path)

    rooftop['image'] = rooftop_image
    rooftop['tilt_angle'] = tilt_angle

    _, zoom = passion.util.gis.extract_filename(filename)
    img_center_latlon = rooftop['img_center_latlon']
    img_shape = rooftop['original_img_shape']

    rooftop_sections = process_rooftop(rooftop)

    sections = sections + rooftop_sections

    for section in rooftop_sections:
      outline_latlon = passion.util.shapes.xy_outline_to_latlon(section['outline_xy'], img_center_latlon, img_shape, zoom)
      section['outline_latlon'] = shapely.geometry.Polygon(outline_latlon).wkt
      outline_lonlat = passion.util.shapes.xy_outline_to_latlon(section['outline_xy'], img_center_latlon, img_shape, zoom, lonlat_order=True)
      section['outline_latlon'] = shapely.geometry.Polygon(outline_latlon).wkt

      center_latlon = passion.util.shapes.get_outline_center(outline_latlon)
      section['center_lat'], section['center_lon'] = center_latlon

      area = passion.util.shapes.get_area(section['outline_xy'], center_latlon, zoom)

      section['area'] = area * SUPERSTRUCTURE_FACTOR

      section['original_image_name'] = rooftop['original_image_name']
      section['section_image_name'] = passion.util.gis.get_filename(center_latlon, zoom)

      img_output_path.mkdir(parents=True, exist_ok=True)
      
      passion.util.io.save_image(section['image'], img_output_path, section['section_image_name'])
      section.pop('image', None)

  passion.util.io.save_to_csv(sections, output_path, output_filename)
  return

def get_tilt(tilt_distribution):
  '''Extracts a new tilt value from a given distribution.'''
  tilt = tilt_distribution.resample(1)[0][0]
  return tilt

def get_optimal_azimuth(latitude):
  '''Returns the optimal panel azimuth orientation.
  180º (south) for positive latitudes and 0º (north) for negative latitudes
  '''
  return 180 if latitude > 0 else 0

def get_optimal_tilt(latitude):
  '''Returns the optimal panel tilt angle for a given latitude.
  TODO: improve it calculating based on latitude.
  '''
  return 31

def process_rooftop(rooftop):
  '''Takes a rooftop and tries to detect the straight ridge line that separates two sections.
  Method should be improved in order to account for more complex shapes.
  
  Edges are first detected with a Canny detector in order to extract the
  first detected Hough line. A 3-class K-Means segmentation is performed in parallel
  and if the previous line divides its classes correctly with a given threshold,
  the rooftop division into sections is considered.

  Returns a list of dictionaries containing the information of the detected section (flat rooftop)
  or sections (tilted rooftop). 
  '''
  r_id = rooftop['rooftop_id']
  outline = rooftop['outline_xy']
  image_portion = rooftop['image']
  
  sections = []

  #TODO: for flat sections, save optimal value of tilt and orientation instead of 0
  flat_section = dict()
  flat_section['rooftop_id'] = r_id
  flat_section['section_id'] = 0
  flat_section['flat'] = 1.0
  center_latitude = rooftop['center_lat']
  flat_section['azimuth'] = get_optimal_azimuth(center_latitude)
  flat_section['tilt_angle'] = get_optimal_tilt(center_latitude)
  flat_section['outline_xy'] = outline
  flat_section['image'] = image_portion

  polygon = shapely.geometry.Polygon(outline)
  minx, miny, maxx, maxy = polygon.bounds
  outline_rel = [(pair[0]-minx, pair[1]-miny) for pair in outline]
  polygon_rel = shapely.geometry.Polygon(outline_rel)

  # K-means segmentation
  background_class = 0
  segmented_image = segment_kmeans(image_portion, k=3)
  gray_segmented_image = cv2.cvtColor(segmented_image, cv2.COLOR_BGR2GRAY)

  # Edge detection
  edges_image = get_edges(image_portion)

  # Hough lines
  lines = None
  threshold = 255

  while (lines is None):
    lines = cv2.HoughLines(edges_image, 5, np.pi / 180, threshold, np.array([]))

    threshold = threshold - 10
    if threshold < 0: return [flat_section]
    if lines is None: continue
    
    line = lines[0]
    angle = get_angle(line)
    # also needed because of later reference #
    rho = line[0][0]
    theta = line[0][1]
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 1000*(-b))
    y1 = int(y0 + 1000*(a))
    x2 = int(x0 - 1000*(-b))
    y2 = int(y0 - 1000*(a))
    #########################################

    upper_perp, lower_perp = get_perpendiculars(angle)

    correct_pixels = 0
    total_pixels = 0
    section_imgs = []

    # for every value in gray_segmented_image (k-means class) that is not the background class:
    # aka for every potential section (2 classes):
    for s_id in np.unique(gray_segmented_image[gray_segmented_image != background_class]):
      n_class = len(gray_segmented_image[gray_segmented_image == s_id].flatten())
      n_total = len(gray_segmented_image[gray_segmented_image != background_class].flatten())
      # if the line divides more than the 75% of the image pixels, discard
      if (n_class / n_total > 0.75): return [flat_section]

      # img_line is used to flood the image and separate the sections
      img_line = np.zeros(image_portion.shape[:-1], np.uint8)
      cv2.line(img_line,(x1,y1),(x2,y2),255,1)
      # for every pixel:
      for i in range(img_line.shape[0]): 
        for j in range(img_line.shape[1]):
          # if it is not yet flooded, flood and add it as a section:
          if (img_line[i][j] == 0):
            previous = img_line.copy()
            cv2.floodFill(img_line, None, (j,i), 1)
            mask = img_line - previous

            section = gray_segmented_image * mask
            section = section[section != background_class]
            n_pixels = len(section)
            max_n = 0
            for color in np.unique(section):
                max_n = max(max_n, len(section[section == color]))
            correct_pixels = correct_pixels + max_n
            total_pixels = total_pixels + n_pixels

            section_img = image_portion * np.stack((mask,)*3, axis=-1)
            section_imgs.append(section_img)
      
      if (len(section_imgs) < 2): return [flat_section]

      line = shapely.geometry.LineString([(x1,y1), (x2,y2)])
      line_abs = shapely.geometry.LineString([(x1+minx,y1+miny), (x2+minx,y2+miny)])
      res_rel = shapely.ops.split(polygon_rel, line)
      res_abs = shapely.ops.split(polygon, line_abs)
      
      assert len(res_rel) == len(res_abs)

    for s_id, (poly_rel, poly_abs) in enumerate(zip(res_rel, res_abs)):
      # check if centroid of segment polygon is on top or on bottom of ridge
      xA, yA = poly_rel.centroid.xy[0][0], poly_rel.centroid.xy[1][0]
      _x1, _y1 = line.xy[0][0], line.xy[1][0]
      _x2, _y2 = line.xy[0][1], line.xy[1][1]

      _v1 = (_x2-_x1, _y2-_y1)
      _v2 = (_x2-xA, _y2-yA)
      xp = _v1[0]*_v2[1] - _v1[1]*_v2[0]  # Cross product

      if xp > 0:
        # on top
        orient = upper_perp
      else:
        # on bottom
        orient = lower_perp
      section_img = passion.util.shapes.get_rooftop_image(list(poly_rel.exterior.coords), image_portion)
      if section_img.size != 0:
        section = {'rooftop_id': r_id, 'section_id': s_id, 'flat': 0.0, 'azimuth': orient, 'tilt_angle': rooftop['tilt_angle'], 'outline_xy': list(poly_abs.exterior.coords), 'image': section_img}
        sections.append(section)

  result = correct_pixels / total_pixels
  result_threshold = 0.75

  if result < result_threshold: return [flat_section]

  return sections

def get_angle(line):
  '''Given a line in parameter space, with rho and theta
  representation, extract the angle in degrees with respect
  to north (Y axis).
  '''
  rho = line[0][0]
  theta = line[0][1]
  a = np.cos(theta)
  b = np.sin(theta)
  x0 = a*rho
  y0 = b*rho
  x1 = int(x0 + 1000*(-b))
  y1 = int(y0 + 1000*(a))
  x2 = int(x0 - 1000*(-b))
  y2 = int(y0 - 1000*(a))
  angle = math.atan2(y1 - y2, x1 - x2) * 180 / np.pi - 90
  return angle

def get_perpendiculars(angle):
  '''Gets the two perpendicular angles of a given angle in degrees.'''
  perpendiculars = [(angle + 90) % 360, (angle - 90) % 360]
  upper_perp = perpendiculars[0] if perpendiculars[0] <= 90 or perpendiculars[0] >= 270 else perpendiculars[1]
  lower_perp = perpendiculars[0] if perpendiculars[0] > 90 and perpendiculars[0] < 270 else perpendiculars[1]
  assert (upper_perp != lower_perp)
  return upper_perp, lower_perp

def segment_kmeans(image_portion, k=3):
  '''Given a numpy image and a number of classes,
  get the numpy image of the K-Means segmentation.
  '''
  pixel_values = image_portion.reshape((-1, 3))
  pixel_values = np.float32(pixel_values)
  criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
  
  _, labels, (centers) = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
  centers = np.uint8(centers)
  labels = labels.flatten()
  segmented_image = centers[labels.flatten()]
  segmented_image = segmented_image.reshape(image_portion.shape)
  return segmented_image

def get_edges(image_portion):
  '''Given a RGB numpy image, gets the edges detected by Canny.
  
  The default preprocessing steps are:
    - Image smoothing
    - Grayscale conversion
    - Histogram equalization
    - Canny detection
  
  The method can be overwritten with any transformations.
  '''
  # Image smoothing
  #smoothed_image = cv2.GaussianBlur(image_portion,(5,5),0)
  #smoothed_image = cv2.medianBlur(image_portion,5)
  smoothed_image = cv2.bilateralFilter(image_portion,9,75,75)
  # Grayscale conversion
  gray_image = cv2.cvtColor(smoothed_image, cv2.COLOR_BGR2GRAY)
  # Histogram equalization
  #equalized_image = cv2.equalizeHist(gray_image)
  clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
  equalized_image = clahe.apply(gray_image)
  # Canny edge detection
  edges_image = cv2.Canny(equalized_image,100,200)
  return edges_image
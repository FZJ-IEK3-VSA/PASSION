import pathlib
import cv2
import numpy as np
import tqdm
import shapely

import passion.util

def generate_rooftops(predictions_path: pathlib.Path,
                      superstructure_predictions_path: pathlib.Path,
                      output_path: pathlib.Path,
                      output_filename: str,
                      superstructures_output_filename: str,
                      tilt_distribution_path: pathlib.Path,
                      minimum_area: int = 25
):
  '''Generates a CSV file containing the detected rooftops of the input segmentations.
  It will also generate an 'img' folder containing the filtered image of each
  rooftop, with the same naming convention as the previous images with the
  latitude and longitude values of the center of the rooftop.

  The CSV file will contain the following columns:
    -rooftop_id: id of the rooftop as part of a single analysis.
    -outline_xy: list of tuples indicating the rooftop outline relative to the original image.
    -outline_latlon: list of tuples indicating the rooftop outline in latitude and longitude.
    -outline_lonlat: list of tuples indicating the rooftop outline in longitude and latitude.
    -center_latlon: tuple of the latitude and longitude of the center of the rooftop.
    -area: estimated area of the rooftop in square meters.
    -original_image_name: name of the image from which the rooftop was extracted.
    -rooftop_image_name: name of the generated image of the rooftop in the 'img' folder.


  ---
  
  predictions_path  -- Path, folder in which segmentation masks and filtered images are stored.
  output_path       -- Path, folder in which rooftop analysis will be stored.
  output_filename   -- str, name for the rooftops analysis file.
  minimum_area      -- int, minimum area in square meters to consider a rooftop for the analysis.
  '''
  output_path.mkdir(parents=True, exist_ok=True)
  img_output_path = output_path / 'img'
  img_output_path.mkdir(parents=True, exist_ok=True)

  rooftops = []
  superstructures = []
  paths = predictions_path.glob('*_MASK*')
  pbar = tqdm.tqdm(paths)
  for mask_path in pbar:
    superstructures_mask_path = superstructure_predictions_path / mask_path.name
    filename = mask_path.stem.replace('_MASK','')
    folder = mask_path.parents[0]
    extension = mask_path.suffix
    filtered_path = folder / (filename + '_FILTERED' + extension)

    img_mask = passion.util.io.load_image(mask_path)
    img_filtered = passion.util.io.load_image(filtered_path)
    superstructure_img_mask = passion.util.io.load_image(superstructures_mask_path)

    img_shape = img_mask.shape
    
    img_center_latlon, zoom = passion.util.gis.extract_filename(filename)

    class_list, rooftop_outlines = passion.util.shapes.get_image_rooftops_xy(img_mask)
    superstructure_class_list, superstructure_outlines = passion.util.shapes.get_image_rooftops_xy(superstructure_img_mask)
    
    print(f'Number of rooftops: {len(rooftop_outlines)}')
    if rooftop_outlines:
      class_list, rooftop_outlines = tuple(zip(*[(c, poly) for (c, poly) in zip(class_list, rooftop_outlines) if not poly.is_empty]))
      print(f'Number of rooftops after removing empty polygons: {len(rooftop_outlines)}')
      # Filter out inner polygons (holes)
      filter_outlines = []
      for i, r_a in enumerate(rooftop_outlines):
        for j, r_b in enumerate(rooftop_outlines):
          if i != j:
            if r_a.contains(r_b):
              filter_outlines.append(j)
      class_list, rooftop_outlines = passion.util.shapes.filter_polygon_holes(class_list, rooftop_outlines)
      print(f'Number of rooftops after filtering holes: {len(rooftop_outlines)}')
    
    print(f'Number of superstructures: {len(superstructure_outlines)}')
    if superstructure_outlines:
      superstructure_class_list, superstructure_outlines = tuple(zip(*[(c, poly) for (c, poly) in zip(superstructure_class_list, superstructure_outlines) if not poly.is_empty]))
      print(f'Number of superstructures after removing empty polygons: {len(superstructure_outlines)}')
      filter_outlines = []
      for i, r_a in enumerate(superstructure_outlines):
        for j, r_b in enumerate(superstructure_outlines):
          if i != j:
            if r_a.contains(r_b):
              filter_outlines.append(j)
      superstructure_class_list, superstructure_outlines = passion.util.shapes.filter_polygon_holes(superstructure_class_list, superstructure_outlines)
      print(f'Number of superstructures after filtering holes: {len(superstructure_outlines)}')

    # rooftop_outline is relative to image!
    for r_id, rooftop_outline in enumerate(rooftop_outlines):
      # Treat PV and obstacles first to reduce suitable area
      for s_id, superstructure_outline in enumerate(superstructure_outlines):
        if superstructure_outline.intersects(rooftop_outline):
          rooftop_outline = rooftop_outline.difference(superstructure_outline)
          # Only process superstructure if it overlaps an outline:
          # TODO: superstructures that are part of multiple rooftops
          # will be processed twice
          superstructure = dict()
          superstructure['type'] = superstructure_class_list[s_id]
          superstructure['outline_xy'] = superstructure_outline.wkt
          s_outline_latlon = passion.util.shapes.xy_outline_to_latlon(superstructure_outline, img_center_latlon, img_shape, zoom)
          superstructure['outline_latlon'] = s_outline_latlon.wkt
          s_center_lat, s_center_lon = passion.util.shapes.get_outline_center(s_outline_latlon)
          superstructure['area'] = passion.util.shapes.get_area(superstructure_outline, (s_center_lat, s_center_lon), zoom)
      
          superstructures.append(superstructure)
      
      # If outline is empty after filtering, remove it
      if rooftop_outline.is_empty: break

      rooftop = dict()
      rooftop['rooftop_id'] = r_id

      rooftop['outline_xy'] = rooftop_outline.wkt
      outline_latlon = passion.util.shapes.xy_outline_to_latlon(rooftop_outline, img_center_latlon, img_shape, zoom)
      rooftop['outline_latlon'] = outline_latlon.wkt

      rooftop['img_center_latlon'] = img_center_latlon
      rooftop['center_lat'], rooftop['center_lon'] = passion.util.shapes.get_outline_center(outline_latlon)
      rooftop['area'] = passion.util.shapes.get_area(rooftop_outline, (rooftop['center_lat'], rooftop['center_lon']), zoom)

      rooftop['original_image_name'] = mask_path.name.replace('_MASK', '')
      rooftop['original_img_shape'] = img_shape

      if rooftop['area'] > minimum_area:
        # Flat rooftop
        if class_list[r_id] == 17:
          rooftop['azimuth'] = 180
          rooftop['tilt_angle'] = 31
          rooftop['flat'] = 1.0
        else:
          rooftop['azimuth'] = get_azimuth_from_segmentation(class_list[r_id])
          tilt_distribution = passion.util.io.load_pickle(tilt_distribution_path)
          rooftop['tilt_angle'] = get_tilt(tilt_distribution)
          rooftop['flat'] = 0.0

        rooftop_image = passion.util.shapes.get_rooftop_image(rooftop_outline, img_filtered)
        rooftop['rooftop_image_name'] = passion.util.gis.get_filename((rooftop['center_lat'], rooftop['center_lon']), zoom)

        passion.util.io.save_image(rooftop_image, img_output_path, rooftop['rooftop_image_name'])

        rooftops.append(rooftop)
  
  passion.util.io.save_to_csv(rooftops, output_path, output_filename)
  passion.util.io.save_to_csv(superstructures, output_path, superstructures_output_filename)

  return

def get_tilt(tilt_distribution):
  '''Extracts a new tilt value from a given distribution.'''
  tilt = tilt_distribution.resample(1)[0][0]
  return tilt

def get_azimuth_from_segmentation(predicted: int):
  '''TODO: docstring'''
  num_classes = 16
  unit = 360 / num_classes

  # Substract one because we changed the background class to 0
  azimuth = (predicted - 1) * unit

  return azimuth 
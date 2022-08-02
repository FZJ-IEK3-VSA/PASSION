import pathlib
import cv2
import numpy as np
import tqdm
import shapely

import passion.util

def generate_rooftops(predictions_path: pathlib.Path,
                      output_path: pathlib.Path,
                      output_filename: str,
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
  paths = predictions_path.glob('*_MASK*')
  pbar = tqdm.tqdm(paths)
  for mask_path in pbar:
    #print('Processing image: '+str(mask_path))
    filename = mask_path.stem.replace('_MASK','')
    folder = mask_path.parents[0]
    extension = mask_path.suffix
    filtered_path = folder / (filename + '_FILTERED' + extension)

    img_mask = passion.util.io.load_image(mask_path)
    img_filtered = passion.util.io.load_image(filtered_path)

    img_shape = img_mask.shape
    
    img_center_latlon, zoom = passion.util.gis.extract_filename(filename)

    rooftop_outlines = passion.util.shapes.get_image_rooftops_xy(img_mask)

    # Filter out inner polygons (holes)
    filter_outlines = []
    for i, r_a in enumerate(rooftop_outlines):
      for j, r_b in enumerate(rooftop_outlines):
        if i != j:
          if shapely.geometry.Polygon(r_a).contains(shapely.geometry.Polygon(r_b)):
            filter_outlines.append(j)

    rooftop_outlines = [r for i, r in enumerate(rooftop_outlines) if i not in filter_outlines]

    # rooftop_outline is relative to image!
    for r_id, rooftop_outline in enumerate(rooftop_outlines):

      rooftop_image = passion.util.shapes.get_rooftop_image(rooftop_outline, img_filtered)
      
      rooftop = dict()
      rooftop['rooftop_id'] = r_id
      rooftop['outline_xy'] = rooftop_outline
      
      rooftop['outline_latlon'] = passion.util.shapes.xy_outline_to_latlon(rooftop['outline_xy'], img_center_latlon, img_shape, zoom)
      rooftop['outline_lonlat'] = passion.util.shapes.xy_outline_to_latlon(rooftop['outline_xy'], img_center_latlon, img_shape, zoom, lonlat_order=True)
      rooftop['center_latlon'] = passion.util.shapes.get_outline_center(rooftop['outline_latlon'])
      rooftop['area'] = passion.util.shapes.get_area(rooftop['outline_xy'], rooftop['center_latlon'], zoom)
      rooftop['original_image_name'] = mask_path.name.replace('_MASK', '')

      if rooftop['area'] > minimum_area:
        rooftop['rooftop_image_name'] = passion.util.gis.get_filename(rooftop['center_latlon'], zoom)

        passion.util.io.save_image(rooftop_image, img_output_path, rooftop['rooftop_image_name'])

        rooftops.append(rooftop)
  
  passion.util.io.save_to_csv(rooftops, output_path, output_filename)

  return

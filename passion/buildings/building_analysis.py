import pathlib
import cv2
import numpy as np
import tqdm
import shapely
import rasterio
import xarray

import passion.util

def analyze_rooftops(rooftop_predictions_path: pathlib.Path,
                      section_predictions_path: pathlib.Path,
                      superstructure_predictions_path: pathlib.Path,
                      output_path: pathlib.Path,
                      output_filename: str,
                      superstructures_output_filename: str,
                      tilt_distribution_path: pathlib.Path,
                      simplification_distance: float,
                      merge_style: str = 'union',
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

  rooftop_paths = sorted(rooftop_predictions_path.glob('*_MASK*'))
  section_paths = sorted(section_predictions_path.glob('*_MASK*'))
  superstructure_paths = sorted(superstructure_predictions_path.glob('*_MASK*'))
  zip_paths = zip(rooftop_paths, section_paths, superstructure_paths)

  tilt_distribution = passion.util.io.load_pickle(tilt_distribution_path)

  if merge_style not in ['union', 'prioritize-rooftops', 'intersection']: merge_style = 'union'

  final_sections = {}
  final_supersts = {}
  for img_i, (rooftop_path, section_path, superst_path) in tqdm.tqdm(enumerate(zip_paths)):
    print(f'Analyzing image {img_i}...')
    partial_sections = {}
    partial_supersts = {}

    rooftop_filename = rooftop_path.stem.replace('_MASK','')
    rooftop_folder = rooftop_path.parents[0]
    rooftop_extension = rooftop_path.suffix

    # Load all three segmented images
    rooftop_src = rasterio.open(rooftop_path)
    rooftop_img = rooftop_src.read(1)
    section_src = rasterio.open(section_path)
    section_img = section_src.read(1)
    superst_src = rasterio.open(superst_path)
    superst_img = superst_src.read(1)
  
    zoom = int(rooftop_src.tags().get('zoom_level'))
    img_center_x, img_center_y = section_src.xy(section_src.height // 2, section_src.width // 2)
    img_center_lat, img_center_lon = passion.util.gis.xy_tolatlon(img_center_x, img_center_y, zoom)
  
    # Extract all of the polygons
    rooftop_classes, rooftops = passion.util.shapes.get_image_classes_xy(rooftop_img, simplification_distance)
    section_classes, sections = passion.util.shapes.get_image_classes_xy(section_img, simplification_distance)
    superst_classes, supersts = passion.util.shapes.get_image_classes_xy(superst_img, simplification_distance)
    if rooftops:
      rooftops_tuple = tuple(zip(*[(c, poly) for (c, poly) in zip(rooftop_classes, rooftops) if not poly.is_empty]))
      if len(rooftops_tuple) == 2: rooftop_classes, rooftops = rooftops_tuple
    if sections:
      sections_tuple = tuple(zip(*[(c, poly) for (c, poly) in zip(section_classes, sections) if not poly.is_empty]))
      if len(sections_tuple) == 2: section_classes, sections = sections_tuple
    if supersts:
      superst_tuple = tuple(zip(*[(c, poly) for (c, poly) in zip(superst_classes, supersts) if not poly.is_empty]))
      if len(superst_tuple) == 2: superst_classes, supersts = superst_tuple

    print(f'Retrieved {len(rooftops)} rooftops.')
    print(f'Retrieved {len(sections)} sections.')
    print(f'Retrieved {len(supersts)} superstructures.')

    if rooftops: rooftop_classes, rooftops = passion.util.shapes.filter_polygon_holes(rooftop_classes, rooftops)
    if sections: section_classes, sections = passion.util.shapes.filter_polygon_holes(section_classes, sections)
    if supersts: superst_classes, supersts = passion.util.shapes.filter_polygon_holes(superst_classes, supersts)

    print(f'Retrieved {len(rooftops)} rooftops after filtering holes.')
    print(f'Retrieved {len(sections)} sections after filtering holes.')
    print(f'Retrieved {len(supersts)} superstructures after filtering holes.')

    # - Sections that are outside of detected rooftops will be filtered out
    # - Sections that intersect with rooftops will be filtered from the rooftop available area
    # - Rooftops that do not have any sections will be treated as flat rooftops
    optimal_tilt = 31
    for i, rooftop in enumerate(rooftops):
      if not rooftop.is_valid: print(f'Invalid rooftop: {i}')
      for j, (section, section_class) in enumerate(zip(sections, section_classes)):
        if not section.is_valid: print(f'Invalid section: {j}')
        if rooftop.intersects(section):
          try:
            if merge_style != 'union': section = section.intersection(rooftop)
            # Filter the section area from the rooftop
            rooftop = rooftop.difference(section)
            # If it has not been added before (intersects with another rooftop), add it
            if f'i{img_i}s{j}' not in partial_sections:
              flat = 1 if section_class==17 else 0
              azimuth = get_azimuth_from_segmentation(section_class)
              tilt = optimal_tilt if flat else get_tilt(tilt_distribution)

              partial_sections[f'i{img_i}s{j}'] = {'polygon_xy': section,
                                      'azimuth': azimuth,
                                      'tilt': tilt,
                                      'flat': flat,
                                      'original_img_center_latlon': (img_center_lat, img_center_lon),
                                      'area': passion.util.shapes.get_area(section, (img_center_lat, img_center_lon), zoom)
                                      }
          except:
            print(f'Exception with intersecting processing polygons:')
            print(type(section))
            print(type(rooftop))
            print(section.wkt)
            print(rooftop.wkt)
      # After filtering its sections, add it if it is not empty
      if merge_style != 'intersection' and not rooftop.is_empty:
        partial_sections[f'i{img_i}r{i}'] = {'polygon_xy': rooftop,
                                  'azimuth': 180,
                                  'tilt': optimal_tilt,
                                  'flat': 1,
                                  'original_img_center_latlon': (img_center_lat, img_center_lon),
                                  'area': passion.util.shapes.get_area(rooftop, (img_center_lat, img_center_lon), zoom)
                                }
    # - Superstructures that are outside of detected rooftops will be filtered out
    # - Superstructures that intersect with rooftops/sections will be filtered from the available area
    for k, v in list(partial_sections.items()):
      poly = v['polygon_xy']
      v['superstructures'] = []
      for i, (superst, superst_class) in enumerate(zip(supersts, superst_classes)):
        intersects = False
        try:
          intersects = poly.intersects(superst)
        except Exception as e:
          print(f'Exception with intersecting processing polygons:')
          print(type(poly))
          print(type(superst))
          print(poly.wkt)
          print(superst.wkt)

        if intersects:
          # Filter the superstructure area from the section
          try:
            # Keep only the part of the superstructure inside of the section
            superst = superst.intersection(poly)
            poly = poly.difference(superst)
          except:
            print(f'Encountered exception processing polygons:')
            print(type(poly))
            print(type(superst))
            print(poly.wkt)
            print(superst.wkt)
          if i not in partial_supersts and superst.is_valid and (superst.geom_type == 'Polygon' or superst.geom_type == 'MultiPolygon'):
            # TODO: add area and other info
            partial_supersts[i] = {
              'class': superst_class,
              'polygon_xy': superst,
              'original_img_center_latlon': (img_center_lat, img_center_lon),
              'area': passion.util.shapes.get_area(superst, (img_center_lat, img_center_lon), zoom)
            }
      # If polygon has become a Geometrycollection, remove non polygons
      if poly.geom_type == 'GeometryCollection':
        polys = []
        [polys.append(p) for p in poly.geoms if p.geom_type == 'Polygon']
        poly = shapely.geometry.MultiPolygon(polys)

      if poly.geom_type == 'Polygon' or poly.geom_type == 'MultiPolygon':
        partial_sections[k].update({'polygon_xy': poly})
      else:
        # Debug why the poly is not a (multi)poly
        print(f'Found non polygon shape:')
        print(poly.geom_type)
        del partial_sections[k]

    # Convert polygons to latlon
    for section_k, section_v in partial_sections.items():
      latlon_poly = passion.util.shapes.xy_poly_to_latlon(section_v['polygon_xy'],
                                                          (img_center_lat, img_center_lon),
                                                          section_img.shape,
                                                          zoom)
      partial_sections[section_k].update({'polygon_latlon': latlon_poly})
    for superst_k, superst_v in partial_supersts.items():
      latlon_poly = passion.util.shapes.xy_poly_to_latlon(superst_v['polygon_xy'],
                                                          (img_center_lat, img_center_lon),
                                                          superst_img.shape,
                                                          zoom)
      partial_supersts[superst_k].update({'polygon_latlon': latlon_poly})
    final_sections.update(partial_sections)
    final_supersts.update(partial_supersts)
  
  # Create and store NetCDF
  section_ids, section_polygons_xy, section_polygons_latlon, section_centers_lat, section_centers_lon, section_azimuths, section_tilts, section_flats, section_areas = [], [], [], [], [], [], [], [], []
  for section_k, section_v in final_sections.items():
    section_ids.append(section_k)
    section_polygons_xy.append(section_v['polygon_xy'].wkt)
    section_polygons_latlon.append(section_v['polygon_latlon'].wkt)
    section_centers_lat.append(section_v['original_img_center_latlon'][0])
    section_centers_lon.append(section_v['original_img_center_latlon'][1])
    section_azimuths.append(section_v['azimuth'])
    section_tilts.append(section_v['tilt'])
    section_flats.append(section_v['flat'])
    section_areas.append(section_v['area'])

  superst_ids, superst_polygons_xy, superst_polygons_latlon, superst_centers_lat, superst_centers_lon, superst_classes, superst_areas = [], [], [], [], [], [], []
  for superst_k, superst_v in final_supersts.items():
    superst_ids.append(superst_k)
    superst_polygons_xy.append(superst_v['polygon_xy'].wkt)
    superst_polygons_latlon.append(superst_v['polygon_latlon'].wkt)
    superst_centers_lat.append(superst_v['original_img_center_latlon'][0])
    superst_centers_lon.append(superst_v['original_img_center_latlon'][1])
    superst_classes.append(superst_v['class'])
    superst_areas.append(superst_v['area'])

  sections_ds = xarray.Dataset(
    data_vars=dict(
        zoom_level=([], zoom),
        original_image_width=([], rooftop_img.shape[0]),
        original_image_height=([], rooftop_img.shape[1]),
        # Sections
        section_wkt_latlon=(['section_id'], section_polygons_latlon, 
                    {
                        'type': 'str',
                        'str_format': 'wkt'
                    }),
        section_wkt_xy=(['section_id'], section_polygons_xy, 
                    {
                        'type': 'str',
                        'str_format': 'wkt'
                    }),
        section_img_center_lat=(['section_id'], section_centers_lat, 
                    {
                        'type': 'float'
                    }),
        section_img_center_lon=(['section_id'], section_centers_lon, 
                    {
                        'type': 'float'
                    }),
        section_azimuth=(['section_id'], section_azimuths, 
                    {
                        'type': 'float'
                    }),
        section_tilt=(['section_id'], section_tilts, 
                    {
                        'type': 'float'
                    }),
        section_flat=(['section_id'], section_flats, 
                    {
                        'type': 'float'
                    }),
        section_area=(['section_id'], section_areas, 
                    {
                        'type': 'float'
                    }),
        # Superstructures
        superst_seg_class=(['superst_id'], superst_classes, 
                    {
                        'type': 'int',
                        'possible_values': [1,2,3,4,5,6,7,8],
                        'description': '1 for panels'
                    }),
        superst_img_center_lat=(['superst_id'], superst_centers_lat, 
                    {
                        'type': 'float'
                    }),
        superst_img_center_lon=(['superst_id'], superst_centers_lon, 
                    {
                        'type': 'float'
                    }),
        superst_wkt_latlon=(['superst_id'], superst_polygons_latlon, 
                    {
                        'type': 'str',
                        'str_format': 'wkt'
                    }),
        superst_wkt_xy=(['superst_id'], superst_polygons_xy, 
                    {
                        'type': 'str',
                        'str_format': 'wkt'
                    }),
        superst_area=(['superst_id'], superst_areas, 
                    {
                        'type': 'float'
                    }),
    ),
    coords=dict(
        section_id=(['section_id'], section_ids, 
                     {
                         'description': 'Format: rooftops r<ID>, sections s<ID>.'
                     }),
        superst_id=(['superst_id'], superst_ids, # TODO: two dimensions: pv panels and rest of obstacles (keeping the class)
                     {
                         'description': 'Format: <ID>.'
                     })
    ),
    attrs=dict(description="Detected sections in region"),
  )

  if not output_filename.endswith('.nc'):
    output_filename += '.nc'
  sections_ds.to_netcdf(str(output_path / output_filename))

  return

def get_tilt(tilt_distribution):
  '''Extracts a new tilt value from a given distribution.'''
  tilt = tilt_distribution.resample(1)[0][0]
  return tilt

def get_azimuth_from_segmentation(predicted: int):
  '''TODO: docstring'''
  if predicted == 17: return 180

  num_classes = 16
  unit = 360 / num_classes

  # Substract one because we changed the background class to 0
  azimuth = (predicted - 1) * unit

  return azimuth 
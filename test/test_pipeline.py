import pytest
import os
import pathlib
import tensorflow as tf
import shutil

import passion

TEMP_FILE_PATH = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "temp"

def test_image_retrieval():
  '''Tests the image retrieval from Bing Maps.'''
  API_KEY = "AhjPfWmuVxVrZGQfVEnguF1rPWTNWfT9lOFx1kb3COXPoAsDNpmK5N3DBUDfQ6cr"
  output_path = TEMP_FILE_PATH / 'satellite'

  # just define a small example set in order to avoid problems with open street map
  passion.satellite.image_retrieval.generate_dataset(API_KEY, 'bing', output_path, zoom = 19, 
    bbox=((50.77850739604879, 6.0768084397936395), (50.77514558009357, 6.081035433169415))
  )

  assert len(list(output_path.glob('*.png'))) == 2

@pytest.mark.skip(reason="Rate limit of OSM API")
def test_get_osm_footprint():
  '''Tests the OSM retrieval from Overpass.'''
  passion.segmentation.osm.generate_osm(TEMP_FILE_PATH, TEMP_FILE_PATH)

def test_get_segmentation_prediction():
  '''Tests the segmentation output from the model.'''
  model_path = TEMP_FILE_PATH / '../../workspace/results/model/rooftop_segmentation.h5'
  input_path = TEMP_FILE_PATH / 'satellite'
  output_path = TEMP_FILE_PATH / 'segmentation'

  model = tf.keras.models.load_model(str(model_path))
  
  passion.segmentation.prediction.segment_dataset(input_path = input_path, model = model, output_path = output_path)

def test_get_rooftops():
  '''Tests the rooftop prediction from the segmentation masks.'''
  
  input_path = TEMP_FILE_PATH / 'segmentation'
  output_path = TEMP_FILE_PATH / 'rooftops'

  passion.buildings.rooftop_analysis.generate_rooftops(input_path, output_path, 'rooftops')

  rooftops = passion.util.io.load_csv(output_path, 'rooftops.csv')
  images = list((output_path / 'rooftops').glob('*.png'))
  
  assert len(rooftops) == len(images)

def test_get_sections():
  '''Tests the section analysis from the rooftops CSV.'''
  tilt_path = TEMP_FILE_PATH / '../data/tilt_distribution.pkl'
  input_path = TEMP_FILE_PATH / 'rooftops'
  output_path = TEMP_FILE_PATH / 'sections'

  passion.buildings.section_analysis.generate_sections(input_path, 'rooftops', output_path, 'sections', tilt_path)

  sections = passion.util.io.load_csv(output_path, 'sections.csv')
  images = list((output_path / 'sections').glob('*.png'))
  
  assert len(sections) == len(images)

  shutil.rmtree(TEMP_FILE_PATH)
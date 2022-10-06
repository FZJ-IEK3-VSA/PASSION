import pytest
import os
import pathlib
import torch
import shutil

import passion

TEMP_FILE_PATH = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "tmp"

def test_image_retrieval():
  '''Tests the image retrieval from Bing Maps.'''
  API_KEY = "AhjPfWmuVxVrZGQfVEnguF1rPWTNWfT9lOFx1kb3COXPoAsDNpmK5N3DBUDfQ6cr"
  output_path = TEMP_FILE_PATH / 'satellite'

  # just define a small example set in order to avoid problems with open street map
  passion.satellite.image_retrieval.generate_dataset(API_KEY, 'bing', output_path, zoom = 19, 
    bbox=((50.77850739604879, 6.0768084397936395), (50.77514558009357, 6.081035433169415))
  )

  assert len(list(output_path.glob('*.png'))) == 1

@pytest.mark.skip(reason="Rate limit of OSM API")
def test_get_osm_footprint():
  '''Tests the OSM retrieval from Overpass.'''
  passion.segmentation.osm.generate_osm(TEMP_FILE_PATH, TEMP_FILE_PATH)

def test_get_segmentation_prediction():
  '''Tests the segmentation output from the model.'''
  model_path = TEMP_FILE_PATH / '../../workflow/output/model/rooftop-segmentation/model_best.pth'
  input_path = TEMP_FILE_PATH / 'satellite'
  output_path = TEMP_FILE_PATH / 'segmentation'
  rooftops_output_path = output_path / 'rooftops'
  superstructures_output_path = output_path / 'superstructures'

  device = 'cuda' if torch.cuda.is_available() else 'cpu'
  model = torch.load(str(model_path), map_location=torch.device(device))

  passion.segmentation.prediction.segment_dataset(
        input_path = input_path,
        model = model,
        output_path = rooftops_output_path,
        background_class = 17
        )
  
  model_path = TEMP_FILE_PATH / '../../workflow/output/model/pv-segmentation/model_best.pth'
  model = torch.load(str(model_path), map_location=torch.device(device))

  passion.segmentation.prediction.segment_dataset(
        input_path = input_path,
        model = model,
        output_path = superstructures_output_path,
        background_class = 8
        )

def test_get_rooftops():
  '''Tests the rooftop prediction from the segmentation masks.'''
  
  input_path = TEMP_FILE_PATH / 'segmentation'
  rooftops_input_path = input_path / 'rooftops'
  superstructures_input_path = input_path / 'superstructures'
  output_path = TEMP_FILE_PATH / 'rooftops'
  rooftops_output_name = 'rooftops'
  superstructures_output_name = 'superstructures'
  tilt_distribution_path = TEMP_FILE_PATH / '../data/tilt_distribution.pkl'

  passion.buildings.rooftop_analysis.generate_rooftops(rooftops_input_path,
                                                     superstructures_input_path,
                                                     output_path,
                                                     rooftops_output_name,
                                                     superstructures_output_name,
                                                     tilt_distribution_path,
                                                     )

  rooftops = passion.util.io.load_csv(output_path, rooftops_output_name + '.csv')
  images = list((output_path / 'img').glob('*.png'))
  
  assert len(rooftops) == len(images)

  shutil.rmtree(TEMP_FILE_PATH)
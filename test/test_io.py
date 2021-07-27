import passion.util.io

import os
import pytest
import random
import pathlib
import shutil
import numpy as np


TEMP_FILE_PATH = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "temp"

def test_image():
  ''''''
  random.seed(101)

  tmp_path = pathlib.Path('tmp')
  tmp_path.mkdir(parents=True, exist_ok=True)

  blank_image = np.zeros((512, 512, 3), np.uint8)
  image_name = 'image.png'

  passion.util.io.save_image(blank_image, tmp_path, image_name)
  loaded_image = passion.util.io.load_image(tmp_path / image_name)
  
  shutil.rmtree(tmp_path)

  assert (blank_image == loaded_image).all()

def test_csv():
  ''''''
  random.seed(101)

  tmp_path = pathlib.Path('tmp')
  tmp_path.mkdir(parents=True, exist_ok=True)

  dicts = []
  for i in range(15):
    new_dict = { 'test_int': random.randint(-10, 10), 'test_str': 'string', 'test_list': [ 1, 2, 3 ] }
    dicts.append(new_dict)
  
  csv_name = 'csv'
  passion.util.io.save_to_csv(dicts, tmp_path, csv_name)
  loaded_csv = passion.util.io.load_csv(tmp_path, csv_name + '.csv')
  
  shutil.rmtree(tmp_path)
  
  assert dicts == loaded_csv


def test_image_retrieval():

  API_KEY = "AhjPfWmuVxVrZGQfVEnguF1rPWTNWfT9lOFx1kb3COXPoAsDNpmK5N3DBUDfQ6cr"


  # just define a small example set in order to avoid problems with open street map
  passion.satellite.image_retrieval.generate_dataset(API_KEY, 'bing', TEMP_FILE_PATH, zoom = 19, 
    bbox=((50.77850739604879, 6.0768084397936395), (50.77514558009357, 6.081035433169415))
  )




@pytest.skip(msg="Rate limit of OSM API")
def test_get_osm_footprint():


  passion.segmentation.osm.generate_osm(TEMP_FILE_PATH, TEMP_FILE_PATH)



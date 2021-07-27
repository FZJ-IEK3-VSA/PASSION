

import passion


import os
import pytest
import pathlib


TEMP_FILE_PATH = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "temp"


def test_get_segmentation_prediction():
  """[summary]
  """

  passion.segmentation.prediction.segment_dataset(input_path = TEMP_FILE_PATH, model = model, output_path = TEMP_FILE_PATH)

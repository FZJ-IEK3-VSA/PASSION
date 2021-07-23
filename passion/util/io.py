import PIL
import csv
import pathlib
import numpy as np
import cv2
import ast
import pickle
import sys

# Test for allowing cells larger than the initial CSV limit.
csv.field_size_limit(min(sys.maxsize, 2147483646))

def load_image(img_path: pathlib.Path):
  '''Loads an image into a numpy array from a given path.'''
  img = PIL.Image.open(img_path)
  img_arr = np.asarray(img)

  return img_arr

def save_image(seg_image: np.ndarray, path: pathlib.Path, name: str):
  '''Saves a numpy image into a given path with a given name.'''
  cv2.imwrite(str(path / name), seg_image)
  return

def save_to_csv(sections, path, filename):
  '''Saves a list of dictionaries with the same attributes as a CSV file.'''
  keys = sections[0].keys()
  with open(str(path / (filename + '.csv')), 'w', newline='')  as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(sections)
  return

def load_csv(path, filename):
  '''Loads a CSV file into a list of dictionaries trying to cast the type of
  the columns.
  '''
  with open(str(path / filename)) as f:
    res = [{k: safe_eval(v) for k, v in row.items()}
      for row in csv.DictReader(f, skipinitialspace=True)]

    return res
def safe_eval(value):
  '''Tries to cast a string as its literal type representation, and returns
  it as a string if it fails.'''
  try:
    return ast.literal_eval(value)
  except Exception:
    return value
  
def load_pickle(path: pathlib.Path):
  '''Loads a pickle object.'''
  with open(path, 'rb') as f:
    obj = pickle.load(f)
  return obj
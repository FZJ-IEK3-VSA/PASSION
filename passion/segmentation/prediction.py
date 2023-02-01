import pathlib
import numpy as np
import cv2
import PIL
from enum import Enum
import tqdm
import shapely.geometry
import PIL
import rasterio

import torch
import torchvision

from typing import List

import passion.util

def segment_dataset(input_path: pathlib.Path,
                    model: torch.nn.Module,
                    output_path: pathlib.Path,
                    background_class: int,
                    tile_size: int = 512,
                    stride: int = 512,
                    save_masks: bool = True,
                    save_filtered: bool = True,
                    opening_closing_kernel: int = 9,
                    erosion_kernel: int = 9
):
  '''Segments a full dataset generated by generate_dataset(),
  saving the rooftop segmented masks in the specified folder.
  Segmented images are saved with the same name as the original
  images appending '_MASK' in the end.

  A stride can be specified smaller than the tile_size
  in order to make predictions in the borders.

  Tile size must match model's input size.
  '''
  output_path.mkdir(parents=True, exist_ok=True)
  
  paths = list(input_path.glob('*.tif'))
  pbar = tqdm.tqdm(paths)
  for img_path in pbar:
    src = rasterio.open(img_path)
    r = src.read(1)
    g = src.read(2)
    b = src.read(3)
    image = np.dstack((b,g,r))

    image = preprocess_input(image)

    seg_image = segment_img(image, model, tile_size, stride, background_class)

    seg_image = postprocess_output(seg_image, opening_closing_kernel, erosion_kernel, background_class)
    
    seg_image = seg_image[np.newaxis, ...]
    channels, height, width = seg_image.shape
    new_dataset = rasterio.open(str(output_path / (img_path.stem + '_MASK.tif')), 'w', driver='GTiff',
                                        height = height, width = width,
                                        count=1, dtype=str(seg_image.dtype),
                                        crs=src.crs,
                                        transform=src.transform)
    new_dataset.update_tags(**src.tags())
    new_dataset.write(seg_image)
    new_dataset.close()

  return

def segment_img(image: np.ndarray,
                model: torch.nn.Module,
                tile_size: int,
                stride: int,
                background_class: int
):
  '''Segments a single image in numpy format with a
  given model. Tile size has to be specified and must
  match model's input size.
  '''
  if type(image) != np.ndarray:
    print('Image type: {0} not a np.array'.format(type(image)))
    return None
  if len(image.shape) != 3 or image.shape[-1] != 3:
    print('Image shape: {0} not in format MxNx3'.format(image.shape))
    return None

  tiles = divide_img_tiles(image, tile_size, stride)

  seg_tiles = []
  for tile in tiles:
    prediction = segment_tile(tile, model, tile_size, background_class)
    if type(prediction) != np.ndarray:
      print('Error processing tile, returning...')
      return None
    seg_tiles.append(prediction)
  seg_tiles = np.array(seg_tiles)

  seg_image = compose_tiles(seg_tiles, image.shape[:2], stride)

  return seg_image
  

def segment_tile(tile: np.ndarray,
                 model: torch.nn.Module,
                 tile_size: int,
                 background_class: int):
  '''Segments a single tile of model's input size.
  This is a single prediction of the model.
  '''
  if type(tile) != np.ndarray:
    print('Tile type: {0} not a np.array'.format(type(tile)))
    return None
  if tile.shape != (tile_size,tile_size,3):
    print('Image shape: {0} not in format {1}x{1}x3'.format(tile.shape, tile_size))
    return None
  
  trans = torchvision.transforms.Compose([torchvision.transforms.ToTensor(), ])
  tile = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
  tile = trans(tile).reshape(1, 3, tile_size, tile_size)
  DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
  tile = tile.to(DEVICE)
  pred = model(tile)
  pred = torch.argmax(pred, dim=1)
  pred = pred.cpu().data.numpy().squeeze()
  tile = tile.cpu().data.numpy().squeeze()
  tile = np.moveaxis(tile, 0, -1)

  # If background is not 0, transform it to 0 and add 1 to the rest of classes
  rooftop_pred = pred.copy()
  if background_class != 0:
    rooftop_pred[pred==background_class] = 0
    rooftop_pred[pred!=background_class] = (rooftop_pred[pred!=background_class] + 1)

  return rooftop_pred

def divide_img_tiles(image: np.ndarray, tile_size: int, stride: int):
  '''Divides an image into a list of tiles of specified size.'''
  img_size_y, img_size_x, img_channels = image.shape

  tiles = []
  for h in range(0,img_size_y,stride):
    for w in range(0,img_size_x,stride):
      i = image[h:h+tile_size,w:w+tile_size]
      i = np.pad(i, ((0, tile_size - i.shape[0]), (0, tile_size - i.shape[1]), (0, 0)),
              mode='constant', constant_values=0)
      tiles.append(i)
  
  return np.array(tiles)

'''
class MERGE_MODE(Enum):
  \'''Custom enum to register the different merging policies.\'''
  OR, AND, VOTE = range(3)
'''

def compose_tiles(tiles: list,
                  img_shape: tuple,
                  stride: int
                  #merge_mode: MERGE_MODE=MERGE_MODE.AND
):
  '''Composes back a list of tiles into a single image.

  If a stride smaller than the tile size is specified,
  a merging policy can be specified from the following:
  
  - MERGE_MODE.AND:   For multiple predictions in a single
  pixel, its value will only be 255 if all of the predictions
  for that pixel are 255.
  - MERGE_MODE.OR:    For multiple predictions in a single
  pixel, its value will only be 255 if any of the predictions
  for that pixel are 255.
  - MERGE_MODE.VOTE:  For multiple predictions in a single
  pixel, its value will only be 255 if the majority of the
  predictions for that pixel are 255.
  '''
  if type(tiles) != np.ndarray:
    print('Error: input tiles type {0} not np.ndarray'.format(type(tiles)))
    return None
  if len(img_shape) != 2:
    print('Image shape {0} not two dimensional'.format(img_shape))
    return None
  
  num_images = len(tiles)
  tile_size_y, tile_size_x = tiles[0].shape
  img_size_y, img_size_x = img_shape

  final_pred = PIL.Image.new('L', (img_size_x, img_size_y), color=1)
  
  '''
  if merge_mode == MERGE_MODE.AND:
    sliding_window_mask = np.array(PIL.Image.new('L', (img_size_x, img_size_y), color=1))
  else:
    sliding_window_mask = np.array(PIL.Image.new('L', (img_size_x, img_size_y), color=0))
  '''
  current_x = 0
  current_y = 0

  for i, tile in enumerate(tiles):
    p = PIL.Image.fromarray(np.uint8(tile))
    '''
    if tile_size_x != stride:
      former = sliding_window_mask[current_y:current_y+tile_size_y,current_x:current_x+tile_size_x]
      new = np.asarray(p)

      new = np.pad(new, ((0, tile_size_x - new.shape[0]), (0, tile_size_y - new.shape[1])),
                  mode='constant', constant_values=0)
      
      if merge_mode == MERGE_MODE.OR:
        former = np.pad(former, ((0, tile_size_x - former.shape[0]), (0, tile_size_y - former.shape[1])),
                mode='constant', constant_values=0)
        merge = np.logical_or(former, new).astype(np.uint8)
      if merge_mode == MERGE_MODE.AND:
        former = np.pad(former, ((0, tile_size_x - former.shape[0]), (0, tile_size_y - former.shape[1])),
                mode='constant', constant_values=1)
        merge = np.logical_and(former, new).astype(np.uint8)
      if merge_mode == MERGE_MODE.VOTE:
        former = np.pad(former, ((0, tile_size_x - former.shape[0]), (0, tile_size_y - former.shape[1])),
                mode='constant', constant_values=0)
        merge = former + new

      p = PIL.Image.fromarray(merge)

      target_shape = sliding_window_mask[current_y:current_y+tile_size_y,current_x:current_x+tile_size_x].shape
      sliding_window_mask[current_y:current_y+tile_size_y,current_x:current_x+tile_size_x] = merge[0:target_shape[0], 0:target_shape[1]]
    '''
    final_pred.paste(p, box=(current_x,current_y,current_x+tile_size_x,current_y+tile_size_y))
    
    
    current_x += stride
        
    if current_x >= img_size_x:
      current_x = 0
      current_y += stride

  final_pred_arr = np.asarray(final_pred)

  #threshold = np.amax(final_pred_arr) // 2
  #final_pred_arr = (final_pred_arr > threshold).astype(np.uint8) * 255
  
  return final_pred_arr

def preprocess_input(image: np.ndarray):
  '''Preprocessing made to the numpy image before performing segmentation.
  Can be redefined with a custom function as:
  prediction.preprocess_input = custom_preprocess_function
  '''
  return image

def postprocess_output(image: np.ndarray, opening_closing_kernel: int = 9, erosion_kernel: int = 9, background_class: int = 0):
  '''Postprocessing made to the numpy image after performing segmentation.
  Can be redefined with a custom function as:
  prediction.postprocess_output = custom_postprocess_function
  '''
  out_image = np.full(image.shape, background_class)

  opening_closing_kernel = np.ones((opening_closing_kernel, opening_closing_kernel), np.uint8)
  erosion_kernel = np.ones((erosion_kernel, erosion_kernel), np.uint8)

  poly_list = []
  class_list = []
  seg_classes = np.unique(image)[np.unique(image) != background_class]
  for seg_class in seg_classes:
    #image_class = image.copy()
    image_class = (image == seg_class).astype(np.uint8)

    # opening + closing
    image_class = cv2.morphologyEx(image_class, cv2.MORPH_OPEN, opening_closing_kernel)
    image_class = cv2.morphologyEx(image_class, cv2.MORPH_CLOSE, opening_closing_kernel)
    # erosion
    image_class = cv2.erode(image_class, erosion_kernel)

    # From binary to class
    out_image[image_class == 1] = seg_class

  return out_image
import tensorflow as tf
import pathlib
import cv2
import pickle
import segmentation_models as sm
import numpy as np
import random

sm.set_framework('tf.keras')

DEFAULT_MODEL = sm.Unet('resnet34', classes=1, activation='sigmoid')
DEFAULT_OPTIMIZER = tf.keras.optimizers.Adam(learning_rate=0.0001)
DEFAULT_LOSS = tf.keras.losses.BinaryCrossentropy(from_logits=True)

def set_default_model(model: tf.keras.Model):
  '''Sets the model to be trained in train_model.'''
  DEFAULT_MODEL = model
  return

def set_default_optimizer(optimizer: tf.keras.optimizers.Optimizer):
  '''Sets the optimizer to be used in train_model.'''
  DEFAULT_OPTIMIZER = optimizer
  return

def set_default_loss(loss: tf.keras.losses.Loss):
  '''Sets the loss functino to be used in train_model.'''
  DEFAULT_LOSS = loss
  return

def train_model(training_data_path: pathlib.Path,
                model_output_path: pathlib.Path,
                batch_size: int = 1,
                n_epochs: int = 10,
                steps_per_epoch: int = 75,
                val_steps: int = 25,
                callbacks: list = [],
                filename='rooftop-segmentation'):
  '''Trains a segmentation model on the dataset found at training_data_path.
  This training data must follow the structure generated by the notebooks 00_generate_aachen_XX:

    - data_path
      |-train
        |-image
        |-label
      |-val
        |-image
        |-label
  
  Corresponding images and labels must have the same name.
  Images are 3 channel RGB satellite images and labels are their one channel binary mask.
  '''
  model = DEFAULT_MODEL
  optimizer = DEFAULT_OPTIMIZER
  loss = DEFAULT_LOSS

  train_generator = get_next_batch(batch_size=batch_size, path=training_data_path / 'train')
  val_generator = get_next_batch(batch_size=batch_size, path=training_data_path / 'val')

  model.compile(optimizer=optimizer, loss=loss, metrics=['accuracy'] + callbacks)
  
  history = model.fit(train_generator,
                    validation_data=val_generator,
                    validation_steps=val_steps,
                    epochs=n_epochs,
                    steps_per_epoch=steps_per_epoch)


  with open(model_output_path / (filename + '_history.pkl'), 'wb') as file_pi:
    pickle.dump(history.history, file_pi)
  
  if '.h5' not in filename: filename = filename + '.h5'
  
  model.save(model_output_path / filename)
  
  return

def get_next_batch(batch_size, path):
  '''Gets the next image batch of the given size from a given path.'''
  names = list((path / 'image').glob('*.png'))
  while True:
    images = []
    labels = []
    for i in range(0,batch_size):
      r = random.randint(0,len(names)-1)
      
      X_path = path / 'image' / names[r].name
      y_path = path / 'label' / names[r].name

      #print('\nProcessing image: ',X_path)
      #print('\nProcessing label: ',y_path)
      
      X = cv2.imread(str(X_path))
      y = cv2.imread(str(y_path), cv2.COLOR_BGR2GRAY)

      y = y // 255

      assert np.amin(y) >= 0 and np.amax(y) <= 1
      assert np.amin(X) >= 0 and np.amax(X) <= 255
      
      images.append(X)
      labels.append(y)
    
    assert np.array(images).shape == (batch_size, 512, 512, 3)
    assert np.array(labels).shape == (batch_size, 512, 512)

    yield np.array(images), np.array(labels)

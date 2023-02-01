import pathlib
import cv2
import pickle
import numpy as np
import random
import torch
import torchvision
import torchmetrics
import os
import time
from tqdm import tqdm
from torch.utils.tensorboard import SummaryWriter

from passion.segmentation import models

cv2.setNumThreads(4)
# determine the device to be used for training and evaluation
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# determine if we will be pinning memory during data loading
PIN_MEMORY = True if DEVICE == "cuda" else False

class SegmentationDataset(torch.utils.data.Dataset):
	def __init__(self, image_paths, label_paths, transforms):
		# store the image and mask filepaths, and augmentation transforms
		self.image_paths = image_paths
		self.label_paths = label_paths
		self.transforms = transforms

	def __len__(self):
		# return the number of total samples contained in the dataset
		return len(self.image_paths)
	def __getitem__(self, idx):
		# grab the image path from the current index
		imagePath = self.image_paths[idx]
		# load the image from disk, swap its channels from BGR to RGB,
		# and read the associated mask from disk in grayscale mode
		image = cv2.imread(str(imagePath))
		image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
		mask = cv2.imread(self.label_paths[idx], 0)
		# check to see if we are applying any transformations
		if self.transforms is not None:
			# apply the transformations to both image and its mask
			image = self.transforms(image)
			mask = self.transforms(mask)

		return (image, mask)

def train_model(train_data_path: pathlib.Path,
                val_data_path: pathlib.Path,
                model_output_path: pathlib.Path,
                model_name: str,
                num_classes: int = 18,
                batch_size: int = 1,
                learning_rate: float = 0.00001,
                n_epochs: int = 10):
  model_output_path.mkdir(parents=True, exist_ok=True)
  
  train_image_paths = sorted(list((train_data_path / 'image').glob('*.png')))
  train_image_paths = [str(path) for path in train_image_paths]
  train_label_paths = sorted(list((train_data_path / 'label').glob('*.png')))
  train_label_paths = [str(path) for path in train_label_paths]
  val_image_paths = sorted(list((val_data_path / 'image').glob('*.png')))
  val_image_paths = [str(path) for path in val_image_paths]
  val_label_paths = sorted(list((val_data_path / 'label').glob('*.png')))
  val_label_paths = [str(path) for path in val_label_paths]
  
  trans = torchvision.transforms.Compose([torchvision.transforms.ToTensor(), ])
  train_dataset = SegmentationDataset(image_paths=train_image_paths,
                                      label_paths=train_label_paths,
                                      transforms=trans)
  val_dataset = SegmentationDataset(image_paths=val_image_paths,
                                     label_paths=val_label_paths,
                                     transforms=trans)
  print(f"[INFO] found {len(train_dataset)}, examples in the training set...")
  print(f"[INFO] {len(train_image_paths)},{len(train_label_paths)}")
  print(f"[INFO] found {len(val_dataset)}, examples in the validation set...")
  print(f"[INFO] {len(val_image_paths)},{len(val_label_paths)}")


  train_loader = torch.utils.data.DataLoader(train_dataset, shuffle=True,
    batch_size=batch_size, pin_memory=PIN_MEMORY,
    num_workers=os.cpu_count())
  val_loader = torch.utils.data.DataLoader(val_dataset, shuffle=False,
    batch_size=batch_size, pin_memory=PIN_MEMORY,
    num_workers=os.cpu_count())
 
  focal_loss = torch.hub.load(
    'passion/segmentation/pytorch-multi-class-focal-loss',
    model='focal_loss',
    source='local',
    alpha=None,
    gamma=2,
    reduction='mean',
    device=DEVICE,
    dtype=torch.float32,
    force_reload=False
  )
  loss_func = focal_loss

  print(f'Initializing ResNetUNet with {num_classes} classes...')
  unet = models.ResNetUNet(num_classes).to(DEVICE)
  unet.to(DEVICE)
  optimizer = torch.optim.Adam(unet.parameters(), lr=learning_rate)

  train_steps = len(train_dataset) // batch_size
  val_steps = len(val_dataset) // batch_size
  # initialize a dictionary to store training history
  H = {"train_loss": [], "val_loss": [], "train_acc":[], "val_acc":[]}

  best_val_score = 0.0

  # Tensorboard writer
  tensorboard_path = pathlib.Path(model_output_path / (model_name.split('.')[0]))
  model_output_path.mkdir(parents=True, exist_ok=True)
  writer = SummaryWriter(log_dir=str(tensorboard_path))

  # loop over epochs
  print("[INFO] training the network...")
  start_time = time.time()
  for e in tqdm(range(n_epochs)):
    confmat = torchmetrics.ConfusionMatrix(task='multiclass',num_classes=num_classes).to(DEVICE)
    cm = torch.zeros((num_classes,num_classes)).to(DEVICE)
    # set the model in training mode
    unet.train()
    # initialize the total training and validation loss
    total_train_loss = 0
    total_val_loss = 0
    total_correct = 0
    total = 0
    jaccard = torchmetrics.JaccardIndex(task='multiclass', num_classes=num_classes).to(DEVICE)
    total_val, total_val_correct = 0, 0
    # loop over the training set
    for (i, (x, y)) in enumerate(train_loader):
      y *= 255
      # send the input to the device
      (x, y) = (x.to(DEVICE), y.to(DEVICE))
      # perform a forward pass and calculate the training loss
      pred = unet(x)
      if DEVICE == "cuda":
        y = y.type(torch.cuda.LongTensor).squeeze()
      else:
        y = y.type(torch.LongTensor).squeeze()
        
      loss = loss_func(pred, (y))
      # first, zero out any previously accumulated gradients, then
      # perform backpropagation, and then update model parameters
      optimizer.zero_grad()
      loss.backward()
      optimizer.step()
      # add the loss to the total training loss so far
      total_train_loss += loss


      pred = torch.argmax(pred, dim=1)
      total += y.size().numel()
      total_correct += (pred == y).sum().item()
      if DEVICE == "cuda":
        pred = pred.type(torch.cuda.LongTensor).squeeze()
      else:
        pred = pred.type(torch.LongTensor).squeeze()
      cm += confmat(pred, y)

    train_iou = intersection_over_union(cm.cpu().detach().numpy())
    mean_train_iou = np.mean(train_iou)
    print('Train Class IOU', train_iou)
    print('Train Mean Class IOU:{}'.format(mean_train_iou))

    # switch off autograd
    with torch.no_grad():
      confmat = torchmetrics.ConfusionMatrix(task='multiclass',num_classes=num_classes).to(DEVICE)
      cm = torch.zeros((num_classes,num_classes)).to(DEVICE)
      # set the model in evaluation mode
      unet.eval()
      # loop over the validation set
      for (x, y) in val_loader:
        # send the input to the device
        y *= 255
        (x, y) = (x.to(DEVICE), y.to(DEVICE))
        # make the predictions and calculate the validation loss
        pred = unet(x)
        if DEVICE == "cuda":
          y = y.type(torch.cuda.LongTensor).squeeze()
        else:
          y = y.type(torch.LongTensor).squeeze()
        #y = replaceTensor(y)
        loss = loss_func(pred, torch.squeeze(y))
        total_val_loss += loss

        pred = torch.argmax(pred, dim=1)
        total_val += y.size().numel()
        total_val_correct += (pred == y).sum().item()

        if DEVICE == "cuda":
          pred = pred.type(torch.cuda.LongTensor).squeeze()
        else:
          pred = pred.type(torch.LongTensor).squeeze()

        j_s = jaccard((pred), (y))
        cm += confmat(pred, y)
      val_iou = intersection_over_union(cm.cpu().detach().numpy())
      mean_val_iou = np.mean(val_iou)
      print('Val Class IOU', val_iou)
      print('Val Mean Class IOU:{}'.format(np.mean(val_iou)))

      if(mean_val_iou > best_val_score):
        print('Better Model Found: {} > {}'.format(mean_val_iou, best_val_score))
        best_val_score = mean_val_iou
        torch.save(unet, model_output_path / model_name)
  
    # calculate the average training and validation loss
    avg_train_loss = total_train_loss / train_steps
    avg_val_loss = total_val_loss / val_steps
    avg_train_acc = total_correct / total
    avg_val_acc = total_val_correct / total_val

    writer.add_scalars(f'iou', {
        'mean_train_iou': mean_train_iou,
        'mean_val_iou': mean_val_iou,
    }, e)
    writer.add_scalars(f'loss', {
        'train_loss': avg_train_loss.cpu().detach().numpy(),
        'val_loss': avg_val_loss.cpu().detach().numpy(),
    }, e)
    writer.add_scalars(f'acc', {
        'train_acc': avg_train_acc,
        'val_acc': avg_val_acc,
    }, e)

    # update our training history
    H["train_loss"].append(avg_train_loss.cpu().detach().numpy())
    H["val_loss"].append(avg_val_loss.cpu().detach().numpy())
    H["train_acc"].append(avg_train_acc)
    H["val_acc"].append(avg_val_acc)
    # print the model training and validation information
    print("[INFO] EPOCH: {}/{}".format(e + 1, n_epochs))
    print("Train loss: {:.6f}, Val loss: {:.4f} Train Acc: {:.6f}, Val Acc: {:.4f}".format(
      avg_train_loss, avg_val_loss, avg_train_acc, avg_val_acc))
  # display the total time needed to perform the training
  end_time = time.time()
  print("[INFO] total time taken to train the model: {:.2f}s".format(
    end_time - start_time))
  
  # serialize the model to disk
  torch.save(unet, model_output_path / 'model_last.pth')
  writer.flush()
  print('Best Val Score:{}'.format(best_val_score))


def intersection_over_union(confusion_matrix):
	# Intersection = TP Union = TP + FP + FN
	# IoU = TP / (TP + FP + FN)
	intersection = np.diag(confusion_matrix)
	union = np.sum(confusion_matrix, axis=1) + np.sum(confusion_matrix, axis=0) - np.diag(confusion_matrix)
	iou = intersection / union
	return iou
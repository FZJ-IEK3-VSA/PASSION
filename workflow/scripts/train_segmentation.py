import passion
import argparse, pathlib, yaml, pathlib, shapefile

parser = argparse.ArgumentParser()
parser.add_argument('--config', metavar='C', type=str, help='Config file path')
args = vars(parser.parse_args())
configfile = args['config']

with open(configfile, "r") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit

training_config = config.get('SegmentationTraining')
results_path = pathlib.Path(config.get('results_path'))

training_data_path = pathlib.Path(training_config['dataset_folder'])
model_output_path = pathlib.Path(training_config['output_folder']) / training_config['folder_name']
model_output_path = results_path / model_output_path

batch_size = training_config['batch_size']
n_epochs = training_config['n_epochs']
steps_per_epoch = training_config['steps_per_epoch']
val_steps = training_config['val_steps']

passion.segmentation.training.train_model(training_data_path,
                                          model_output_path,
                                          batch_size=1,
                                          n_epochs=n_epochs,
                                          steps_per_epoch=steps_per_epoch,
                                          val_steps=val_steps)
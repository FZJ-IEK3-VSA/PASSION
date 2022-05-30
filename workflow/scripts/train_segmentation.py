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

training_data_path = training_config['dataset_folder']
model_output_path = training_config['output_folder']

batch_size = training_config['batch_size']
n_epochs = training_config['n_epochs']
steps_per_epoch = training_config['steps_per_epoch']
val_steps = training_config['val_steps']

passion.segmentation.training.train_model(training_data_path, model_output_path,
                                            batch_size=1,
                                            n_epochs=n_epochs,
                                            steps_per_epoch=steps_per_epoch,
                                            val_steps=val_steps)
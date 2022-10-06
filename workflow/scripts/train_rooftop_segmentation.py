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

training_config = config.get('RooftopSegmentationTraining')
results_path = pathlib.Path(config.get('results_path'))

train_path = pathlib.Path(training_config['train_folder'])
val_path = pathlib.Path(training_config['val_folder'])
model_output_path = pathlib.Path(training_config['output_folder']) / training_config['folder_name']
model_output_path = results_path / model_output_path

batch_size = int(training_config['batch_size'])
n_epochs = int(training_config['n_epochs'])
learning_rate = float(training_config['learning_rate'])
num_classes = int(training_config['num_classes'])

passion.segmentation.training.train_model(train_path,
                                          val_path,
                                          model_output_path,
                                          num_classes=num_classes,
                                          batch_size=batch_size,
                                          learning_rate=learning_rate,
                                          n_epochs=n_epochs)
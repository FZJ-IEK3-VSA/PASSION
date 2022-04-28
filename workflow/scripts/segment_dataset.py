import passion
import argparse, pathlib, yaml, pathlib, shapefile
import tensorflow as tf

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

segmentation_config = config.get('ImageSegmentation')
image_retrieval_config = config.get('ImageRetrieval')
results_path = pathlib.Path(config.get('results_path'))


input_folder = image_retrieval_config['output_folder']
input_path = results_path / input_folder

output_folder = segmentation_config['output_folder']
output_path = results_path / output_folder

model_rel_path = segmentation_config['model_rel_path']
model_path = results_path / model_rel_path

model = tf.keras.models.load_model(str(model_path))

passion.segmentation.prediction.segment_dataset(input_path = input_path, model = model, output_path = output_path)

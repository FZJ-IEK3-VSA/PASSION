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

is_osm = segmentation_config.get('osm')

polygon_simplification_distance = segmentation_config.get('polygon_simplification_distance')
polygon_simplification_distance = float(polygon_simplification_distance)

kernel_size = segmentation_config.get('kernel_size')
kernel_size = int(kernel_size)

osm_request_interval = segmentation_config.get('osm_request_interval')
osm_request_interval = int(osm_request_interval)

if is_osm:
    passion.segmentation.osm.generate_osm(input_path = input_path,
                    output_path = output_path,
                    save_masks = True,
                    save_filtered = True,
                    osm_request_interval = osm_request_interval)
else:
    model_rel_path = segmentation_config['model_rel_path']
    model_path = results_path / model_rel_path

    model = tf.keras.models.load_model(str(model_path))

    passion.segmentation.prediction.segment_dataset(
        input_path = input_path,
        model = model,
        output_path = output_path,
        polygon_simplification_distance = polygon_simplification_distance,
        kernel_size = kernel_size
        )

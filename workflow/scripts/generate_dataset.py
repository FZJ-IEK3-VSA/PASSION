import passion
import argparse, pathlib, yaml, pathlib, shapefile

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--config', metavar='C', type=str, help='Config file path')
args = vars(parser.parse_args())
configfile = args['config']

with open(configfile, "r") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit

image_retrieval_config = config.get('ImageRetrieval')
results_path = pathlib.Path(config.get('results_path'))

api_key = image_retrieval_config.get('api_key')
service = image_retrieval_config.get('service')
zoom = int(image_retrieval_config.get('zoom'))
bbox = image_retrieval_config.get('bbox')
if bbox:
    min_lat = float(bbox.get('min_lat'))
    min_lon = float(bbox.get('min_lon'))
    max_lat = float(bbox.get('max_lat'))
    max_lon = float(bbox.get('max_lon'))
    bbox = ((min_lat, min_lon), (max_lat, max_lon))
    bbox = ((min_lat, min_lon), (max_lat, max_lon))
shape = image_retrieval_config.get('shapefile')
if shape:
    sf = shapefile.Reader(shape)
    shape = sf.shapes()[0]

output_folder = image_retrieval_config['output_folder']
output_path = results_path / output_folder

passion.satellite.image_retrieval.generate_dataset(api_key, service, output_path,
                                    zoom = zoom, bbox=bbox, shapefile=shape)

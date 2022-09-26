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

rooftop_config = config.get('RooftopAnalysis')
segmentation_config = config.get('ImageSegmentation')
results_path = pathlib.Path(config.get('results_path'))

input_folder = segmentation_config['output_folder']
input_path = results_path / input_folder

output_folder = rooftop_config['output_folder']
output_path = results_path / output_folder

output_name = rooftop_config['file_name']

tilt_distribution_rel_path = rooftop_config['tilt_rel_path']
tilt_distribution_path = results_path / tilt_distribution_rel_path

minimum_area = int(rooftop_config.get('minimum_area'))

passion.buildings.rooftop_analysis.generate_rooftops(input_path,
                                                     output_path,
                                                     output_name,
                                                     tilt_distribution_path,
                                                     minimum_area)
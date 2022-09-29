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
technical_config = config.get('TechnicalAnalysis')
results_path = pathlib.Path(config.get('results_path'))

input_folder = rooftop_config['output_folder']
input_path = results_path / input_folder
input_name = rooftop_config['file_name']

output_folder = technical_config['output_folder']
output_path = results_path / output_folder

output_name = technical_config['file_name']

era5_path = technical_config.get('era5_path')
sarah_path = technical_config.get('sarah_path')

passion.technical.reskit.generate_technical(input_path, input_name, output_path, output_name, era5_path, sarah_path)
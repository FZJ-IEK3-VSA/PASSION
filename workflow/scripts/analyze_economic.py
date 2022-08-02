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

technical_config = config.get('TechnicalAnalysis')
economic_config = config.get('EconomicAnalysis')
results_path = pathlib.Path(config.get('results_path'))

input_folder = technical_config['output_folder']
input_path = results_path / input_folder
input_name = technical_config['file_name']

output_folder = economic_config['output_folder']
output_path = results_path / output_folder

output_name = economic_config['file_name']

passion.economic.lcoe.generate_economic(input_path, input_name, output_path, output_name)
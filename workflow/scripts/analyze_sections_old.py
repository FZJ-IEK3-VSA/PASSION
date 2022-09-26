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

section_config = config.get('SectionAnalysis')
rooftop_config = config.get('RooftopAnalysis')
results_path = pathlib.Path(config.get('results_path'))

input_folder = rooftop_config['output_folder']
input_path = results_path / input_folder
input_name = rooftop_config['file_name']

output_folder = section_config['output_folder']
output_path = results_path / output_folder

output_name = section_config['file_name']

tilt_distribution_rel_path = section_config['tilt_rel_path']


tilt_distribution_path = results_path / tilt_distribution_rel_path

passion.buildings.section_analysis.generate_sections(input_path, input_name, output_path, output_name, tilt_distribution_path)

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
rooftop_segmentation_config = config.get('RooftopSegmentation')
section_segmentation_config = config.get('SectionSegmentation')
superstructure_segmentation_config = config.get('SuperstructureSegmentation')
results_path = pathlib.Path(config.get('results_path'))
zoom = config.get('ImageRetrieval').get('zoom')
project_results_path = results_path / (f"{config.get('project_name')}-z{zoom}")

rooftop_input_folder = rooftop_segmentation_config['output_folder']
rooftop_input_path = project_results_path / rooftop_input_folder
section_input_folder = section_segmentation_config['output_folder']
section_input_path = project_results_path / section_input_folder
superstructure_input_folder = superstructure_segmentation_config['output_folder']
superstructure_input_path = project_results_path / superstructure_input_folder

output_folder = rooftop_config['output_folder']
output_path = project_results_path / output_folder

output_name = rooftop_config['file_name']

tilt_distribution_rel_path = rooftop_config['tilt_rel_path']
tilt_distribution_path = results_path / tilt_distribution_rel_path

simplification_distance = rooftop_config.get('simplification_distance')
simplification_distance = float(simplification_distance)

merge_style = rooftop_config.get('merge_style')

passion.buildings.building_analysis.analyze_rooftops(rooftop_input_path,
                                                     section_input_path,
                                                     superstructure_input_path,
                                                     output_path,
                                                     output_name,
                                                     tilt_distribution_path,
                                                     simplification_distance,
                                                     merge_style)
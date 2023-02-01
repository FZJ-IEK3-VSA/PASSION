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
zoom = config.get('ImageRetrieval').get('zoom')
project_results_path = results_path / (f"{config.get('project_name')}-z{zoom}")


input_folder = rooftop_config['output_folder']
input_path = project_results_path / input_folder
input_name = rooftop_config['file_name']

output_folder = technical_config['output_folder']
output_path = project_results_path / output_folder

output_name = technical_config['file_name']

era5_path = technical_config.get('era5_path')
sarah_path = technical_config.get('sarah_path')

minimum_section_area = float(technical_config.get('minimum_section_area'))

pv_model_id = technical_config.get('pv_model_id')
pv_model_name = technical_config.get('pv_model_name')
pv_model_capacity = float(technical_config.get('pv_model_capacity'))
pv_model_width = float(technical_config.get('pv_model_width'))
pv_model_height = float(technical_config.get('pv_model_height'))
pv_model_price = float(technical_config.get('pv_model_price'))
pv_spacing_factor = float(technical_config.get('pv_spacing_factor'))
pv_border_spacing = float(technical_config.get('pv_border_spacing'))
pv_n_offset = int(technical_config.get('pv_n_offset'))

pv_panel_properties = {
    'id': pv_model_id,
    'name': pv_model_name,
    'capacity': pv_model_capacity,
    'width': pv_model_width,
    'height': pv_model_height,
    'price': pv_model_price,
    'spacing_factor': pv_spacing_factor,
    'border_spacing': pv_border_spacing,
    'n_offset': pv_n_offset
}

passion.technical.reskit.generate_technical(input_path,
                                            input_name,
                                            output_path,
                                            output_name,
                                            era5_path,
                                            sarah_path,
                                            minimum_section_area,
                                            pv_panel_properties)
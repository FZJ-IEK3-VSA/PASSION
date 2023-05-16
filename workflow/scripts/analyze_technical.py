import passion
import argparse, pathlib, yaml, pathlib, shapefile
import pkg_resources
import shutil

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

merra_path = technical_config.get('merra_path')
merra_path = results_path / merra_path
if list(merra_path.glob('.nc')) == []:
    reskit_merra_path = pkg_resources.resource_filename('reskit', '_test/data/merra-like')
    print(f'Merra path specified in config.yml does not exist. Copying default merra-like data from RESKit ({reskit_merra_path}).')
    reskit_merra_path = pathlib.Path(reskit_merra_path)
    merra_path.mkdir(parents=True, exist_ok=True)
    for f in reskit_merra_path.glob('*.nc4'):
        shutil.copy(f, merra_path)
    
solar_atlas_path = technical_config.get('solar_atlas_path')
solar_atlas_path = results_path / solar_atlas_path
if not solar_atlas_path.exists():
    reskit_solar_atlas_path = pkg_resources.resource_filename('reskit', '_test/data/gsa-ghi-like.tif')
    print(f'Solar atlas path specified in config.yml does not exist. Copying default solar atlas data from RESKit ({reskit_solar_atlas_path}).')
    shutil.copy(reskit_solar_atlas_path, solar_atlas_path)

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
                                            merra_path,
                                            solar_atlas_path,
                                            minimum_section_area,
                                            pv_panel_properties)
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

technical_config = config.get('TechnicalAnalysis')
economic_config = config.get('EconomicAnalysis')
results_path = pathlib.Path(config.get('results_path'))
zoom = config.get('ImageRetrieval').get('zoom')
project_results_path = results_path / (f"{config.get('project_name')}-z{zoom}")

input_folder = technical_config['output_folder']
input_path = project_results_path / input_folder
input_name = technical_config['file_name']

output_folder = economic_config['output_folder']
output_path = project_results_path / output_folder

output_name = economic_config['file_name']

panel_lifespan = float(economic_config['panel_lifespan'])
inverter_lifespan = float(economic_config['inverter_lifespan'])
inverter_price_rate = float(economic_config['inverter_price_rate'])
other_costs = float(economic_config['other_costs'])
discount_rate = float(economic_config['discount_rate'])
yearly_degradation = float(economic_config['yearly_degradation'])


passion.economic.lcoe.generate_economic(input_path,
                                        input_name,
                                        output_path,
                                        output_name,
                                        panel_lifespan,
                                        inverter_lifespan,
                                        inverter_price_rate,
                                        other_costs,
                                        discount_rate,
                                        yearly_degradation)
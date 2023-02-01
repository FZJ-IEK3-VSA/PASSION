import passion
import argparse, pathlib, yaml, pathlib, shapefile
import torch

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

segmentation_config = config.get('SuperstructureSegmentation')
image_retrieval_config = config.get('ImageRetrieval')
results_path = pathlib.Path(config.get('results_path'))
zoom = image_retrieval_config.get('zoom')
project_results_path = results_path / (f"{config.get('project_name')}-z{zoom}")

input_folder = image_retrieval_config['output_folder']
input_path = project_results_path / input_folder

output_folder = segmentation_config['output_folder']
output_path = project_results_path / output_folder

background_class = segmentation_config.get('background_class')

opening_closing_kernel = segmentation_config.get('opening_closing_kernel')
opening_closing_kernel = int(opening_closing_kernel)
erosion_kernel = segmentation_config.get('erosion_kernel')
erosion_kernel = int(erosion_kernel)

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Using torch device: {device}')
if device=='cuda': print(f'Name: {torch.cuda.get_device_name(0)}')
model_rel_path = segmentation_config['model_rel_path']
model_path = results_path / model_rel_path
model = torch.load(str(model_path), map_location=torch.device(device))

passion.segmentation.prediction.segment_dataset(
    input_path = input_path,
    model = model,
    output_path = output_path,
    background_class = background_class,
    opening_closing_kernel = opening_closing_kernel,
    erosion_kernel = erosion_kernel
    )

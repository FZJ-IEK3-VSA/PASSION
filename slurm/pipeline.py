from .. import passion

import pathlib
import tensorflow as tf

# SATELLITE, OUT OF HERE BECAUSE WITH SBATCH I GET URLCONNECTION ERROR
satellite_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/satellite')
#passion.satellite.image_retrieval.generate_dataset('API_KEY', 'bing', satellite_output_path, zoom = 19, bbox=((50.77850739604879, 6.0768084397936395), (50.77214558009357, 6.091035433169415)))

# MODEL TRAINING
training_data_path = pathlib.Path('/storage/internal/data/r-pueblas/aachen_model')
model_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/model')

#passion.segmentation.training.train_model(training_data_path, model_output_path, batch_size=1)

# OSM FOOTPRINTS, OUT OF HERE BECAUSE WITH SBATCH I GET CONNECTION ERROR
#osm_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/osm')

#passion.segmentation.osm.generate_osm(satellite_output_path, osm_output_path)

# MODEL SEGMENTATION
model_path = model_output_path / 'rooftop_segmentation.h5'

model = tf.keras.models.load_model(str(model_path))
segmentation_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/segmentation')

passion.segmentation.prediction.segment_dataset(input_path = satellite_output_path, model = model, output_path = segmentation_output_path)

# ROOFTOPS ANALYSIS

rooftop_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/rooftops')

passion.buildings.rooftop_analysis.generate_rooftops(segmentation_output_path, rooftop_output_path)

# SECTIONS ANALYSIS

section_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/sections')
tilt_distribution_path = pathlib.Path('/storage/internal/home/r-pueblas/final/passion/buildings/data/tilt_distribution.pkl')

passion.buildings.section_analysis.generate_sections(rooftop_output_path, section_output_path, tilt_distribution_path)

# TECHNICAL

technical_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/technical')
era5_path = r'/storage/internal/data/gears/weather/ERA5/processed/4/8/5/2014'
sarah_path = r'/storage/internal/data/gears/weather/SARAH/processed/4/8/5/2014'

passion.technical.reskit.generate_technical(section_output_path, technical_output_path, era5_path, sarah_path)

# ECONOMIC

economic_output_path = pathlib.Path('/storage/internal/home/r-pueblas/final/results/economic')

passion.economic.lcoe.generate_economic(technical_output_path, economic_output_path)
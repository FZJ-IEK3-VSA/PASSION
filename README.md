# PASSION - PhotovoltAic Satellite SegmentatION

The PASSION python package provides a framework for estimating the rooftop photovoltaic potential of a region
by analysing its satellite imagery. The library allows all the necessary steps, like obtaining the
imagery from one of the services (Bing Maps or Google Maps) or training the segmentation model.
Final result can be obtained in terms of Levelised Cost of Electricity (LCOE).

## Getting Started


### Prerequisites

To set the project up, you need to run in the root folder:

#### Linux:
```
conda create --name passion-test --channel conda-forge python=3.7 "netCDF4>=1.5.3" "gdal>=2.0.0,<3.0.0" xarray matplotlib descartes pandas numpy scipy scikit-learn pathlib pillow tqdm shapely pyshp mahotas pytest

source activate passion-test
pip3 install -r requirements.txt

git clone https://github.com/FZJ-IEK3-VSA/geokit.git
cd geokit
pip3 install .
cd ..
rm -rf geokit
pip3 install git+https://github.com/FZJ-IEK3-VSA/reskit.git#egg=reskit
pip3 install -U segmentation-models
```

#### Windows:
```
conda create --name passion-test --channel conda-forge python=3.7 "netCDF4>=1.5.3" "gdal>=2.0.0,<3.0.0" xarray matplotlib descartes pandas numpy scipy scikit-learn pathlib pillow tqdm shapely pyshp mahotas pytest

activate passion-test
pip3 install -r requirements.txt

git clone https://github.com/FZJ-IEK3-VSA/geokit.git
cd geokit
pip3 install .
cd ..
del /s /q geokit
pip3 install git+https://github.com/FZJ-IEK3-VSA/reskit.git#egg=reskit
pip3 install -U segmentation-models
```

## Running the tests

To execute automated tests, in the root folder run:

```
pytest
```

### Examples

A set of examples can be found in the notebooks folder.

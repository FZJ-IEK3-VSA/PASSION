# PASSION - PhotovoltAic Satellite SegmentatION

The PASSION python package provides a framework for estimating the rooftop photovoltaic potential of a region
by analysing its satellite imagery. The library allows all the necessary steps, like obtaining the
imagery from one of the services (Bing Maps or Google Maps) or training the segmentation model.
Final result can be obtained in terms of Levelised Cost of Electricity (LCOE).

## Getting Started


### Prerequisites

To set the project up, you need to run in the root folder:

```
conda env create -f environment.yml
conda activate passion
python setup.py install
```


For getting the satelite images, please retrieve an API_KEY for bing maps from https://www.bingmapsportal.com/ and set it.


The trained model is quite big, therefore it is stored outside of the repository and can be downloaded here: 

## Running the tests

To execute automated tests, in the root folder run:

```
pytest
```

### Examples

A set of examples can be found in the notebooks folder.

# PASSION - PhotovoltAic Satellite SegmentatION

![Click here to see the package layers](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/layers.png)


The PASSION python package provides a framework for estimating the rooftop photovoltaic potential of a region
by analysing its satellite imagery. The library allows all the necessary steps, like obtaining the
imagery from one of the services (Bing Maps or Google Maps) or training the segmentation model.
Final result can be obtained in terms of Levelised Cost of Electricity (LCOE).



![Click here to see the visual pipeline.](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/full_process.gif)

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

A set of examples for every step can be found in the notebooks folder.  Also, notebooks for generating the training data for the model, and an example of the manager that runs all the pipeline in a single function call.

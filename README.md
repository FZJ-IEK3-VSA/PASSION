# PASSION - PhotovoltAic Satellite SegmentatION

![Click here to see the package layers](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/layers.png)


The PASSION python package provides a framework for estimating the rooftop photovoltaic potential of a region
by analysing its satellite imagery. The library allows all the necessary steps, like obtaining the
imagery from one of the services (Bing Maps or Google Maps) or training the segmentation model.
Final result can be obtained in terms of Levelised Cost of Electricity (LCOE).



![Click here to see the visual pipeline.](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/full_process.gif)

## Getting Started


### Prerequisites

Given the model size, this repository requires git LFS. You can install it in your system with the following guide:
http://arfc.github.io/manual/guides/git-lfs

To set the project up, you need to run in the root folder:

```
conda env create -f requirements.yml
conda activate passion
```


For getting the satelite images, please retrieve an API_KEY for bing maps from https://www.bingmapsportal.com/ and set it in the snakemake config file.

The key should be specified at workflow/config.yml as:
```
api_key: '<API_KEY>'
```

To run the pipeline with the sample configuration, you can choose to run:

```
snakemake --cores 1
```

Or, if you want to access the GUI and select which steps to run:

```
snakemake --gui
```

In order to run passion in a SLURM environment, run:
```
snakemake --profile workflow/slurm
```

## Running the tests

To execute automated tests, in the root folder run:

```
pytest
```

### Examples

A set of examples for every step can be found in the notebooks folder.  Also, notebooks for generating the training data for the model, and a notebook that uses the final economic CSV file.
<a href="https://www.fz-juelich.de/en/iek/iek-3"><img src="https://www.fz-juelich.de/static/media/Logo.2ceb35fc.svg" alt="FZJ Logo" width="200px"></a>

# PASSION - PhotovoltAic Satellite SegmentatION

![Click here to see the package layers](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/layers.png)

The PASSION python package provides a framework for estimating the rooftop photovoltaic potential of a region by analysing its satellite imagery. The library allows all the necessary steps, like obtaining the
imagery from one of the services (Bing Maps or Google Maps) or training the segmentation model.
Final result can be obtained in terms of Levelised Cost of Electricity (LCOE).

## Features
* Retrieve satellite imagery from a shapefile or bounding box from one of the following providers:
  * Bing Maps: [get your API key](https://www.bingmapsportal.com/)
  * Google Maps: [get your API key](https://developers.google.com/maps)
* Detect and segment building rooftops from the given satellite images.
* Simulate and estimate the photovoltaic potential of the rooftops by using [RESKit](https://github.com/FZJ-IEK3-VSA/RESKit).
* Transform the potential into economic terms using the Levelized Cost of Electricity (LCOE).

![Click here to see the visual pipeline.](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/full_process.gif)

## Getting Started

---

### Prerequisites

Given the model size, this repository requires git LFS. You can install it in your system with the following guide:
http://arfc.github.io/manual/guides/git-lfs. Please make sure that the model under `workflow/output/model/rooftop_segmentation.h5` is properly downloaded before moving on.

To set the project up and running any of the steps, you need to run in the root folder:

```
conda env create -f requirements.yml
conda activate passion
```

Please take into account that the **environment needs to be activated** in order to run the project.

For getting the satelite images, please retrieve an API_KEY from one of the providers (bing maps is recommended, from https://www.bingmapsportal.com/) and set it in the snakemake config file:

`
workflow/config.yml
`

The key should be specified as:

`
api_key: '<API_KEY>'
`

---

### Required data

Each of the different steps will require different data files. You can run any of the steps without requiring the data files that the other steps need.

1. Satellite retrieval:
   * No additional data files are required. Only a valid API key for one of the satellite providers.
2. Rooftop segmentation.
   * The file `workflow/output/model/rooftop_segmentation.h5` is needed, and should have been directly downloaded when cloning the repository. Git-LFS is needed for the model to be properly downloaded.
3. Section segmentation.
   * The file `workflow/output/tilt_distribution.pkl` is needed, and should have been directly downloaded when cloning the repository.
4. Technical potential simulation:
   * ERA5 dataset: WIP, external dependency
   * SARAH dataset: WIP, external dependency
5. Economic potential:
   * No additional data files are required.

---

### Software usage

To run the whole pipeline with the given configuration, you can choose to run:

* Regular run:

```
snakemake --cores 1
```

* Snakemake GUI (also allows to select which steps to run, and executing a dry-run):

```
snakemake --gui
```

* In order to run passion in a SLURM environment, run:

```
snakemake --profile workflow/slurm
```

To train the model, run the following argument after any of the above:
```
snakemake [...] --until segmentation_training
```

---

## Visualizing results (very early stages)

If you want to visualize the results of your pipeline, a local GUI can be instantiated as:

`
python gui/sample_server.py
`

When the server is running, you can access the GUI entering the following local address in your browser:

`
http://127.0.0.1:5000/
`


---

## Running the tests

To execute automated tests, in the root folder run:

```
pytest
```

### Examples

A set of lower level jupyter notebooks for every step can be found in the examples folder. Also, notebooks for generating the training data for the model, and a notebook that uses the final economic CSV file.

## License

MIT License

Copyright (c) 2021-2022 Rodrigo Pueblas (FZJ/IEK-3), Shruthi Patil (FZJ/IEK-3), Patrick Kuckertz (FZJ/IEK-3), Jann Weinand (FZJ/IEK-3), Leander Kotzur (FZJ/IEK-3), Detlef Stolten (FZJ/IEK-3)

You should have received a copy of the MIT License along with this program.
If not, see https://opensource.org/licenses/MIT

## About Us

We are the [Institute of Energy and Climate Research - Techno-economic Systems Analysis (IEK-3)](https://www.fz-juelich.de/en/iek/iek-3) belonging to the [Forschungszentrum Jülich](https://www.fz-juelich.de/en). Our interdisciplinary department's research is focusing on energy-related process and systems analyses. Data searches and system simulations are used to determine energy and mass balances, as well as to evaluate performance, emissions and costs of energy systems. The results are used for performing comparative assessment studies between the various systems. Our current priorities include the development of energy strategies, in accordance with the German Federal Government’s greenhouse gas reduction targets, by designing new infrastructures for sustainable and secure energy supply chains and by conducting cost analysis studies for integrating new technologies into future energy market frameworks.

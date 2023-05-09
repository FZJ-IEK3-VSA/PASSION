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

In order to skip the training of the models, they can be directly downloaded via [this link](https://doi.org/10.5281/zenodo.7886980). Please move the files to the folders `workflow/output/model/rooftop-segmentation`, `workflow/output/model/section-segmentation` and `workflow/output/model/superst-segmentation` before moving on.

To set the project up and running any of the steps, you need to run in the root folder:

```
conda env create -f requirements.yml
conda activate passion
```

Please take into account that the **environment needs to be activated** in order to run the project.

For getting the satelite images, please retrieve an API_KEY from one of the providers (bing maps is recommended, from https://www.bingmapsportal.com/) and set it in the snakemake config file (`workflow/config.yml`) as follows:
```
api_key: '<API_KEY>'
```

---

### Required data

Each of the different steps will require different data files. You can run any of the steps without requiring the data files that the other steps need.

1. Satellite retrieval:
   * No additional data files are required. Only a valid API key for one of the satellite providers.
2. Rooftop segmentation.
   * The models downloaded from [Sciebo](https://fz-juelich.sciebo.de/s/XsKThEaYnTotkbm) are needed, and should be located in the structure defined in the `config.yml` file. The default required structure is:
     * `workflow/output/model/rooftop-segmentation/rooftops.pth`
     * `workflow/output/model/section-segmentation/sections.pth`
     * `workflow/output/model/superst-segmentation/superstructures.pth`
3. Building analysis.
   * The file `workflow/output/tilt_distribution.pkl` is needed, and should have been directly downloaded when cloning the repository.
4. Technical potential simulation:
   * A folder for ERA5 data processed in RESKit format is needed. A sample folder can be found in `https://github.com/FZJ-IEK3-VSA/RESKit/tree/master/reskit/_test/data/era5-like`.
   * A folder for SARAH data processed in RESKit format is needed. A sample folder can be found in `https://github.com/FZJ-IEK3-VSA/RESKit/tree/master/reskit/_test/data/sarah-like`.
5. Economic potential:
   * No additional data files are required.


In order to use the sample weather datasets for technical and economic calculations, please follow these steps:
1. Clone RESKit repository:
   ```
   $ git clone https://github.com/FZJ-IEK3-VSA/RESKit.git
   ```
2. Change the following properties in `workflow/config.yml` (please, substitute <RESKit_REPO> with the location of your previously cloned repository):
   ```
   era5_path: '<RESKit_REPO>/reskit/_test/data/era5-like' 
   sarah_path: '<RESKit_REPO>/reskit/_test/data/sarah-like' 
   ```

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
snakemake --cores 1 --until generate_dataset       # only if SLURM does not have access to the internet
snakemake --profile workflow/slurm
```

To train the model, run the following argument after any of the above:
```
snakemake [<ONE OF THE PREVIOUS>] --until train_rooftop_segmentation   # for the rooftop segmentation model
snakemake [<ONE OF THE PREVIOUS>] --until train_section_segmentation   # for the section segmentation model
snakemake [<ONE OF THE PREVIOUS>] --until train_superstructure_segmentation   # for the superstructure segmentation model
```

![Click here to see the rule diagram](https://jugit.fz-juelich.de/iek-3/groups/data-and-model-integration/patil/pueblas/passion/-/blob/master/assets/rules.png)

---

## Visualizing results (very early stages)

If you want to visualize the results of your pipeline, a local GUI can be instantiated as:

`
python gui/netcdf_visualizer.py
`

When the server is running, you can access the GUI entering the following local address in your browser:

`
http://127.0.0.1:8082/
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

Copyright (c) 2023 Forschungszentrum Jülich GmbH, Institute of Energy and Climate Research – Techno-economic Systems Analysis (IEK-3), 52425 Jülich, Germany

You should have received a copy of the MIT License along with this program.
If not, see https://opensource.org/licenses/MIT

## About Us

We are the [Institute of Energy and Climate Research - Techno-economic Systems Analysis (IEK-3)](https://www.fz-juelich.de/en/iek/iek-3) belonging to the [Forschungszentrum Jülich](https://www.fz-juelich.de/en). Our interdisciplinary department's research is focusing on energy-related process and systems analyses. Data searches and system simulations are used to determine energy and mass balances, as well as to evaluate performance, emissions and costs of energy systems. The results are used for performing comparative assessment studies between the various systems. Our current priorities include the development of energy strategies, in accordance with the German Federal Government’s greenhouse gas reduction targets, by designing new infrastructures for sustainable and secure energy supply chains and by conducting cost analysis studies for integrating new technologies into future energy market frameworks.

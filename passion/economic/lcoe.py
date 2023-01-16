import pathlib
import xarray

import passion.util

# Parameters to take into consideration during the LCOE calculation.
# Any of the properties can be overwritten.
DEFAULT_LCOE_PARAMS = {
  'panel_lifespan': 25,
  'inverter_lifespan': 13,
  'inverter_price_rate': 0.2,
  'other_costs': 200,
  'discount_rate': 0.05,
  'yearly_degradation': 0.005
}

def generate_economic(input_path: pathlib.Path,
                      input_filename: str,
                      output_path: pathlib.Path,
                      output_filename: str,
                      panel_lifespan: int = 25,
                      inverter_lifespan: int = 13,
                      inverter_price_rate: float = 0.2,
                      other_costs: float = 200,
                      discount_rate: float = 0.08,
                      yearly_degradation: float = 0.005):
  '''Generates a CSV file containing the economic potential of the input sections.
  The used metric is the Levelised Cost of Electricity, that divides the overall
  costs of an energy system during its lifetime by its overall benefits, or
  electricity generation.

  The CSV file will contain the following columns:
    -lat: float latitude value of the section center.
    -lon: float longitude value of the section center.
    -yearly_gen: yearly estimated generation of the section in Wh.
    -elevation: sea level of the building.
    -capacity: total capacity of the estimated PV system.
    -tilt: estimated tilt of the section. If flat, an optimal value is given.
    -azimuth: estimated orientation of the section. If flat, an optimal value is given.
    -area: estimated area of the section in square meters.
    -flat: int indicating if the section was estimated to be flat (1) or not (0).
    -outline_xy: list of tuples indicating the section outline relative to the original image.
    -outline_latlon: list of tuples indicating the section outline in latitude and longitude.
    -original_image_name: name of the image from which the rooftop was extracted.
    -section_image_name: name of the generated image of the section in the 'sections' folder.
    -modules_cost: total estimated cost of the system PV modules.
    -lcoe_eur_MWh: levelised cost of electrity of the section during its lifespan in Mega-Watts Hour.


  ---
  
  input_path       -- Path, folder in which the technical potential analysis is stored.
  input_filename   -- str, name for the technical analysis output.
  output_path      -- Path, folder in which the economic potential analysis will be stored.
  output_filename  -- str, name for the economic analysis output.
  '''
  output_path.mkdir(parents=True, exist_ok=True)

  if not input_filename.endswith('.nc'):
    input_filename += '.nc'
  with xarray.open_dataset(str(input_path / input_filename)) as technical_ds:
    print(technical_ds)
    lcoe = calculate_lcoe(technical_ds.section_yearly_system_generation,
                          technical_ds.section_capacity,
                          technical_ds.section_modules_cost,
                          lcoe_params = {
                          'panel_lifespan': panel_lifespan,
                          'inverter_lifespan': inverter_lifespan,
                          'inverter_price_rate': inverter_price_rate,
                          'other_costs': other_costs,
                          'discount_rate': discount_rate,
                          'yearly_degradation': yearly_degradation
                          })
    technical_ds = technical_ds.assign(section_lcoe=lcoe)
  
  if not output_filename.endswith('.nc'):
    output_filename += '.nc'
  technical_ds.to_netcdf(str(output_path / output_filename))

  return

def calculate_lcoe(generation: float, capacity: float, modules_cost: float, lcoe_params: dict):
  '''Calculates the Levelised Cost of Electricity for a yearly electricity generation
  and installation properties.

  The formula takes into account the yearly costs and benefits, degradation factor
  and discount rate. Parameters can be changed in the dictionary DEFAULT_LCOE_PARAMS.

  Returns the average price per Mega-Watt hour during the system lifespan.
  '''
  inverter_price = lcoe_params['inverter_price_rate'] * capacity
  initial_investment = modules_cost + inverter_price + lcoe_params['other_costs']

  maintenance_costs = 0
  total_generation = 0
  for year in range(0, lcoe_params['panel_lifespan']):
    m_costs_y = 0.01 * initial_investment / ((1 + lcoe_params['discount_rate']) ** year)
    maintenance_costs += m_costs_y

    if year == lcoe_params['inverter_lifespan']:
      maintenance_costs += inverter_price

    generation_y = generation - (lcoe_params['yearly_degradation'] ** year) / ((1 + lcoe_params['discount_rate']) ** year)
    total_generation += generation_y

  lcoe = (initial_investment + maintenance_costs) / total_generation
  lcoe_eur_MWh = lcoe * 1000 * 1000

  return lcoe_eur_MWh

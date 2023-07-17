import xarray as xr
import argparse

parser = argparse.ArgumentParser("netcdf-analysis")
parser.add_argument("input_file", help="Input path to the NetCDF file", type=str)
args = parser.parse_args()

def print_summary(ds):
    print('Global dimensions:')
    for dim in ds.dims:
        print(f'* {dim}')
    
    print('Global attributes:')
    for k, v in ds.attrs:
        print(f'* {k}: {v}')

    print('Variables:')
    for item in ds.items():
        name = item[0]
        print(f'* {name}:')
        da = item[1]
        coords = da.coords
        values = da.values
        attrs = da.attrs

        print('\Dimensions:')
        for coord in coords:
            print(f'\t- {coord}')
        print(f'\tValue shape: {values.shape}')
        print(f'\tValue type: {values.dtype}')
        print('\tAttributes:')
        for attr in attrs:
            print(f'\t- {attr}')

if __name__ == "__main__":
    input_file = args.input_file

    ds = xr.open_dataset(input_file)
    
    print_summary(ds)


    '''
    # Rodrigo's testing for trimming PASSION's NetCDF

    minimal_vars = [
        'section_yearly_system_generation',
        'section_capacity',
        'section_modules_cost',
    ]

    minimal_ds = ds[minimal_vars]
    minimal_ds = minimal_ds.rename({"section_yearly_system_generation": "section_yearly_system_gen"})

    minimal_ds['section_modules_cost'] = minimal_ds.section_modules_cost.astype(str)

    print_summary(minimal_ds)
    '''

    #minimal_ds.to_netcdf('workflow/output/sample-z19/technical/technical-minimal-sample.nc')
    
    #print_summary(ds)

    #print('Dictionary representation:')
    #print(ds.to_dict(data=False))
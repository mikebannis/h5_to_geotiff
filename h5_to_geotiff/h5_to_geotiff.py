"""
Extract raster data from an H5 file and save as a GeoTiff. The raster profile must be saved as an
attribute on the layer.
"""
import os
import sys
import json
from typing import List

import h5py
import click
import rasterio as rio
from beautifultable import BeautifulTable, ALIGN_LEFT, WEP_WRAP

REV_CONUS_PROFILE = {
    "driver": "GTiff",
    "nodata": 99.0,
    "width": 48640,
    "height": 33792,
    "count": 1,
    "crs": "+proj=aea +lat_1=20 +lat_2=60 +lat_0=40 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs=True",
    "transform": [90.0, 0.0, -2245497.1304, 0.0, -90.0, 1338250.676],
    "blockxsize": 128,
    "blockysize": 128,
    "tiled": False,
    "compress": "lzw",
    "interleave": "band"
}
REV_OFFSHORE_PROFILE = {
    'crs': 'PROJCS["unknown",GEOGCS["NAD83",DATUM["North American Datum 1983",SPHEROID["GRS 1980",6378137,298.257222101004]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",40],PARAMETER["longitude_of_center",-96],PARAMETER["standard_parallel_1",20],PARAMETER["standard_parallel_2",60],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
    'transform': [90.0, 0.0, -2641009.648820926, 0.0, -90.0, 1383261.013006147],
    'height': 35780,
    'width': 56332,
    'count': 1,
    'compress': 'lzw',
}

PROFILE_MAP = {
    (33792, 48640): REV_CONUS_PROFILE,
    (35780, 56332): REV_OFFSHORE_PROFILE,
}

def terminal_width() -> int:
    return os.get_terminal_size().columns


def get_dataset_name(f: h5py.File, show_description: bool) -> str:
    """
    Display layer selection list to user and return selected layer name
    """
    layers = f.keys()
    if len(layers) == 0:
        click.echo('No layers found in file')
        sys.exit(1)

    table = BeautifulTable(maxwidth=terminal_width(), default_alignment=ALIGN_LEFT)
    layer_map: List[str] = []
    for layer_name in layers:
        layer_map.append(layer_name)
        layer = f[layer_name]
        shape = layer.shape
        attrs = layer.attrs
        descr = attrs['description'] if 'description' in attrs else ''
        dtype = layer.dtype
        if show_description:
            table.rows.append([layer_name, shape, dtype, descr])
        else:
            table.rows.append([layer_name, shape, dtype])


    table.rows.header = [str(x) for x in range(len(layers))]
    if show_description:
        table.columns.header = ['Name', 'Shape', 'dtype', 'Description']
    else:
        table.columns.header = ['Name', 'Shape', 'dtype']
    table.set_style(BeautifulTable.STYLE_COMPACT)
    table.columns.width_exceed_policy = WEP_WRAP
    click.echo(table)

    selection: int = click.prompt('\nSelect layer by number', type=click.IntRange(0, len(layers)-1))
    layer_name = layer_map[selection]
    return layer_name


def print_attributes(layer: h5py.Dataset):
    """ Print attributes in a layer"""
    if len(layer.attrs) == 0:
        click.echo('Layer has no attributes')
        return

    table = BeautifulTable(maxwidth=terminal_width(), default_alignment=ALIGN_LEFT)
    for attr, value in layer.attrs.items():
        table.rows.append([attr, value])
    table.columns.header = ['Attribute', 'Value']
    table.set_style(BeautifulTable.STYLE_COMPACT)
    table.columns.width_exceed_policy = WEP_WRAP
    click.echo(table)


def get_profile(layer: h5py.Dataset, layer_name: str) -> dict:
    """
    Get profile from layer attributes or optionally use known profile based on resolution.
    """
    if 'profile' in layer.attrs:
        return  json.loads(layer.attrs['profile'])

    click.echo(f'Layer {layer_name} doesn\'t have a profile stored in the attributes.')

    shape = layer.shape if len(layer.shape) == 2 else layer.shape[1:]
    if shape not in PROFILE_MAP:
        click.echo('Layer resolution does not have a known profile. Aborting')
        sys.exit(1)

    if not click.confirm('There is a known profile for the resolution of of this layer. '
                         'Should I attempt to use it to make a GeoTiff? Resulting '
                         'georeferencing may not be valid.'):
        click.echo('Bye!')
        sys.exit(0)

    profile = PROFILE_MAP[shape]
    profile['dtype'] = layer.dtype
    return profile


@click.command()
@click.argument('h5_file', type=click.Path(exists=True),)
@click.option ('-a', '--attributes', is_flag=True, default=False, help='Show attributes for '
               'selected layer and exit without creating GeoTiff.')
@click.option ('-d', '--descriptions', is_flag=True, default=False, help='Show layer '
               'descriptions in layer list.')
def main(h5_file: str, attributes: bool, descriptions: bool):
    """
    Convert a dataset in an H5 file to a GeoTiff.

    H5_FILE is the H5 file to extract data from.
    """
    with h5py.File(h5_file, "r") as f:
        layer_name = get_dataset_name(f, descriptions)
        layer = f[layer_name]
        if attributes:
            click.echo()
            print_attributes(layer)
            sys.exit(0)

        profile = get_profile(layer, layer_name)

        print(f'Loading layer {layer_name} from {h5_file}...')
        if len(layer.shape) == 3:
            data = layer[0, :, :]
        elif len(layer.shape) == 2:
            data = layer[:, :]
        else:
            click.echo(f'Layer must have 2 or 3 dimensions to convert. {layer_name} has '
                       f'{len(layer.shape)}')
            sys.exit(1)

    click.echo(f'Loaded. Shape: {data.shape}, min: {data.min()}, max: '
               f'{data.max()}, dtype: {data.dtype}')

    if 'dtype' not in profile:
        profile['dtype'] = data.dtype
    if 'compress' not in profile:
        profile['compress'] = 'lzw'

    assert profile['dtype'] == data.dtype
    assert profile['height'] == data.shape[0]
    assert profile['width'] == data.shape[1]

    tiff_name = f'{layer_name}.tif'
    click.echo(f'Writing data to {tiff_name}')
    with rio.open(tiff_name, 'w', **profile) as outf:
        outf.write(data, indexes=1)


if __name__ == '__main__':
    main() # pylint: disable=no-value-for-parameter

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
from beautifultable import BeautifulTable, ALIGN_LEFT, WEP_WRAP, WEP_ELLIPSIS


def terminal_width() -> int:
    return os.get_terminal_size().columns


def get_dataset_name(f: h5py.File) -> str:
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
        table.rows.append([layer_name, shape, dtype, descr])

    table.rows.header = [str(x) for x in range(len(layers))]
    table.columns.header = ['Name', 'Shape', 'dtype', 'Description']
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


@click.command()
@click.argument('h5_file', type=click.Path(exists=True),)
@click.option ('-s', '--show-attributes', is_flag=True, default=False, help="Show layer attributes "
               'and exit without creating GeoTiff.')
def main(h5_file: str, show_attributes: bool):
    """
    Convert a dataset in an H5 file to a GeoTiff.

    H5_FILE is the H5 file to extract data from.
    """
    with h5py.File(h5_file, "r") as f:
        layer_name = get_dataset_name(f)
        layer = f[layer_name]
        if show_attributes:
            click.echo()
            print_attributes(layer)
            sys.exit(0)

        if 'profile' not in layer.attrs:
            click.echo(f'Layer {layer_name} doesn\'t have a profile attribute. Aborting')
            sys.exit(1)
        profile = json.loads(layer.attrs['profile'])

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
    main()

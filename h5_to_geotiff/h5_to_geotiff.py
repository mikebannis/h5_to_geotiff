"""
Extract raster data from an H5 file and save as a GeoTiff. The raster profile must be saved as an
attribute on the layer.
"""
import sys
import h5py
import json
import click
import rasterio as rio

from typing import List


def get_dataset_name(f: h5py.File) -> str:
    """
    Display layer selection list to user and return selected layer name
    """
    layers = f.keys()
    if len(layers) == 0:
        click.echo(f'No layers found in file')
        sys.exit(1)

    click.echo('Available datasets:')
    layer_map: List[str] = []
    for i, layer_name in enumerate(layers):
        layer_map.append(layer_name)
        layer = f[layer_name]
        shape = layer.shape
        attrs = layer.attrs
        descr = attrs['description'] if 'description' in attrs else ''
        dtype = layer.dtype
        click.echo(f'\t{i}) {layer_name} \t{shape} \t{dtype} \t{descr}')

    selection: int = click.prompt('Select layer by number', type=click.IntRange(0, len(layers)-1))
    layer_name = layer_map[selection]
    return layer_name


@click.command()
@click.argument('h5_file', type=click.Path(exists=True),)
def main(h5_file: str):
    """
    Convert a dataset in an H5 file to a GeoTiff.

    H5_FILE is the H5 file to extract data from.
    """
    with h5py.File(h5_file, "r") as f:
        layer_name = get_dataset_name(f)
        layer = f[layer_name]

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

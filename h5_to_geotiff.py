import h5py
import json
import pandas as pd
import rasterio as rio

profile = {
    'crs': 'PROJCS["unknown",GEOGCS["NAD83",DATUM["North American Datum 1983",SPHEROID["GRS 1980",6378137,298.257222101004]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",40],PARAMETER["longitude_of_center",-96],PARAMETER["standard_parallel_1",20],PARAMETER["standard_parallel_2",60],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
    'transform': [90.0, 0.0, -2641009.648820926, 0.0, -90.0, 1383261.013006147],
    'height': 35780,
    'width': 56332,
    'count': 1,
    'compress': 'lzw',
}
# h5_file = './20231110_wowts_costs.h5'
h5_file = '/shared-projects/rev/exclusions/xmission_costs.h5'
layer = 'tie_line_costs_102MW'

with h5py.File(h5_file, "r") as ds:
    data = ds[layer][0, :, :]
    profile = json.loads(ds[layer].attrs['profile'])


breakpoint()
print(data.shape, data.min(), data.max())

if 'dtype' not in profile:
    profile['dtype'] = data.dtype

assert profile['dtype'] == data.dtype
assert profile['height'] == data.shape[0]
assert profile['width'] == data.shape[1]

with rio.open(f'{layer}.tif', 'w', **profile) as outf:
    outf.write(data, indexes=1)

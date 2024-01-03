# H5-to-GeoTiff

Convert raster data in an H5 file to a GeoTiff. The raster data must have a profile defined
in the dataset attributes.

## Install

Install all dependancies and the CLI command with:

```
$ pip install -e .
```

## Use

Extract data and save as tiff as follows:

```
$ h5-to-geotiff /shared-projects/rev/exclusions/xmission_costs.h5
```

Available layers will be displayed and the user prompted to select one.

## Issues

Likely many. Datasets cannot be in groups.

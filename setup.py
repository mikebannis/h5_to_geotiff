from setuptools import setup

with open("requirements.txt") as f:
    install_requires = f.readlines()

setup(
    name='h5_to_geotiff',
    author='Mike Bannister',
    version='0.0.2',
    entry_points={
        'console_scripts': ['h5-to-geotiff=h5_to_geotiff.h5_to_geotiff:main']
    },
    install_requires=install_requires,
)
import os
import glob
import setuptools
from distutils.core import setup

with open("README.md", 'r') as readme:
    long_description = readme.read()

setup(
    name='smoldyn-process',
    version='0.0.1',
    packages=[
        'smoldyn_process',
        'smoldyn_process.processes',
        'smoldyn_process.composites',
        'smoldyn_process.experiments',
    ],
    author='Eran Agmon, Steve Andrews, Ryan Spangler, Alex Patrie',
    author_email='eagmon@stanford.edu, steven.s.andrews@gmail.com, ryan.spangler@gmail.com, apatrie@uchc.edu',
    url='https://github.com/vivarium-collective/smoldyn-process',
    license='MIT',
    entry_points={
        'console_scripts': []
    },
    short_description='A Process-bigraph wrapper for Smoldyn',
    long_description=long_description,
    long_description_content_type='text/markdown',
    package_data={},
    include_package_data=True,
    install_requires=[
        'process-bigraph',
        'biosimulators-simularium',
        'smoldyn',
        'jupyterlab'
    ],
)

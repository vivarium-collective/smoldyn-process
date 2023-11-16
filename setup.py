import re
from setuptools import setup, find_packages


VERSION = '0.0.1'


with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="smoldyn-process",
    version=VERSION,
    author="Alex Patrie/Eran Agmon",
    author_email="apatrie@uchc.edu/agmon.eran@gmail.com",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vivarium-collective/smoldyn-process",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.6",
)

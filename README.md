**Update on August 16th, 2021:** Another set of scripts with some application-specific up-scaling focus has been created in the repository [PebbleCounts-Application](https://github.com/UP-RS-ESP/PebbleCounts-Application). The manuscript associated with this application is: https://doi.org/10.1029/2021JF006260.

# Introduction to PebbleCounts
PebbleCounts is a Python based application for the identification and sizing of gravel from either orthorectified, georeferenced (**UTM projected**) images with known resolution or simple non-orthorectified images taken from directly overhead with the image resolution approximated by the camera parameters and shot height. Read about it (and cite it!) here:

Purinton, B. and Bookhagen, B.: Introducing PebbleCounts: a grain-sizing tool for photo surveys of dynamic gravel-bed rivers, Earth Surf. Dynam., 7, 859–877, [https://doi.org/10.5194/esurf-7-859-2019](https://doi.org/10.5194/esurf-7-859-2019), 2019.

[FULL MANUAL INCLUDING INSTALL AND RUNNING](docs/PebbleCounts_Manual.pdf)

<img src="docs/figs/logo.png" width="300px" >

# Software Citation
Purinton, Benjamin; Bookhagen, Bodo (2019): PebbleCounts: a Python grain-sizing algorithm for gravel-bed river imagery. V. 1.0. GFZ Data Services. [http://doi.org/10.5880/fidgeo.2019.007](http://doi.org/10.5880/fidgeo.2019.007)

# License
GNU General Public License, Version 3, 29 June 2007

Copyright © 2019 Benjamin Purinton, University of Potsdam, Potsdam, Germany

PebbleCounts is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. PebbleCounts is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

## Disclaimer
PebbleCounts is a free (released under GNU General Public License v3.0) and open-source application written by a geologist / amateur programmer. If you have any problems contact me [purinton@uni-potsdam.de](purinton@uni-potsdam.de) and I can help!

# Quick note on imagery and running PebbleCounts
Georeferenced ortho-photos should be in a [**UTM projection**](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system), providing the scale in meters. You can use the [gdal](https://www.gdal.org/) command line utilities to [translate rasters between various projections](https://www.nceas.ucsb.edu/scicomp/recipes/gdal-reproject). Because PebbleCounts doesn't allow you to save work in the middle of clicking it's recommended that you don't use images covering areas of more than 2 by 2 meters or so. Furthermore, the algorithm is most effective on images of 0.8-1.2 mm/pixel resolution, where a lower cutoff of 20-pixels is appropriate. Resampling can also be accomplished quickly in [gdal](https://www.gdal.org/). For higher resolution (< 0.8 mm/pixel) imagery it's recommended not to go above 1 by 1 meter areas, particularly if there are many < 1 cm pebbles. If you want to cover a larger area simply break the image into smaller parts and process each individually, so you can give yourself a break. If at anytime you want to end the application simply press *CTRL + C*.

## The PebbleCountsAuto Function
In addition to the manual-clicking version of PebbleCounts based on k-means segmentation, we have also developed and included an automated version that has higher uncertainties. We recommend using PebbleCounts in a subset of data to validate larger areas run in PebbleCountsAuto. The description of the automatic algorithm and uncertainties can be found in the publication (**PUBLICATION DOI TO BE ADDED**).

# Installation
The first step is downloading the GitHub repository somewhere on your computer, and unzipping it. There you will find the Python algorithms (e.g., `PebbleCounts.py`), an `environment.yml` file containing the Python dependencies for quick installs with `conda` on Windows, a folder `example_data` with two example images one orthorectified and the other raw, and a folder `docs` containing the [full manual](docs/PebbleCounts_Manual.pdf).

For newcomers to Python, no worries! Installation should be a cinch on most machines. First, you'll want the [Miniconda](https://conda.io/miniconda.html) Python package manager to setup a new Python environment for running the algorithm ([see this good article on Python package management](https://medium.freecodecamp.org/why-you-need-python-environments-and-how-to-manage-them-with-conda-85f155f4353c)). Download either the 32- or 64-bit Miniconda installer of Python 3.x then follow the instructions (either using the `.exe` file for Windows, `.pkg` for Mac, or `bash installer` for Linux). Add Miniconda to the system `PATH` variable when prompted.

PebbleCounts has a number of important dependencies including [gdal](https://www.gdal.org/) for georeferenced raster manipulation, [openCV](https://opencv.org/) for image manipulation and GUI operation, [scikit-image](https://scikit-image.org/) for filtering and measuring, [scikit-learn](https://scikit-learn.org/stable/) for k-means segmentation, [shapely](https://shapely.readthedocs.io/en/latest/) for geometry operations, along with a number of standard Python libraries including [numpy](http://www.numpy.org/), [scipy](https://www.scipy.org/), [matplotlib](https://matplotlib.org/), and [tkinter](https://wiki.python.org/moin/TkInter).

### For Windows
Once you've got `conda` commands installed, you can open a command-line terminal and create a conda environment with:
```
conda create --name pebblecounts python=3.6 opencv shapely \
   scikit-image scikit-learn numpy gdal scipy matplotlib tk
```
Or just use the `.yml` file provided with:
```
conda env create -f environment.yml
```
and once installation is complete (and assuming no errors during the install) activate the new environment to run PebbleCounts by:
```
activate pebblecounts
```
Deactivate the environment to exit anytime by:
```
deactivate
```

### For Mac and Linux Users
Those using Mac OS or Linux shouldn't have much trouble modifying the above commands slightly (just add a leading `conda` to the `activate` and `deactivate` commands above). Also we need to install `opencv` separately from within the virtual environment using the `pip` package manager.

Similar to the above, once you have `conda` installed we create the virtual environment:
```
conda create --name pebblecounts python=3.6 shapely \
   scikit-image scikit-learn numpy gdal scipy matplotlib tk
```
and once installation is complete (and assuming no errors during the install) activate the new environment by:
```
conda activate pebblecounts
```
We've left out the opencv package which must be installed with the following `pip` command in the activated `pebblecounts` environment:
```
pip install opencv-python
```
Deactivate the environment to exit anytime by:
```
conda deactivate
```

#### Issues with opencv on Mac and Linux
Note that installing openCV and getting it to function properly can be a pain sometimes, especially in the case of Linux. In that case it is recommended to find some instructions for installing openCV's Python API for your specific Linux operating system [online](https://www.pyimagesearch.com/2018/05/28/ubuntu-18-04-how-to-install-opencv/).

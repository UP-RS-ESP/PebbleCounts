---
title: "PebbleCounts Grain-sizing Application"
date: "November 2018"
author: "Ben Purinton ([purinton@uni-potsdam.de](purinton@uni-potsdam.de))"
---

# Introduction to PebbleCounts
PebbleCounts is a Python based application for the identification and sizing of gravel from either orthorectified, georeferenced images with known resolution or simple non-orthorectified images taken from directly overhead with the image resolution approximated by the camera parameters and shot height. If you really want some deeper background on the problem of grain size measurement from imagery and the testing of PebbleCounts, check out the publication accompanying the algorithm: PUBLICATION DOI. And cite it if you use the algorithm in your own work.

Happy clicking!

## Disclaimer
PebbleCounts is a free (released under GNU General Public License v3.0) and open-source application written by a geologist / amateur programmer. If you have problems installing or running the software *please* contact me [purinton@uni-potsdam.de](purinton@uni-potsdam.de) and I can help!

# Overview
To briefly summarize, PebbleCounts pre-processes the image by allowing the user to subset the full scene, then interactively masks shadows (interstices between grains) and color (for instance sand). Following this, PebbleCounts windows the scene at three different scales with the window size determined by the input resolution and expected maximum grain size provided by the user. This multi-scale approach allows the algorithm to "burrow" through the grain size distribution beginning by removing the largest grains and ending on the smallest, with the medium sizes in between.

At each window the algorithm filters the image, detects edges, and employs [k-means segmentation](https://scikit-learn.org/stable/modules/clustering.html#k-means) to get an approximate cleaned-up mask of potential separate pebbles. The window is then shown with the mask overlain and the user is able to click the **good** looking grains and leave out the **bad** ones (see the [full manual](docs/PebbleCounts_Manual_Nov2018.md) for the example). These grains are then measured via ellipse fitting to retrieve the long- and short-axis and orientation. This process is iterated through each window and the output from the counting is provided as a comma separated value (.csv) file for user manipulation.

### Flowchart for PebbleCounts
<img src="docs/figs/pebblecounts_flowchart.png" width="500">

# Installation
The first step is downloading the GitHub repository somewhere on your computer. The folder should contain:
1. Three Python scripts: PebbleCounts.py, PCfunctions.py, calculate_camera_resolution.py
2. An `environment.yml` file containing the Python dependencies
3. A folder `example_data` with two example images one orthorectified and the other raw
4. A folder `docs` containing the [full manual](docs/PebbleCounts_Manual_Nov2018.md)

## For the Pros
For those familiar with Python, the best way to install PebbleCounts is by simply downloading the GitHub repository, navigating to the PebbleCounts folder at the command line, ensuring all Python dependencies are installed (see the `environment.yml` file) and getting started by skipping ahead to **Command-line Options**

## For Newbies 
For newcomers to Python, no worries! Installation should be a cinch on most machines and I'll describe it here for Windows. First of all you'll want the [Miniconda](https://conda.io/miniconda.html) Python package manager to setup a new Python environment for running the algorithm ([see this good article on Python package management](https://medium.freecodecamp.org/why-you-need-python-environments-and-how-to-manage-them-with-conda-85f155f4353c)). 

Download either the 32- or 64-bit installer of Python 3.x then follow the installation instructions. It's recommend to add Miniconda to the system `PATH` variable when prompted. PebbleCounts has a number of important dependencies including [gdal](https://www.gdal.org/) for geo-referenced raster manipulation, [openCV](https://opencv.org/) for image manipulation and GUI operation, [scikit-image](https://scikit-image.org/) for filtering and measuring, [scikit-learn](https://scikit-learn.org/stable/) for k-means segmentation, along with a number of standard Python libraries including [numpy](http://www.numpy.org/), [scipy](https://www.scipy.org/), [matplotlib](https://matplotlib.org/), and [tkinter](https://wiki.python.org/moin/TkInter).

Once you've got `conda` commands installed, you can open a command-line terminal and create a conda environment with:
```
conda create --name pebblecounts python=3.6 opencv \
   scikit-image scikit-learn numpy gdal scipy matplotlib tk
```
Or just use the environment .yml file provided with:
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

## For Mac and Linux Users
Those using Mac OS or Linux shouldn't have much trouble modifying the above commands slightly (just add a leading `source` to the `activate` and `deactivate` commands above). Note that installing openCV and getting it to function properly can be a pain sometimes, especially in the case of Linux. In that case it is recommended to find some instructions for installing openCV's Python API for your specific Linux operating system [online](https://www.pyimagesearch.com/2018/05/28/ubuntu-18-04-how-to-install-opencv/), but I don't absolve myself from helping, so you can always *contact me*.

# Command-line Options
Great you've got it installed\! Hopefully that is, we're about to find out\! The first step to running the software is navigating to the directory where the three scripts live. On Windows that might look like:
```
cd C:\Users\YourName\PebbleCounts
```
Just replace everything after `cd` with the path on your computer to the downloaded `PebbleCounts` folder.

## Calculate Camera Resolution
First off, if the imagery you intend to use is not orthorectified and georeferenced you'll want to calculate the approximate ground resolution of the photos in millimeters per pixel. To do so you can run the script `calculate_camera_resolution.py` at the command line.
Parameters to be provided can be listed with ```python calculate_camera_resolution.py -h```. Here they all are:
```
usage: calculate_camera_resolution.py [-h] [-focal FOCAL] [-height HEIGHT]
                                      [-sensorHW SENSORHW [SENSORHW ...]]
                                      [-imageHW IMAGEHW [IMAGEHW ...]]

optional arguments:
  -h, --help            show this help message and exit
  -focal FOCAL          Camera focal length in millimeters
  -height HEIGHT        Photo capture height in meters
  -sensorHW SENSORHW [SENSORHW ...]
                        The height and width of the internal camera sensor in
                        millimeters
  -imageHW IMAGEHW [IMAGEHW ...]
                        The height and width of the photography in pixels
```

#### Example Use
Let's say I have a photo that I took from a height of 1.5 meters at a camera focal length of 35 mm. The camera has a [sensor size](https://en.wikipedia.org/wiki/Image_sensor_format) of 15 by 26 mm and was shot at 24 MP resolution, providing a 4000 pixel high by 6000 pixel wide picture. My command would look like this:
```
python calculate_camera_resolution.py -focal 35 -height 1.5 -sensorHW 15 26 -imageHW 4000 6000
```
And the output printed to the screen would be:
```
Focal length 35.00 mm; Shot from 1.50 m; Sensor size (15.00, 26.00) mm; Image size (4000, 6000) pixels:

The field of view is 0.64 by 1.11 m

approximate (x,y) resolution in mm/pixel = (0.1607, 0.1857)
average resolution in mm/pixel = 0.1732
```
And I could then pass this resolution (`0.1732`) to the `PebbleCounts.py` script.

**Note on Shot Height:** If you aren't sure exactly what height the image was shot from, use an approximate value. Even for differences of up to 1 m in shot height the ground resolution for most cameras will change by less than 0.2 mm, and thus have a negligible effect on the resulting grain-sizes measured.

## PebbleCounts
The code can be run from the command line with
```
python PebbleCounts.py ...
```
Parameters to be provided can be listed with ```python PebbleCounts.py -h```. Here they all are:
```
usage: PebbleCounts.py [-h] [-im IM] [-ortho ORTHO]
                       [-input_resolution INPUT_RESOLUTION]
                       [-lithologies LITHOLOGIES] [-maxGS MAXGS]
                       [-cutoff CUTOFF]
                       [-min_sz_factors MIN_SZ_FACTORS [MIN_SZ_FACTORS ...]]
                       [-win_sz_factors WIN_SZ_FACTORS [WIN_SZ_FACTORS ...]]
                       [-improvement_ths IMPROVEMENT_THS [IMPROVEMENT_THS ...]]
                       [-coordinate_scales COORDINATE_SCALES [COORDINATE_SCALES ...]]
                       [-overlaps OVERLAPS [OVERLAPS ...]]
                       [-nl_means_chroma_filts NL_MEANS_CHROMA_FILTS [NL_MEANS_CHROMA_FILTS ...]]
                       [-bilat_filt_szs BILAT_FILT_SZS [BILAT_FILT_SZS ...]]
                       [-tophat_th TOPHAT_TH] [-sobel_th SOBEL_TH]
                       [-canny_sig CANNY_SIG] [-resize RESIZE]

optional arguments:
  -h, --help            show this help message and exit
  -im IM                The image to use including the full path and
                        extension.
  -ortho ORTHO          'y' if geo-referenced ortho-image, 'n' if not. Supply
                        input resolution if 'n'.
  -input_resolution INPUT_RESOLUTION
                        If image is not ortho-image, input the calculated
                        resolution from calculate_camera_resolution.py
  -lithologies LITHOLOGIES
                        What is the expected number of lithologies with
                        distinct colors? DEFAULT=1
  -maxGS MAXGS          Maximum expected longest axis grain size in meters.
                        DEFAULT=0.3
  -cutoff CUTOFF        Cutoff factor in pixels for inclusion of pebble in
                        final count. DEFAULT=10
  -min_sz_factors MIN_SZ_FACTORS [MIN_SZ_FACTORS ...]
                        Factors to multiply cutoff value by at each scale.
                        Used to clean-up the masks for easier clicking. The
                        default values are good for ~1 mm/pixel imagery but
                        should be doubled for sub-millimeter or halved for
                        centimeter resolution imagery. DEFAULT=[100, 10, 2]
  -win_sz_factors WIN_SZ_FACTORS [WIN_SZ_FACTORS ...]
                        Factors to multiply maximum grain-size (in pixels) by
                        at each scale. The default values are good for
                        millimeter and sub-millimeter imagery, but should be
                        doubled for coarser centimeter imagery. DEFAULT=[10,
                        2, 0.5]
  -improvement_ths IMPROVEMENT_THS [IMPROVEMENT_THS ...]
                        Improvement threshold values for each window scale
                        that tells k-means when to halt. DEFAULT=[0.01, 0.1,
                        0.1]
  -coordinate_scales COORDINATE_SCALES [COORDINATE_SCALES ...]
                        Fraction to scale X/Y coordinates by in k-means.
                        DEFAULT=[0.5, 0.5, 0.5]
  -overlaps OVERLAPS [OVERLAPS ...]
                        Fraction of overlap between windows at the different
                        scales. DEFAULT=[0.5, 0.3, 0.1]
  -nl_means_chroma_filts NL_MEANS_CHROMA_FILTS [NL_MEANS_CHROMA_FILTS ...]
                        Nonlocal means chromaticity filtering strength for the
                        different scales. DEFAULT=[3, 2, 1]
  -bilat_filt_szs BILAT_FILT_SZS [BILAT_FILT_SZS ...]
                        Size of bilateral filtering windows for the different
                        scales. DEFAULT=[9, 5, 3]
  -tophat_th TOPHAT_TH  Top percentile threshold to take from tophat filter
                        for edge detection. DEFAULT=90
  -sobel_th SOBEL_TH    Top percentile threshold to take from sobel filter for
                        edge detection. DEFAULT=90
  -canny_sig CANNY_SIG  Canny filtering sigma value for edge detection.
                        DEFAULT=2
  -resize RESIZE        Value to resize windows by should be between 0 and 1.
                        DEFAULT=0.8
```

Here's a bit more detail on some of the less obvious inputs to clarify:

* `-resize` controls the pop-up window size for the GUI. If you notice the window is too small to see the grains then use a high value like 0.9, but if the image is partially off-screen you should try lowering the value to around 0.7.
* `-lithologies` is the expected number of different rock types in the image with distinct coloration differences. It defaults to 1, meaning the lithology is uniform or the color differences between lithologies are minimal and therefore difficult to discern from the image alone.
* `-maxGS` is the expected size in meters of the largest rock in the image based on some field knowledge. This value is used during the windowing to set the appropriate sizes at the three scales in conjunction with the `-win_sz_factors` input.
* `-cutoff` is the algorithm's lower limit on b-axis measurement given in pixels. The default value of 10 is what we found to be reliable for accurate distribution measurement using PebbleCounts. This value is also used by the `-min_sz_factors` input to cleanup the mask at each of the three window scales and should also be scaled depending on the imagery resolution (sub-mm, mm, cm).
* `-improvement_ths` is the fractional percentage (from 0-1) that k-means uses to assess convergence and stopping. The default values are probably good here.
* `-coordinate_scales` is the fractional percentage (from 0-1) to scale the x,y coordinates of each pixel compared with the color information in the k-means segmentation. Since we want to allow for anisotropic grains covering large areas if they have semi-uniform color, we want to scale the relative importance of pixel location by approximately 50% of the color, hence the default values of 0.5 at each scale.
* `-nl_means_chroma_filts` is the level of chromaticity filtering to apply during [non-local means denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html), which should be reduced at each scale. Higher values lead to more smoothing of the image and a cartoonish appearance. The default values should again be good here.
* `-bilat_filt_szs` is the square window size to apply for [bilateral filtering](https://docs.opencv.org/3.1.0/d4/d13/tutorial_py_filtering.html), with the aim of further smoothing the image while preserving interstices between the grains. The size of this filter window should be reduced with the windowing scale. The default values are also good here.
* `-tophat_th`, `-sobel_th`, and `-canny_sig` are the [tophat](http://scikit-image.org/docs/dev/api/skimage.morphology.html#skimage.morphology.black_tophat) filter percentile threshold, [Sobel](http://scikit-image.org/docs/dev/api/skimage.filters.html#skimage.filters.sobel) filter percentile threshold, and [Canny](http://scikit-image.org/docs/dev/auto_examples/edges/plot_canny.html) edge detection smoothing standard deviation. These are the values used on edge detection from the gray-scale image and are probably good at the default value. The same value is used for each scale.

# Running PebbleCounts
Now you're ready to run an image. Because PebbleCounts doesn't allow you to save work in the middle of clicking it's recommended that you don't use images covering areas of more than 2 by 2 meters or so. For higher resolution (sub-mm) imagery it's recommended not to go above 1 by 1 meters. If you want to cover a larger area simply break the image into smaller parts and process each individually, so you can give yourself a break. Head-over to the [full manual](docs/PebbleCounts_Manual_Nov2018.md) for a step-by-step guide to running PebbleCounts for a given image
# PebbleCountsAuto - a tool for measuring gravel-bed river grain-size
#       Developed by Ben Purinton (purinton[at]uni-potsdam.de)
#       26 March 2019
#       See the help manual for instructions on use at: https://github.com/bpurinton/PebbleCounts

# =============================================================================
# Load the modules
# =============================================================================

import os, csv, time, argparse, sys
import cv2
import numpy as np
import PCfunctions as func
from osgeo import gdal, osr, ogr
from scipy import ndimage as ndi
from skimage import color
from skimage import measure as meas
from skimage import segmentation as segm
from skimage import feature as feat
from skimage import morphology as morph
from skimage import filters as filt
import matplotlib.pyplot as plt
from matplotlib.path import Path
from shapely.geometry.point import Point
from shapely.geometry.polygon import Polygon
# ignore some warnings thrown by sci-kit
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# =============================================================================
# Argument parser, set from the command-line
# =============================================================================

# Get the arguments
parser = argparse.ArgumentParser()
parser.add_argument("-im", type=str,
                    help="The image to use including the path to folder and extension.")
parser.add_argument("-ortho", type=str,
                    help="'y' if geo-referenced ortho-image, 'n' if not. Supply input resolution if 'n'.")
parser.add_argument("-input_resolution", type=float,
                    help="If image is not ortho-image, input the calculated resolution from calculate_camera_resolution.py")
parser.add_argument("-subset", type=str,
                    help="'y' to interactively subset the image, 'n' to use entire image. DEFAULT='n'", default='n')
parser.add_argument("-sand_mask", type=str,
                    help="The name with the path to folder and extension to a sand mask GeoTiff if one already exists.")
parser.add_argument("-otsu_threshold", type=int,
                    help="Percentage of Otsu value to threshold by. Supplied to skip the interactive thresholding step.", default=None)
parser.add_argument("-cutoff", type=int,
                    help="Cutoff factor (minimum b-axis length) in pixels for found pebbles. DEFAULT=20", default=20)
parser.add_argument("-percent_overlap", type=int,
                    help="Maximum allowable overalp percentage between neighboring ellipses for filtering suspect grains. DEFAULT=15", default=15)
parser.add_argument("-misfit_threshold", type=int,
                    help="Maximum allowable percentage misfit between ellipse and grain mask for filtering suspect grains. DEFAULT=30", default=30)
parser.add_argument("-min_size_threshold", type=int,
                    help="Minimum area of grain (in pixels) to be considered in count. Used to clean the grain mask. 10 is good for ~1 mm/pixel images, 20 for < 0.8 mm/pixel. DEFAULT=10", default=10)
parser.add_argument("-first_nl_denoise", type=int,
                    help="Initial denoising non-local means chromaticity filtering strength. DEFAULT=5", default=5)
parser.add_argument("-tophat_th", type=float,
                    help="Top percentile threshold to take from tophat filter for edge detection. DEFAULT=90", default=90)
parser.add_argument("-sobel_th", type=float,
                    help="Top percentile threshold to take from sobel filter for edge detection. DEFAULT=90", default=90)
parser.add_argument("-canny_sig", type=int,
                    help="Canny filtering sigma value for edge detection. DEFAULT=2", default=2)
parser.add_argument("-resize", type=float,
                    help="Value to resize windows by should be between 0 and 1. DEFAULT=0.8", default=0.8)
args = parser.parse_args()

# =============================================================================
# Configure the run with command line arguments
# =============================================================================

# assign and test the arguments
im = args.im
resize = args.resize
sand_mask = args.sand_mask
otsu_threshold = args.otsu_threshold
cutoff = args.cutoff
first_nl_denoise = args.first_nl_denoise
tophat_th = args.tophat_th
canny_sig = args.canny_sig
sobel_th = args.sobel_th
perc_overlap = args.percent_overlap
misfit_threshold = args.misfit_threshold
min_size = args.min_size_threshold
subset = args.subset

# exit if there was no image supplied or the file doesn't exist
if im == None:
    print("\nSupply and image with the -im command line argument")
    sys.exit()
elif not os.path.exists(im):
    print("\nThe image doesn't exist, check the path and name")
    sys.exit()
else:
    pass

# also exit if there was no ortho option supplied or if there was no input resolution
ortho = args.ortho
if ortho == 'n':
    ortho=False
elif ortho == 'y':
    ortho=True
else:
    print("\nIs the input image an ortho? Use '-ortho y' or '-ortho n'")
    sys.exit()
input_resolution = args.input_resolution
if not ortho and input_resolution == None:
    print("\nSupply an input image resolution with '-input_resolution' calculated with 'calculate_camera_resolution.py'")
    sys.exit()

# assign output files
base_name = os.path.splitext(os.path.basename(im))[0]
base_dir = os.path.dirname(im)
csv_out = os.path.join(base_dir, base_name + "_PebbleCountsAuto_CSV.csv")
im_out = os.path.join(base_dir, base_name + "_PebbleCountsAuto_LABELS.tif")
fig_out = os.path.join(base_dir, base_name + "_PebbleCountsAuto_FIGURE.png")
sand_mask_tiff_out = os.path.join(base_dir, base_name + "_PebbleCounts_SandMask_TIFF.tif")
sand_mask_shp_out = os.path.join(base_dir, base_name + "_PebbleCounts_SandMask_SHP.shp")

# check existence of outputs and warn the user
overwrite=None
if os.path.exists(csv_out):
    print("\nLooks like the .csv exists already\n")
    while True:
        overwrite = input("Do you want to overwrite previous run? ('y' or 'n'): ")
        if overwrite=='y' or overwrite=='n':
            break
        else:
            print("incorrect input, should be 'y' or 'n'")
if overwrite=='y':
    print("\nFiles will be overwritten\n")
elif overwrite=='n':
    print("\nEnding the script, move the files to a different directory or rename them to proceed\n")
    sys.exit()
else:
    print("No output files exist for the image yet, proceeding\n")

# open the datset and get the step size if ortho image
if ortho:
    ds = gdal.Open(im)
    gt = ds.GetGeoTransform()
    ds = None
    step = gt[1]
# otherwise take the given input_resolution
if not ortho:
    step = input_resolution
    # convert to meters
    step /= 1000

# get start time
start = time.time()

# =============================================================================
# Pre-process the entire image (subsetting, shadow masking, color masking)
# =============================================================================

# subset the image?
if subset=='y':
    while True:
        img = cv2.imread(im)
        win_name = "ROI Selector ('spacebar' to end)"
        cv2.startWindowThread()
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(win_name, 0, 0)
        cv2.resizeWindow(win_name, func.resizeWin(img, resize)[0],
                         func.resizeWin(img, resize)[1])
        r = cv2.selectROI(win_name, img, False, False)
        if r[2] < 10 or r[3] < 10:
            print("\nBad ROI: {}\nThe image will not be subset, try again".format(str(r)))
            cv2.destroyAllWindows()
        else:
            cv2.destroyAllWindows()
            break

# read the image
if subset=='y':
    bgr = cv2.imread(im)[int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
else:
    bgr = cv2.imread(im)

# do strong nonlocal means denoising
print("\nNon-local means filtering of color image")
bgr = cv2.fastNlMeansDenoisingColored(bgr, None, first_nl_denoise, 1, 7, 21)

# get the X/Y UTM grid if it's an ortho image
if ortho:
    if subset=='y':
        xgrid = func.getXYgrid(im)[0][int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
        ygrid = func.getXYgrid(im)[1][int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
    else:
        xgrid, ygrid = func.getXYgrid(im)

# create gray and do otsu thresholding to remove shadow regions
if not otsu_threshold == None:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    otsu_th, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    ignore_mask = gray > otsu_th*(otsu_threshold/100)
else:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    otsu_th, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    otsu_thresholding = func.otsu_threshold()
    while True:
        otsu_thresholding.percent_of_otsu(otsu_th)
        otsu_thresholding.apply_threshold(gray, bgr, otsu_th, resize)
        if otsu_thresholding.thresh != None:
            otsu_threshold = otsu_thresholding.thresh
            ignore_mask = gray > otsu_th*(otsu_threshold/100)
            break

# do color masking of sand
if not sand_mask == None:
    color_mask = cv2.imread(sand_mask, -1)
#    border_mask = np.invert(cv2.imread(im, -1)[:,:,-1]).astype(bool)
#    perc_sand = (np.sum(color_mask))/(color_mask.size-np.sum(border_mask))
    perc_sand = (np.sum(color_mask))/(color_mask.size)
    ignore_mask = np.logical_and(ignore_mask, np.invert(color_mask.astype(bool)))
else:
    # instantiate percentage sand for colormask
    perc_sand = 0

    # interactively select the color for masking
    while True:
        do_masking = input("\ncreate a color mask (for sand, vegetation, etc.)? (y/n): ")
        if do_masking=='y':
            # copy the image to prevent modification when adding more masks
            img = bgr.copy()
            # create hsv for colorpicking
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV_FULL)
            break
        elif do_masking=='n':
            break
        else:
            print("incorrect input, should be 'y' or 'n'")
    color_masks = []
    shadow_mask = np.invert(ignore_mask.copy().astype(np.uint8))
    while do_masking == 'y':
        # instantiate coordinate class for storing the clicks
        coords = func.pick_colors()
        # also create a copy of the current shadow mask to pass to the function
        current_mask = np.invert(ignore_mask.copy().astype(np.uint8))
        current_mask[current_mask==254] = 0
        current_mask = np.dstack((current_mask, current_mask, current_mask))
        img = cv2.addWeighted(current_mask, 0.6, img, 1, 0)
        # create a window and set the callback function
        win_name = "Color Selector ('q' to close, 'r' to flash image)"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(win_name, coords.clicker, param=[img, hsv, resize])
        while cv2.getWindowProperty(win_name, 0) >= 0:
            cv2.imshow(win_name, img)
            cv2.moveWindow(win_name, 0, 0)
            cv2.resizeWindow(win_name, func.resizeWin(img, resize)[0],
                             func.resizeWin(img, resize)[1])
            k = cv2.waitKey(1)
            if k == ord('q') & 0xFF:
                cv2.destroyAllWindows()
                break
            elif k == ord('r') & 0xFF:
                timeout = time.time() + 0.5
                while time.time() < timeout:
                    cv2.namedWindow("Image Overlay", cv2.WINDOW_NORMAL)
                    cv2.imshow("Image Overlay", bgr)
                    cv2.moveWindow("Image Overlay", 0, 0)
                    cv2.resizeWindow("Image Overlay", func.resizeWin(bgr, resize)[0],
                                 func.resizeWin(bgr, resize)[1])
                    cv2.waitKey(1)
                cv2.destroyWindow("Image Overlay")
            elif coords.closeWin == True:
                cv2.destroyAllWindows()
                break
        try:
            # apply the clicked range
            lower = coords.lower
            upper = coords.upper
            color_mask = cv2.inRange(hsv, lower, upper)
            color_mask = np.invert(color_mask).astype(bool)
            # clean it up
            color_mask = morph.remove_small_holes(color_mask, area_threshold=min_size, connectivity=2)
            color_mask = morph.opening(color_mask, selem=morph.selem.disk(1))
            color_mask = morph.closing(color_mask, selem=morph.selem.disk(1))
            # add the hue mask to the full ignore mask
            ignore_mask = np.logical_and(ignore_mask, color_mask)
            # make the color mask three channel image for stacking
            color_mask = color_mask.astype(np.uint8)
            color_mask[color_mask==0] = 255
            color_mask[color_mask==1] = 0
            color_mask = np.dstack((color_mask, color_mask, color_mask))
            color_masks.append(color_mask)
            # stack the color mask for subsequent runs
            img = cv2.addWeighted(color_mask, 0.6, img, 1, 0)
            # do we repeat the color masking?
            while True:
                do_masking = input("add another color mask? (y/n): ")
                if do_masking=='y' or do_masking=='n':
                    break
                else:
                    print("incorrect input, should be 'y' or 'n'")
        except:
            while True:
                do_masking = input("add another color mask? (y/n): ")
                if do_masking=='y' or do_masking=='n':
                    break
                else:
                    print("incorrect input, should be 'y' or 'n'")

    # combine the color masks if any were applied and get percentage sand
    if len(color_masks) != 0:
        color_mask = np.zeros(color_masks[0].shape[0:2]).astype(bool)
        for m in color_masks:
            m = m[:,:,0].astype(bool)
            color_mask = np.logical_or(color_mask, m)
        # the "color mask" represents percentage of pixels that are sand
        perc_sand = (np.sum(color_mask))/(color_mask.size)
        # also save the color_mask out as a TIFF and SHP mask if from georeferenced ortho-image
        if ortho:
            func.array2rast(color_mask.astype(int), im, sand_mask_tiff_out, xgrid, ygrid, filetype=gdal.GDT_Byte)
            sourceRaster = gdal.Open(sand_mask_tiff_out)
            band = sourceRaster.GetRasterBand(1)
            driver = ogr.GetDriverByName("ESRI Shapefile")
            outDatasource = driver.CreateDataSource(sand_mask_shp_out)
            srs = osr.SpatialReference()
            srs.ImportFromWkt(sourceRaster.GetProjectionRef())
            outLayer = outDatasource.CreateLayer(sand_mask_shp_out, srs)
            newField = ogr.FieldDefn("SandMask", ogr.OFTInteger)
            outLayer.CreateField(newField)
            gdal.Polygonize(band, band, outLayer, 0, [], callback=None)
            outDatasource.Destroy()
            sourceRaster=None
            band=None

# =============================================================================
# Segment
# =============================================================================

print("\nBeginning segmentation")

# tophat edges
print("Black tophat edge detection")
tophat = morph.black_tophat(gray, selem=morph.selem.disk(1))
tophat = tophat < np.percentile(tophat, tophat_th)
tophat = morph.remove_small_holes(tophat, area_threshold=5, connectivity=2)
if not np.sum(tophat) == 0:
    foo = func.featAND_fast(ignore_mask, tophat)
    ignore_mask = np.logical_and(foo, ignore_mask)
# canny edges
print("Canny edge detection")
canny = feat.canny(gray, sigma=canny_sig)
canny = np.invert(canny)
foo = func.featAND_fast(ignore_mask, canny)
ignore_mask = np.logical_and(foo, ignore_mask)
# sobel edges
print("Sobel edge detection")
sobel = filt.sobel(gray)
sobel = sobel < np.percentile(sobel, sobel_th)
sobel = morph.remove_small_holes(sobel, area_threshold=5, connectivity=2)
sobel = morph.thin(np.invert(sobel))
sobel = np.invert(sobel)
foo = func.featAND_fast(ignore_mask, sobel)
ignore_mask = np.logical_and(foo, ignore_mask)

# cleanup the mask
master_mask = morph.remove_small_objects(ignore_mask, min_size=min_size, connectivity=2)
master_mask = morph.erosion(master_mask, selem=morph.selem.square(3))
master_mask = morph.dilation(master_mask, selem=morph.selem.square(2))
master_mask = segm.clear_border(master_mask)
master_mask = morph.remove_small_objects(master_mask, min_size=min_size, connectivity=2)
# make sure we didn't accidently add any definite edges back in
master_mask[ignore_mask == False] = False

# eliminate any regions that are smaller than cutoff value
tmp, num = ndi.label(master_mask)
for region in meas.regionprops(tmp):
    grain_dil_ = morph.dilation(region.image, selem=morph.selem.square(2)).astype(int)
    grain_dil_ = np.pad(grain_dil_, ((1, 1), (1,1)), 'constant')
    b_ = meas.regionprops(grain_dil_)[0].minor_axis_length
    a_ = meas.regionprops(grain_dil_)[0].major_axis_length
    if b_ < float(cutoff) or a_ < float(cutoff):
        idxs = region.coords
        idxs = [tuple(i) for i in idxs]
        for idx in idxs:
            tmp[idx] = 0
idx = np.where(tmp == 0)
master_mask[idx] = 0

# get all the grains in the final mask
grains = []
polys = []
coordList = []
print("Getting grain properties")
labels, _ = ndi.label(master_mask)
for grain in meas.regionprops(labels):
    # dilate the grain before getting measurements
    grain_dil = morph.dilation(grain.image, selem=morph.selem.square(2)).astype(int)
    grain_dil = np.pad(grain_dil, ((1, 1), (1,1)), 'constant')
    b = meas.regionprops(grain_dil)[0].minor_axis_length
    a = meas.regionprops(grain_dil)[0].major_axis_length
    # get ellipse ring coordinates
    y0, x0 = grain.centroid[0], grain.centroid[1]
    orientation = grain.orientation - np.pi/2
    phi = np.linspace(0,2*np.pi,50)
    X = x0 + a/2 * np.cos(phi) * np.cos(-orientation) - b/2 * np.sin(phi) * np.sin(-orientation)
    Y = y0 + a/2 * np.cos(phi) * np.sin(-orientation) + b/2 * np.sin(phi) * np.cos(-orientation)
    # convert coordinates
    tupVerts = list(zip(X, Y))
    p = Path(tupVerts)
    # append ellipse as shapely polygon
    x, y = zip(*p.vertices)
    poly = Polygon([(i[0], i[1]) for i in list(zip(x, y))])
    polys.append(poly)
    # append list of grain coordinates for later removal if misfit/overlap
    grain_coords = [(i[0], i[1]) for i in grain.coords]
    coordList.append(grain_coords)
    # also get the percent difference in area (misfit)
    perc_diff_area = ((poly.area-grain.filled_area)/poly.area)*100
    # append the grain
    grains.append((y0, x0, b, a, orientation, grain.filled_area, poly.area, perc_diff_area))

# remove grains based on centroid inside of another grain and percentage overlap
# TODO: THIS IS SLOW
remove_indices = []
print("Removing overlapping grains")
for index, poly in enumerate(polys):
    x, y = poly.centroid.coords.xy[0][0], poly.centroid.coords.xy[1][0]
    check_pt = Point(x,y)
    for index_check, poly_check in enumerate(polys):
        # check the ellipse against all other ellipses except itself
        if not index == index_check:
            # is the centroid contained in another, then remove
            if poly_check.contains(check_pt):
                remove_indices.append(index)
            # is the overlap with another greater than threshold, then remove
            elif poly.intersection(poly_check).area/poly.area > perc_overlap/100:
                remove_indices.append(index)

# also find indices where the percent misfit is above some threshold and remove these
print("Removing misfit grains")
for index, grain in enumerate(grains):
    if index in remove_indices:
        continue
    elif np.abs(grain[7]) >= misfit_threshold:
        remove_indices.append(index)

# use the indices to remove the offending grains from the list and from the mask
label_fixed = labels.copy().astype(bool)
grains = [i for j, i in enumerate(grains) if j not in remove_indices]
for index in remove_indices:
    for i in coordList[index]:
        label_fixed[i] = False

# create a figure showing the results
print("Output final figure")
plt.figure(figsize=(10,10))
plt.imshow(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
labels, _ = ndi.label(label_fixed)
labels = labels.astype(float)
labels[labels == 0] = np.nan
labels[np.isfinite(labels)] = 255
plt.imshow(labels, cmap='gray', alpha = 0.5)
for grain in grains:
    y0, x0 = grain[0], grain[1]
    a, b = grain[3], grain[2]
    orientation = grain[4]
    x1 = x0 + np.cos(orientation) * .5 * a
    y1 = y0 - np.sin(orientation) * .5 * a
    x2 = x0 - np.sin(orientation) * .5 * b
    y2 = y0 - np.cos(orientation) * .5 * b
    # also plot the ellipse
    phi = np.linspace(0,2*np.pi,50)
    x = x0 + a/2 * np.cos(phi) * np.cos(-orientation) - b/2 * np.sin(phi) * np.sin(-orientation)
    y = y0 + a/2 * np.cos(phi) * np.sin(-orientation) + b/2 * np.sin(phi) * np.cos(-orientation)
    plt.plot((x0, x1), (y0, y1), '-r', linewidth=1)
    plt.plot((x0, x2), (y0, y2), '-r', linewidth=1)
    plt.plot(x0, y0, '.g', markersize=2)
    plt.plot(x, y, 'r--', linewidth=0.7)
plt.axis('off')
plt.savefig(fig_out, dpi=300)
plt.close()

# output results
print("Output final CSV and LABELS")
# what is the percent of the image not measured (fines or unfound rocks)
#perc_nongrain = (np.sum(np.invert(label_fixed.astype(bool)))-np.sum(border_mask))/(color_mask.size-np.sum(border_mask))
perc_nongrain = (np.sum(np.invert(label_fixed.astype(bool))))/(gray.size)
# subtract the percent sand from this
perc_nongrain -= perc_sand
# output the measured grains as a csv
with open(csv_out, "w") as csv_file:
    writer=csv.writer(csv_file, delimiter=",",lineterminator="\n",)
    writer.writerow(["PebbleCounts Parameters"])
    writer.writerow(["otsu_threshold", "cutoff", "percent_overlap", "misfit_threshold",
                     "min_size_threshold", "first_nl_denoise",
                     "tophat_th", "sobel_th", "canny_sig"])
    writer.writerow([otsu_threshold, cutoff, perc_overlap, misfit_threshold,
                     min_size, first_nl_denoise,
                     tophat_th, sobel_th, canny_sig])
    writer.writerow([])
    writer.writerow(["Image Details"])
    writer.writerow(["perc. not meas.", "perc. background color"])
    writer.writerow([perc_nongrain*100, perc_sand*100])
    writer.writerow([])
    writer.writerow(["Pebble Details"])
    if ortho:
        writer.writerow(["UTM X (m)", "UTM Y (m)", "a (px)", "b (px)",
                         "a (m)", "b (m)", "area (px)", "area (m2)",
                         "orientation", "ellipse area (px)", "perc. diff. area"])
    if not ortho:
        writer.writerow(["a (px)", "b (px)",
                         "a (m)", "b (m)", "area (px)", "area (m2)",
                         "orientation", "ellipse area (px)", "perc. diff. area"])

    for grain in grains:
        y0, x0 = grain[0], grain[1]
        a, b = grain[3], grain[2]
        orientation = grain[4]
        area = grain[5]
        ellipseArea = grain[6]
        perc_diff_area = grain[7]

        if ortho:
            x_coord = xgrid[np.round(y0).astype(int), np.round(x0).astype(int)]
            y_coord = ygrid[np.round(y0).astype(int), np.round(x0).astype(int)]
            writer.writerow([x_coord, y_coord, a, b,
                             a*step, b*step, area, area*step**2, orientation,
                             ellipseArea, perc_diff_area])

        if not ortho:
            writer.writerow([a, b,
                             a*step, b*step, area, area*step**2, orientation,
                             ellipseArea, perc_diff_area])

    csv_file.close()

# save out as raster or image
labels, _ = ndi.label(label_fixed)
if ortho:
    func.array2rast(labels, im, im_out, xgrid, ygrid)
if not ortho:
    labels = (color.label2rgb(labels, bg_label=0, bg_color=[1, 1, 1])*255).astype(np.uint8)
    cv2.imwrite(im_out, labels)

# get end time
end = time.time()
print("\nThat took about {:.0f} minutes, you counted {:d} pebbles!\n".format(end/60-start/60, len(grains)))

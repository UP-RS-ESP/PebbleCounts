# Python module accompanying PebbleCounts
#       Developed by Ben Purinton (purinton[at]uni-potsdam.de)
#       29 March 2019

import time
import numpy as np
import cv2
from skimage import measure as meas
from skimage import morphology as morph
from skimage.morphology import (square, disk)
from osgeo import gdal
from scipy.sparse import csr_matrix

def resizeWin(img, resize_factor=0.7):
    """
    Get the system screen resolution and resize input image by a factor. Factor
    must be in the range (0, 1].
    """
    from sys import platform as sys_pf
    if sys_pf != 'darwin':
        # this import needs to be within the function or else openCV throws errors
        import tkinter as tk
        root = tk.Tk()
        resize_factor = (1 - resize_factor) + 1
        sys_w, sys_h = root.winfo_screenwidth()/resize_factor, root.winfo_screenheight()/resize_factor
        root.destroy()
        root.quit()
        del root
    else:
        resize_factor = (1 - resize_factor) + 1
        sys_w, sys_h = 1920/resize_factor, 1080/resize_factor
    scale_width = sys_w / img.shape[1]
    scale_height = sys_h / img.shape[0]
    dimensions = min(scale_width, scale_height)
    window_width = int(img.shape[1] * dimensions)
    window_height = int(img.shape[0] * dimensions)
    return window_width, window_height

def image_check(im, resize_factor=0.7):
    """
    Open a given image and proceed with script on 'y' or end on 'n'
    """
    img = cv2.imread(im)
    win_name = "image check ('y'/'n'?)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    while cv2.getWindowProperty(win_name, 0) >= 0:
        cv2.imshow(win_name, img)
        cv2.moveWindow(win_name, 0, 0)
        cv2.resizeWindow(win_name, resizeWin(img, resize_factor)[0],
                         resizeWin(img, resize_factor)[1])
        k = cv2.waitKey(1)
        if k == ord('n') & 0xFF:
            cv2.destroyAllWindows()
            raise ValueError("\n\nSkipping image, ending script\n")
        elif k == ord('y') & 0xFF:
            print("\nProceeding with image\n")
            cv2.destroyAllWindows()
            break
        elif cv2.getWindowProperty(win_name, 0) == -1:
            raise ValueError("\n\nSkipping image, ending script\n")

def featAND(master_mask, joining_mask):
    """
    Feature-AND function to join labels in joining mask with master mask if
    the labels overlap. This version is deprecated as it was too slow.
    featAND_fast uses faster indexing using a sparse matrix to achieve needed speed.
    Background: Russ, John C. "The image processing handbook." (2002)
    """
    # label the interstices in each
    master_mask_labels = meas.label(master_mask, background=True, connectivity=2)
    joining_mask_labels = meas.label(joining_mask, background=True, connectivity=2)
    # loop through the array and pull out matching labeled regions
    connected_labels = []
    for i in range(master_mask.shape[0]):
        for j in range(master_mask.shape[1]):
            # if the pixel is labeled in both masks, append the label number
            if master_mask_labels[i,j] != 0 and joining_mask_labels[i,j] != 0:
                connected_labels.append(joining_mask_labels[i,j])
    # make a unique list of the labels in the joining mask that are connected to the master mask
    connected_labels = np.unique(np.array(connected_labels))
    # create the feature-AND mask
    threshold_AND = np.zeros(master_mask.shape).astype(np.uint8)
    for i in connected_labels:
        threshold_AND[joining_mask_labels == i] = 1
    # return as a boolean array
    mask = np.invert(threshold_AND.astype(bool))
    return mask

def featAND_fast(master_mask, joining_mask):
    """
    Feature-AND function to join labels in joining mask with master mask if
    the labels overlap. Using the faster indexing by sparse matrix:
        https://stackoverflow.com/questions/18452591/fast-python-numpy-where-functionality
    Background: Russ, John C. "The image processing handbook." (2002)
    """
    # label the interstices in each
    master_mask_labels = meas.label(master_mask, background=True, connectivity=2)
    joining_mask_labels = meas.label(joining_mask, background=True, connectivity=2)
    # loop through the array and pull out matching labeled regions
    connected_labels = []
    for i in range(master_mask.shape[0]):
        for j in range(master_mask.shape[1]):
            # if the pixel is labeled in both masks, append the label number
            if master_mask_labels[i,j] != 0 and joining_mask_labels[i,j] != 0:
                connected_labels.append(joining_mask_labels[i,j])
    # make a unique list of the labels in the joining mask that are connected to the master mask
    connected_labels = np.unique(np.array(connected_labels))
    # get all indices of the joining array using sparse matrix method
    cols = np.arange(joining_mask_labels.size)
    M = csr_matrix((cols, (joining_mask_labels.ravel(), cols)),
                   shape=(joining_mask_labels.max() + 1, joining_mask_labels.size))
    all_indx = [np.unravel_index(row.data, joining_mask_labels.shape) for row in M]
    # only take those indices in the connected labels array
    indx = []
    for i in connected_labels:
        indx.append(all_indx[i])
    # output the binary featureAND matrix
    threshold_AND = np.zeros(master_mask.shape).astype(np.uint8)
    for i in indx:
        threshold_AND[i] = 1
    # return as a boolean array
    mask = np.invert(threshold_AND.astype(bool))
    return mask

class otsu_threshold:
    """
    Class object for otsu thresholding
    """
    def __init__(self):
        # parameters to store
        #self.lower = None
        self.thresh = None
        self.closeWin = None
    def percent_of_otsu(self, otsu):
        while True:
            value = input("\nWhat percent of Otsu value ({:0.0f}) do you want to threshold with? (suggested 50): ".format(otsu))
            try:
                value = int(value)
            except:
                print("\nHmm looks like you didn't enter an integer from 0-100")
            if isinstance(value, int):
                self.thresh = float(value)
                break
            else:
                print("\nIncorrect input, should be an integer from 0-100\n")
    def apply_threshold(self, gray, bgr, otsu, resize_factor):
        gray_th = gray > otsu*(self.thresh/100)
        gray_th = gray_th.astype(np.uint8)
        gray_th[gray_th == 0] = 255
        gray_th[gray_th == 1] = 0
        gray_th = np.dstack((gray_th, gray_th, gray_th))
        image_mask = cv2.addWeighted(gray_th, 0.8, bgr, 1, 0)
        win_name = "Otsu Shadow Mask ('y' keep, 'n' to try another, 'r' flash image)"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        while cv2.getWindowProperty(win_name, 0) >= 0:
            cv2.imshow(win_name, image_mask)
            cv2.moveWindow(win_name, 0, 0)
            cv2.resizeWindow(win_name, resizeWin(image_mask, resize_factor)[0],
                             resizeWin(image_mask, resize_factor)[1])
            k = cv2.waitKey(1)
            # only keep the threshold if the 'y' key is pressed
            if k == ord('y') & 0xFF:
                cv2.destroyWindow(win_name)
                self.closeWin = True
                break
            # create a call to overlapping window of RGB image if 'r' is presseds
            elif k == ord('r') & 0xFF:
                timeout = time.time() + 0.5
                while time.time() < timeout:
                    cv2.namedWindow("Image Overlay", cv2.WINDOW_NORMAL)
                    cv2.imshow("Image Overlay", bgr)
                    cv2.moveWindow("Image Overlay", 0, 0)
                    cv2.resizeWindow("Image Overlay", resizeWin(bgr, resize_factor)[0],
                                resizeWin(bgr, resize_factor)[1])
                    cv2.waitKey(1)
                cv2.destroyWindow("Image Overlay")
            # ignore the threshold if 'n' or window is closed
            elif k == ord('n') & 0xFF:
                self.thresh = None
                cv2.destroyWindow(win_name)
                break
            elif cv2.getWindowProperty(win_name, 0) == -1:
                self.thresh = None
                break

class pick_colors:
    """
    Class object for selecting color range to mask
    """
    def __init__(self):
        # paramters we want to store
        self.lower = None
        self.upper = None
        self.closeWin = None
    def clicker(self, event, x, y, flags, param):
        """
        Function to store the upper and lower color bounds for the mask at the
        clicked location.
        """
        # parse the parameters
        bgr = param[0]
        hsv = param[1]
        resize_factor = param[2]
        if event == cv2.EVENT_LBUTTONDOWN:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV_FULL)
            pixel = hsv[y,x]
            # mask the following HSV (hue, saturation, brightness) ranges
            upper =  np.array([pixel[0] + 6, pixel[1] + 6, pixel[2] + 30])
            lower =  np.array([pixel[0] - 6, pixel[1] - 6, pixel[2] - 30])
            # add the clicked value
            self.lower = lower
            self.upper = upper
            # how does this mask look overlaid on the original image?
            image_mask = cv2.inRange(hsv,lower,upper)

            image_mask = np.invert(image_mask).astype(bool)
            # clean it up
            image_mask = morph.remove_small_holes(image_mask, area_threshold=10, connectivity=2)
            image_mask = morph.opening(image_mask, footprint=disk(1))
            image_mask = morph.closing(image_mask, footprint=disk(1))
            image_mask = image_mask.astype(np.uint8)
            image_mask[image_mask==0] = 255
            image_mask[image_mask==1] = 0
            image_mask = np.dstack((image_mask, image_mask, image_mask))
            image_mask = cv2.addWeighted(image_mask, 0.6, bgr, 1, 0)
            win_name = "Otsu Shadow Mask + Color Mask ('y' keep, 'n' to try another)"
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            while cv2.getWindowProperty(win_name, 0) >= 0:
                cv2.imshow(win_name, image_mask)
                cv2.moveWindow(win_name, 0, 0)
                cv2.resizeWindow(win_name, resizeWin(image_mask, resize_factor)[0],
                                 resizeWin(image_mask, resize_factor)[1])
                k = cv2.waitKey(1)
                # only keep the bounds if the 'y' key is pressed
                if k == ord('y') & 0xFF:
                    cv2.destroyWindow(win_name)
                    self.closeWin = True
                    break
                # ignore the clicked bounds if 'n' or window is closed
                elif k == ord('n') & 0xFF:
                    self.lower = None
                    self.upper = None
                    cv2.destroyWindow(win_name)
                    break
                elif cv2.getWindowProperty(win_name, 0) == -1:
                    self.lower = None
                    self.upper = None
                    break

class select_grains:
    """
    Class object for selecting seed points
    """
    def __init__(self):
        # parameters we want to store
        self.clicks = []
    def clicker(self, event, x, y, flags, param):
        #global img, clicks, values, circles
        img = param[0]
        # if left button click, add a seed point at that location and draw a black circle
        if event == cv2.EVENT_LBUTTONDOWN:
            print('clicked point: {}, {}'.format(str(y), str(x)))
            self.clicks.append((y,x))
            cv2.circle(img, (x,y), 5, (0, 0, 0), 2)
        # if right button click anywhere, remove the previous seed point and draw a red circle
        if event == cv2.EVENT_RBUTTONDOWN:
            try:
                print('removed point: {}, {}'.format(str(self.clicks[-1][0]), str(self.clicks[-1][1])))
                cv2.circle(img, (self.clicks[-1][1], self.clicks[-1][0]), 5, (0, 0, 255), 2)
                self.clicks = self.clicks[:-1]
            except:
                print('no seed points clicked')

def sliding_window(image, stepSize, windowSize):
    """
    Sliding window breaks input image into overlapping regions.
    """
    for y in range(0, image.shape[0], stepSize):
        for x in range(0, image.shape[1], stepSize):
            sz = image[y:y + windowSize, x:x + windowSize].shape
            yield (x, y, sz)

def getXYgrid(geo_rast):
    """
    takes input geo raster and outputs numpy arrays of X and Y coordinates (center of pixel)
    """
    # create X and Y and get the resolution (step)
    ds = gdal.Open(geo_rast)
    cols, rows = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()
    ds = None
    step = gt[1]
    # size of grid (minx, stepx, 0, maxy, 0, -stepy)
    minx, maxy = gt[0], gt[3]
    maxx, miny = gt[0] + step * cols, gt[3] + -step * rows
    # center of pixel
    ygrid = np.arange(miny + (step / 2), maxy, step)
    xgrid = np.arange(minx + (step / 2), maxx, step)
    xgrid, ygrid = np.meshgrid(xgrid, ygrid)
    ygrid = np.flipud(ygrid)
    return xgrid, ygrid

def array2rast(array, rast_in, rast_out, xgrid, ygrid, NDV=0, filetype=gdal.GDT_Int32):
    """
    Use GDAL to take an input array and a given raster and output a raster with the
    same spatial referencing
    """
    ds = gdal.Open(rast_in)
    gt = ds.GetGeoTransform()
    cs = ds.GetProjection()
    ds = None
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    outRaster = driver.Create(rast_out, array.shape[1],
                              array.shape[0], 1, filetype)
    gt_new = (xgrid[0,0], gt[1], gt[2], ygrid[0,0], gt[4], gt[5])
    outRaster.SetGeoTransform(gt_new)
    outRaster.SetProjection(cs)
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array,0,0)
    outband.SetNoDataValue(0)
    outband.FlushCache()
    del driver, outRaster, gt, cs, outband, ds

def calculate_camera_res(focal_length_mm, height_m, sensorH_mm=15.6, sensorW_mm=23.5,
                         pixelsH=4000, pixelsW=6000):
    """
    Get approximated camera resolution in mm/pixel given a top down photograph.
    Check the photo meta-data to get the focal length and height and width in pixels.
    The sensor height and width can be found in the camera specs or via a quick
    online search of the camera make and model.
    """
    fovH_m = (sensorH_mm/focal_length_mm)*height_m
    fovW_m = (sensorW_mm/focal_length_mm)*height_m
    print("\nThe field of view is {:0.2f} by {:0.2f} m\n".format(fovH_m, fovW_m))
    return np.round(fovH_m*1000/pixelsH, 4), np.round(fovW_m*1000/pixelsW, 4)
